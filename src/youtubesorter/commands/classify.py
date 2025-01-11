"""Command for classifying videos into multiple playlists.

This command inherits from YouTubeCommand (in src/commands/__init__.py) which provides:
- Progress tracking (self.set_total_items, self.update_progress)
- Dry run support (self.dry_run)
- Error handling (self.handle_error)
- Logging (self._logger)
"""

import logging
from typing import Optional, List, Dict, Any

from ..api import YouTubeAPI
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

            with RecoveryManager(self.source_playlist_id, self.name) as recovery:
                if self.resume_destination:
                    if self.resume_destination not in recovery.destination_metadata:
                        raise ValueError(
                            f"Destination {self.resume_destination} not found in recovery state"
                        )
                    progress = recovery.get_destination_progress(self.resume_destination)
                    if progress.get("completed", False):
                        raise ValueError(f"Destination {self.resume_destination} already completed")

    def classify_video(self, video: Dict[str, Any]) -> Optional[str]:
        """Classify a video into a target playlist.

        Args:
            video: Video data

        Returns:
            Target playlist ID or None if no match
        """
        return self.target_playlists[0] if self.target_playlists else None

    def _run(self) -> bool:
        """Execute the command.

        Returns:
            True if successful, False otherwise
        """
        try:
            with RecoveryManager(
                playlist_id=self.source_playlist_id, operation_type=self.name
            ) as recovery:
                self.recovery = recovery

                # Load previous state if resuming
                if self.resume:
                    recovery.load_state()

                # Get videos from playlist
                try:
                    videos = self.youtube.get_playlist_videos(self.source_playlist_id)
                    for video in videos:
                        recovery.assign_video(video["video_id"], None, video_data=video)
                except Exception as e:
                    self._logger.error("Failed to get videos from playlist: %s", str(e))
                    return False

                # Get remaining videos to process
                remaining = recovery.get_remaining_videos()

                if not remaining:
                    self._logger.info("No videos to process")
                    return True

                self._logger.info("Processing %d videos...", len(remaining))

                # Process each video
                for video in remaining:
                    video_id = video["video_id"]
                    title = video.get("title", "Unknown")

                    try:
                        # Classify video
                        target_playlist = self.classify_video(video)
                        if not target_playlist:
                            self._logger.info("No target playlist for video: %s", title)
                            recovery.processed_videos.add(video_id)
                            continue

                        if self.dry_run:
                            self._logger.info(
                                "Would add video '%s' to playlist '%s'",
                                title,
                                target_playlist,
                            )
                            recovery.processed_videos.add(video_id)
                            continue

                        # Add video to target playlist
                        try:
                            added = self.youtube.batch_add_videos_to_playlist(
                                [video_id], target_playlist
                            )
                            if video_id in added:
                                recovery.processed_videos.add(video_id)
                            else:
                                self._logger.error("Failed to process %s: Video not added", title)
                                recovery.failed_videos.add(video_id)
                        except Exception as e:
                            self._logger.error("Failed to process %s: %s", title, str(e))
                            recovery.failed_videos.add(video_id)

                        recovery.save_state()

                    except Exception as e:
                        self._logger.error("Failed to process %s: %s", title, str(e))
                        recovery.failed_videos.add(video_id)
                        recovery.save_state()

                self._logger.info("Classification complete")
                return True

        except Exception as e:
            self._logger.error("Error classifying videos: %s", str(e))
            return False
