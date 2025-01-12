"""Distribute videos from a playlist based on filter prompts."""

import logging
from typing import Dict, List, Optional, Set

from . import common
from .core import YouTubeBase
from .errors import PlaylistNotFoundError, YouTubeError
from .undo import UndoManager, UndoOperation

logger = logging.getLogger(__name__)


def distribute_videos(
    youtube: YouTubeBase,
    source_playlist: str,
    target_playlists: List[str],
    filter_prompts: List[str],
    dry_run: bool = False,
    verbose: bool = False,
    resume: bool = False,
    resume_destination: Optional[str] = None,
    retry_failed: bool = False,
    limit: Optional[int] = None,
) -> bool:
    """Distribute videos from a source playlist to multiple target playlists.

    Based on filter prompts, videos are moved to matching target playlists.

    Args:
        youtube: YouTube API client
        source_playlist: Source playlist ID
        target_playlists: List of target playlist IDs
        filter_prompts: List of filter prompts (one per target playlist)
        dry_run: Whether to perform a dry run
        verbose: Whether to enable verbose output
        resume: Whether to resume a previous operation
        resume_destination: Resume from specific destination playlist
        retry_failed: Whether to retry failed operations
        limit: Maximum number of videos to process

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Validate input
        if len(target_playlists) != len(filter_prompts):
            logger.error("Number of target playlists must match number of filter prompts")
            return False

        # Get source playlist info
        try:
            source_info = youtube.get_playlist_info(source_playlist)
            source_title = source_info["title"]
        except PlaylistNotFoundError:
            logger.error("Source playlist %s not found", source_playlist)
            return False

        # Get target playlist info
        target_titles = []
        for playlist_id in target_playlists:
            try:
                info = youtube.get_playlist_info(playlist_id)
                target_titles.append(info["title"])
            except PlaylistNotFoundError:
                logger.error("Target playlist %s not found", playlist_id)
                return False

        # Log operation details
        logger.info(
            "Distributing videos from %s to %d playlists",
            source_title,
            len(target_playlists)
        )
        for i, (playlist_id, title, prompt) in enumerate(
            zip(target_playlists, target_titles, filter_prompts), 1
        ):
            logger.info("  Target %d: %s (%s) - Filter: %s", i, title, playlist_id, prompt)

        if dry_run:
            logger.info("Dry run - no changes will be made")
            return True

        # Get videos from source playlist
        try:
            videos = youtube.get_playlist_videos(source_playlist)
        except YouTubeError as e:
            logger.error("Failed to get videos from source playlist: %s", str(e))
            return False

        if not videos:
            logger.info("No videos found in source playlist")
            return True

        # Process videos
        processed_videos: Set[str] = set()
        failed_videos: Set[str] = set()
        skipped_videos: Set[str] = set()
        target_mapping: Dict[str, str] = {}

        # Classify and distribute videos
        for i, (target_id, prompt) in enumerate(zip(target_playlists, filter_prompts)):
            # Classify videos for this target
            unprocessed = [v for v in videos if v["id"] not in processed_videos]
            matches = common.classify_video_titles(unprocessed, prompt)
            matching_videos = [v["id"] for v, match in zip(unprocessed, matches) if match]

            if not matching_videos:
                logger.info("No matching videos for target %s", target_id)
                continue

            # Move matching videos
            success = youtube.batch_move_videos_to_playlist(
                playlist_id=target_id,
                video_ids=matching_videos,
                source_playlist_id=source_playlist,
                remove_from_source=True
            )
            
            # Track results
            for video_id in matching_videos:
                if video_id in success:
                    processed_videos.add(video_id)
                    target_mapping[video_id] = target_id
                else:
                    failed_videos.add(video_id)

        # Save undo operation
        manager = UndoManager("distribute")
        operation = UndoOperation(
            operation_type="distribute",
            source_playlists=[source_playlist],
            target_playlists=target_playlists,
            was_move=True,
            videos=[{"id": vid} for vid in processed_videos],
            target_mapping=target_mapping,
        )
        manager.save_operation(operation)

        # Log summary
        common.log_operation_summary(
            "distribute",
            source_playlist,
            list(processed_videos),
            list(failed_videos),
            list(skipped_videos),
            verbose=verbose,
        )

        return True

    except Exception as e:
        logger.error("Failed to distribute videos: %s", str(e))
        return False
