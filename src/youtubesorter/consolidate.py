"""Consolidate videos from multiple playlists into one."""

import argparse
import logging
import os
from typing import Dict, List, Optional, Set, Tuple

from . import common, errors
from .core import YouTubeBase
from .errors import PlaylistNotFoundError, YouTubeError
from .undo import UndoManager, UndoOperation
from .config import STATE_DIR


logger = logging.getLogger(__name__)


class RecoveryManager:
    """Manages recovery state for consolidate operations."""

    def __init__(self, operation_type: str):
        """Initialize recovery manager.
        
        Args:
            operation_type: Type of operation (consolidate, move, etc)
        """
        self.operation_type = operation_type
        self.processed_videos: Set[str] = set()
        self.failed_videos: Set[str] = set()
        self.target_mapping: Dict[str, str] = {}

    def save_state(self) -> None:
        """Save current recovery state."""
        common.save_operation_state(
            playlist_id=self.operation_type,
            processed_videos=list(self.processed_videos),
            failed_videos=list(self.failed_videos),
            skipped_videos=[]  # Consolidate doesn't track skipped videos
        )

    def load_state(self) -> bool:
        """Load previous recovery state.
        
        Returns:
            bool: True if state was loaded successfully
        """
        try:
            state_file = os.path.join(STATE_DIR, f"{self.operation_type}_state.json")
            state = common.load_operation_state(state_file=state_file)
            if not state or state.get("operation_type") != self.operation_type:
                return False
                
            self.processed_videos = set(state.get("processed_videos", []))
            self.failed_videos = set(state.get("failed_videos", []))
            self.target_mapping = state.get("target_mapping", {})
            return True
        except Exception as e:
            logger.error("Failed to load recovery state: %s", str(e))
            return False

    def add_processed_video(self, video_id: str, target_playlist: str) -> None:
        """Add a successfully processed video.
        
        Args:
            video_id: ID of processed video
            target_playlist: Target playlist ID
        """
        self.processed_videos.add(video_id)
        self.target_mapping[video_id] = target_playlist
        self.save_state()

    def add_failed_video(self, video_id: str) -> None:
        """Add a failed video.
        
        Args:
            video_id: ID of failed video
        """
        self.failed_videos.add(video_id)
        self.save_state()

    def clear_state(self) -> None:
        """Clear recovery state."""
        self.processed_videos.clear()
        self.failed_videos.clear()
        self.target_mapping.clear()
        common.clear_operation_state()


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
    """Process a single playlist.

    Args:
        youtube: YouTube API client
        source_playlist: Source playlist ID
        target_playlist: Target playlist ID
        copy: Whether to copy videos instead of moving them
        limit: Maximum number of videos to process
        verbose: Whether to log verbose output
        processed_videos: Set of already processed video IDs
        failed_videos: Set of failed video IDs

    Returns:
        Tuple of (processed, failed, skipped) video IDs
    """
    if verbose:
        logger.info("Processing playlist: %s", source_playlist)

    processed_videos = processed_videos or set()
    failed_videos = failed_videos or set()

    # Get videos from source playlist
    videos = youtube.get_playlist_videos(source_playlist)
    if not videos:
        return [], [], []

    # Filter out already processed videos
    unprocessed_videos = [v for v in videos if v["video_id"] not in processed_videos]
    skipped = [v["video_id"] for v in videos if v["video_id"] in processed_videos]

    # Apply limit if specified
    if limit:
        unprocessed_videos = unprocessed_videos[:limit]

    # Get video IDs
    unprocessed_ids = [v["video_id"] for v in unprocessed_videos]
    if not unprocessed_ids:
        return [], [], skipped

    # Move or copy videos
    try:
        if copy:
            processed = youtube.batch_add_videos_to_playlist(
                playlist_id=target_playlist,
                video_ids=unprocessed_ids
            )
        else:
            processed = youtube.batch_move_videos_to_playlist(
                playlist_id=target_playlist,
                video_ids=unprocessed_ids,
                source_playlist_id=source_playlist,
                remove_from_source=True
            )
        failed = [v for v in unprocessed_ids if v not in processed]
        return processed, failed, skipped
    except Exception as e:
        logger.error("Failed to process videos: %s", str(e))
        return [], unprocessed_ids, skipped


def consolidate_playlists(
    youtube: YouTubeBase,
    source_playlists: List[str],
    target_playlist: str,
    copy: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    resume: bool = False,
    retry_failed: bool = False,
    limit: Optional[int] = None,
    resume_destination: Optional[str] = None,
) -> Tuple[List[str], List[str], List[str]]:
    """Consolidate multiple playlists into one.

    Args:
        youtube: YouTube API client
        source_playlists: List of source playlist IDs
        target_playlist: Target playlist ID
        copy: Whether to copy videos instead of moving them
        dry_run: Whether to perform a dry run without making changes
        verbose: Whether to log verbose output
        resume: Whether to resume from a previous state
        retry_failed: Whether to retry failed videos
        limit: Maximum number of videos to process per playlist
        resume_destination: Playlist ID to resume from

    Returns:
        Tuple of (processed video IDs, failed video IDs, skipped video IDs)
    """
    recovery = RecoveryManager("consolidate")
    total_processed = []
    total_failed = []
    total_skipped = []

    # Load previous state if resuming
    if resume:
        try:
            recovery.load_state()
            if retry_failed:
                total_failed = list(recovery.failed_videos)
            else:
                total_processed = list(recovery.processed_videos)
                total_failed = list(recovery.failed_videos)
        except Exception as e:
            logger.error(f"No recovery state found: {e}")
            if resume_destination:
                raise YouTubeError("No recovery state found")

    # Validate target playlist exists
    try:
        target_info = youtube.get_playlist_info(target_playlist)
        if verbose:
            logger.info(f"Target playlist: {target_info['title']}")
    except Exception as e:
        logger.error(f"Failed to get target playlist info: {e}")
        raise YouTubeError(f"Target playlist not found: {target_playlist}")

    # Process each source playlist
    start_processing = not resume_destination
    for source_playlist in source_playlists:
        if resume_destination and source_playlist == resume_destination:
            start_processing = True
        if not start_processing:
            continue

        try:
            processed, failed, skipped = process_playlist(
                youtube,
                source_playlist,
                target_playlist,
                copy=copy,
                limit=limit,
                verbose=verbose,
                processed_videos=set(total_processed),
                failed_videos=set(total_failed)
            )
            total_processed.extend(processed)
            total_failed.extend(failed)
            total_skipped.extend(skipped)

            # Update recovery state
            recovery.processed_videos = set(total_processed)
            recovery.failed_videos = set(total_failed)
            recovery.save_state()

        except PlaylistNotFoundError:
            logger.error(f"Playlist not found: {source_playlist}")
            continue
        except YouTubeError as e:
            logger.error(f"Failed to process playlist {source_playlist}: {e}")
            continue

    return total_processed, total_failed, total_skipped


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
