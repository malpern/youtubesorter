"""Command for classifying videos into multiple playlists.

This command inherits from YouTubeCommand (in src/commands/__init__.py) which provides:
- Progress tracking (self.set_total_items, self.update_progress)
- Dry run support (self.dry_run)
- Error handling (self.handle_error)
- Logging (self._logger)
"""

import logging
from typing import Optional, List, Dict, Any

from ..core import YouTubeBase
from ..recovery import RecoveryManager
from ..common import find_latest_state
from . import YouTubeCommand

# Get logger instance
logger = logging.getLogger(__name__)


class ClassifyCommand(YouTubeCommand):
    """Command for classifying videos into multiple playlists."""

    def __init__(
        self,
        youtube: YouTubeBase,
        source_playlist_id: str,
        target_playlists: List[str],
        resume: bool = False,
        resume_destination: Optional[str] = None,
        retry_failed: bool = False,
        dry_run: bool = False,
        limit: Optional[int] = None,
    ) -> None:
        """Initialize command.

        Args:
            youtube: YouTube API client
            source_playlist_id: ID of source playlist
            target_playlists: List of target playlist IDs
            resume: Whether to resume from last saved state
            resume_destination: Optional destination to resume for
            retry_failed: Whether to retry failed videos
            dry_run: Whether to run in dry run mode
            limit: Maximum number of videos to process
        """
        super().__init__(youtube)
        self.name = "classify"
        self.help = "Classify videos into multiple playlists"
        self.source_playlist_id = source_playlist_id
        self.target_playlists = target_playlists
        self.resume = resume
        self.resume_destination = resume_destination
        self.retry_failed = retry_failed
        self.recovery = None
        self.batch_size = 50
        self.dry_run = dry_run
        self.limit = limit

    def validate(self) -> None:
        """Validate command arguments."""
        super().validate()
        if not self.source_playlist_id:
            raise ValueError("Source playlist ID is required")
        if not self.target_playlists:
            raise ValueError("At least one target playlist ID is required")

        if self.resume_destination and not self.resume:
            raise ValueError("--resume-destination requires --resume")

        if self.resume:
            state_file = find_latest_state(self.source_playlist_id)
            if not state_file:
                raise ValueError(f"No recovery state found for playlist {self.source_playlist_id}")

            self.recovery = RecoveryManager(self.source_playlist_id, self.name)
            self.recovery.load_state()  # Load state after validation
            if self.resume_destination:
                if self.resume_destination not in self.recovery.destination_metadata:
                    raise ValueError(
                        f"Destination {self.resume_destination} not found in recovery state"
                    )
                if self.recovery.get_destination_progress(self.resume_destination).get("completed"):
                    raise ValueError(
                        f"Destination {self.resume_destination} already completed"
                    )

    def classify_video(self, video: Dict[str, Any]) -> Optional[str]:
        """Classify a video into a target playlist.

        Args:
            video: Video data

        Returns:
            Target playlist ID or None if no match
        """
        return self.target_playlists[0] if self.target_playlists else None

    def _run(self) -> bool:
        """Run the command."""
        # Get videos to process
        if self.resume:
            videos = self.recovery.get_remaining_videos()
        else:
            videos = self.youtube.get_playlist_videos(self.source_playlist_id)

        if not videos:
            logger.info("No videos to process")
            return True

        logger.info("Processing %d videos...", len(videos))

        # Process each video
        for video in videos:
            try:
                target_playlist = self.classify_video(video)
                if target_playlist:
                    # Add video to target playlist
                    self.youtube.batch_add_videos_to_playlist(
                        [video["snippet"]["resourceId"]["videoId"]], target_playlist
                    )
                    self.recovery.add_processed_video(video["snippet"]["resourceId"]["videoId"])
                else:
                    self.recovery.add_skipped_video(video["snippet"]["resourceId"]["videoId"])
            except Exception as e:
                logger.error("Failed to process video '%s': %s", video["snippet"]["title"], str(e))
                self.recovery.add_failed_video(video["snippet"]["resourceId"]["videoId"])

        return True
