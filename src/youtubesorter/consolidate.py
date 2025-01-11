"""Consolidate videos from multiple playlists."""

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Set, Tuple

from . import common, errors
from .api import YouTubeAPI
from .core import YouTubeBase
from .recovery import RecoveryManager


logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(description="YouTube playlist consolidation tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Consolidate command
    consolidate_parser = subparsers.add_parser(
        "consolidate", help="Consolidate videos from multiple playlists"
    )
    consolidate_parser.add_argument(
        "source_playlists", help="Comma-separated list of source playlist IDs or URLs"
    )
    consolidate_parser.add_argument(
        "-t", "--target-playlist", required=True, help="Target playlist ID or URL"
    )
    consolidate_parser.add_argument(
        "-c", "--copy", action="store_true", help="Copy instead of move videos"
    )
    consolidate_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    consolidate_parser.add_argument(
        "-r", "--resume", action="store_true", help="Resume previous operation"
    )
    consolidate_parser.add_argument(
        "--retry-failed", action="store_true", help="Retry previously failed videos"
    )
    consolidate_parser.add_argument("--limit", type=int, help="Limit number of videos to process")

    # Undo command
    undo_parser = subparsers.add_parser("undo", help="Undo last operation")
    undo_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    return parser


def process_playlist(
    youtube: YouTubeBase,
    source_playlist: str,
    target_playlist: str,
    copy: bool = False,
    limit: Optional[int] = None,
    verbose: bool = False,
    processed_videos: Optional[Set[str]] = None,
    failed_videos: Optional[Set[str]] = None,
) -> Tuple[List[str], List[str], List[str]]:
    """Process a single playlist for consolidation.

    Args:
        youtube: YouTube API client
        source_playlist: Source playlist ID
        target_playlist: Target playlist ID
        copy: Whether to copy instead of move videos
        limit: Optional limit on number of videos to process
        verbose: Whether to output verbose progress
        processed_videos: Set of already processed video IDs
        failed_videos: Set of failed video IDs

    Returns:
        Tuple of (successful_moves, failed_moves, skipped_videos)
    """
    if processed_videos is None:
        processed_videos = set()
    if failed_videos is None:
        failed_videos = set()

    api = YouTubeAPI(youtube)
    try:
        videos = api.get_playlist_videos(source_playlist)
        if not videos:
            logger.info("No videos found in source playlist")
            return [], [], []

        # Filter out already processed videos
        videos = [v for v in videos if v["video_id"] not in processed_videos]
        if limit:
            videos = videos[:limit]

        if not videos:
            logger.info("No new videos to process")
            return [], [], []

        # Process videos
        video_ids = [v["video_id"] for v in videos]
        if copy:
            processed = api.batch_add_videos_to_playlist(target_playlist, video_ids)
        else:
            processed = api.batch_move_videos_to_playlist(
                source_playlist, target_playlist, video_ids
            )

        failed = [v for v in video_ids if v not in processed]
        skipped = []

        # Update tracking sets
        processed_videos.update(processed)
        failed_videos.update(failed)

        if verbose:
            logger.info(
                "Processed %d videos from %s (%d failed, %d skipped)",
                len(processed),
                source_playlist,
                len(failed),
                len(skipped),
            )

        return processed, failed, skipped
    except Exception as e:
        logger.error("Error processing playlist %s: %s", source_playlist, str(e))
        return [], [], []


def consolidate_playlists(
    youtube: YouTubeBase,
    source_playlist_ids: List[str],
    target_playlist_id: str,
    copy: bool = False,
    limit: Optional[int] = None,
    verbose: bool = False,
    resume: bool = False,
    retry_failed: bool = False,
) -> None:
    """Consolidate videos from multiple playlists into one.

    Args:
        youtube: YouTube API client
        source_playlist_ids: List of source playlist IDs
        target_playlist_id: Target playlist ID
        copy: Whether to copy instead of move videos
        limit: Optional limit on number of videos to process
        verbose: Whether to output verbose progress
        resume: Whether to resume from last state
        retry_failed: Whether to retry previously failed videos
    """
    # Initialize or load state
    recovery_manager = RecoveryManager(
        playlist_id=source_playlist_ids[0],  # Use first playlist as primary
        operation_type="consolidate",
    )

    if resume:
        processed_videos = set(recovery_manager.processed_videos)
        failed_videos = set(recovery_manager.failed_videos)
    else:
        processed_videos = set()
        failed_videos = set()

    if retry_failed:
        failed_videos.clear()

    total_successful = []
    total_failed = []
    total_skipped = []

    # Process playlists sequentially to maintain consistent state
    for playlist_id in source_playlist_ids:
        try:
            # Calculate remaining limit for this playlist
            remaining_limit = None
            if limit is not None:
                remaining_videos = limit - len(total_successful)
                if remaining_videos <= 0:
                    break
                remaining_limit = remaining_videos

            successful, failed, skipped = process_playlist(
                youtube,
                playlist_id,
                target_playlist_id,
                copy=copy,
                limit=remaining_limit,
                verbose=verbose,
                processed_videos=processed_videos,
                failed_videos=failed_videos,
            )

            total_successful.extend(successful)
            total_failed.extend(failed)
            total_skipped.extend(skipped)

            # Update recovery state after each playlist
            for video_id in successful:
                recovery_manager.assign_video(video_id, target_playlist_id)
            for video_id in failed:
                recovery_manager.assign_video(video_id, target_playlist_id, success=False)

            if verbose:
                logger.info("Completed processing playlist %s", playlist_id)

        except Exception as e:
            logger.error("Error processing playlist %s: %s", playlist_id, str(e))
            total_failed.extend([playlist_id])

    # Save operation for undo
    common.save_operation_state(
        target_playlist=target_playlist_id,
        processed=total_successful,
        failed=total_failed,
        skipped=total_skipped,
        state_file=".youtubesorter_undo_state.json",
    )

    # Log summary
    common.log_operation_summary(
        operation_type="consolidate",
        target_playlist=target_playlist_id,
        processed=total_successful,
        failed=total_failed,
        skipped=total_skipped,
        verbose=verbose,
    )


def undo_last_operation(youtube: YouTubeBase, verbose: bool = False) -> bool:
    """Undo the last consolidate operation.

    Args:
        youtube: YouTube API client
        verbose: Whether to enable verbose output

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        common.undo_operation(youtube, verbose=verbose)
        return True
    except Exception as e:
        errors.log_error(str(e), "Failed to undo consolidate operation")
        return False
