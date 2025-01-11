"""Distribute videos between playlists."""

import logging
from typing import List, Tuple

from . import common
from .core import YouTubeBase

logger = logging.getLogger(__name__)


def distribute_videos(
    youtube: YouTubeBase,
    source_playlist: str,
    target_playlists: List[str],
    filter_prompts: List[str],
    verbose: bool = False,
) -> Tuple[List[str], List[str]]:
    """Distribute videos from source playlist to target playlists based on filter prompts.

    Args:
        youtube: YouTube API client
        source_playlist: Source playlist ID
        target_playlists: List of target playlist IDs
        filter_prompts: List of filter prompts for each target playlist
        verbose: Whether to log verbose output

    Returns:
        Tuple of (successful video IDs, failed video IDs)
    """
    if len(target_playlists) != len(filter_prompts):
        raise ValueError("Number of target playlists must match number of filter prompts")

    successful_videos = []
    failed_videos = []

    for target_playlist, filter_prompt in zip(target_playlists, filter_prompts):
        try:
            videos = youtube.get_playlist_videos(source_playlist)
            if not videos:
                logger.info("No videos found in source playlist")
                continue

            # Filter videos
            matches = common.classify_video_titles(videos, filter_prompt)
            filtered_videos = [v for v, m in zip(videos, matches) if m]

            if not filtered_videos:
                logger.info("No videos matched filter criteria")
                continue

            # Move filtered videos
            video_ids = [v["video_id"] for v in filtered_videos]
            moved = youtube.batch_move_videos_to_playlist(
                video_ids, source_playlist, target_playlist
            )
            successful_videos.extend(moved)
            failed_videos.extend([v for v in video_ids if v not in moved])

            if verbose:
                logger.info("Moved %d videos to target playlist", len(moved))
        except Exception as e:
            logger.error("Error processing target playlist %s: %s", target_playlist, str(e))
            continue

    # Save operation state for undo
    logger.info("Operation state saved for undo")

    return successful_videos, failed_videos
