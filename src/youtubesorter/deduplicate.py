"""Command for removing duplicate videos from a playlist."""

from typing import List, Set

from .core import YouTubeBase
from .logging_config import get_logger
from .commands import YouTubeCommand

# Get logger instance
logger = get_logger(__name__)


def deduplicate_playlist(youtube: YouTubeBase, playlist_id: str) -> List[str]:
    """Remove duplicate videos from a playlist.

    Args:
        youtube: YouTube API client
        playlist_id: ID of playlist to deduplicate

    Returns:
        List of removed video IDs
    """
    videos = youtube.get_playlist_videos(playlist_id)

    # Track seen videos by ID
    seen_videos: Set[str] = set()
    duplicates: Set[str] = set()

    for video in videos:
        video_id = video["video_id"]
        if video_id in seen_videos:
            duplicates.add(video_id)
        else:
            seen_videos.add(video_id)

    # Remove duplicates
    if duplicates:
        removed = youtube.batch_remove_videos_from_playlist(
            playlist_id=playlist_id,
            video_ids=list(duplicates)
        )
        logger.info("Removed %d duplicate videos", len(removed))
        return removed

    logger.info("No duplicate videos found")
    return []


class DeduplicateCommand(YouTubeCommand):
    """Command for removing duplicate videos from a playlist."""

    def __init__(self, youtube: YouTubeBase, playlist_id: str):
        """Initialize command.

        Args:
            youtube: YouTube API client
            playlist_id: ID of playlist to deduplicate
        """
        super().__init__(youtube)
        self.playlist_id = playlist_id
        self._logger = logger

    def validate(self) -> bool:
        """Validate command arguments.

        Returns:
            True if validation passes
        """
        if not self.playlist_id:
            raise ValueError("Playlist ID is required")
        return True

    def run(self) -> bool:
        """Run the command.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            removed = deduplicate_playlist(self.youtube, self.playlist_id)
            return bool(removed)
        except Exception as e:
            self._logger.error("Error deduplicating playlist: %s", str(e))
            return False
