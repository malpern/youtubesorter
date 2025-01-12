"""Command for deduplicating playlists."""

import logging
from typing import Optional, List, Dict, Any

from ..core import YouTubeBase
from ..recovery import RecoveryManager
from ..common import find_latest_state
from . import YouTubeCommand

# Get logger instance
logger = logging.getLogger(__name__)


class DeduplicateCommand(YouTubeCommand):
    """Command for deduplicating playlists."""

    def __init__(
        self,
        youtube: YouTubeBase,
        playlist_id: str,
        resume: bool = False,
        resume_destination: Optional[str] = None,
        retry_failed: bool = False,
        dry_run: bool = False,
        limit: Optional[int] = None,
    ) -> None:
        """Initialize command.

        Args:
            youtube: YouTube API client
            playlist_id: ID of playlist to deduplicate
            resume: Whether to resume from last saved state
            resume_destination: Optional destination to resume for
            retry_failed: Whether to retry failed videos
            dry_run: Whether to run in dry run mode
            limit: Maximum number of videos to process
        """
        super().__init__(youtube)
        self.name = "deduplicate"
        self.help = "Remove duplicate videos from a playlist"
        self.playlist_id = playlist_id
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
        if not self.playlist_id:
            raise ValueError("Playlist ID is required")

        if self.resume_destination and not self.resume:
            raise ValueError("--resume-destination requires --resume")

        if self.resume:
            state_file = find_latest_state(self.playlist_id)
            if not state_file:
                raise ValueError(f"No recovery state found for playlist {self.playlist_id}")

            with RecoveryManager(self.playlist_id, self.name) as recovery:
                if self.resume_destination:
                    if self.resume_destination not in recovery.destination_metadata:
                        raise ValueError(
                            f"Destination {self.resume_destination} not found in recovery state"
                        )
                    progress = recovery.get_destination_progress(self.resume_destination)
                    if progress.get("completed", False):
                        raise ValueError(f"Destination {self.resume_destination} already completed")

    def _run(self) -> bool:
        """Execute the command.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Initialize recovery manager
            with RecoveryManager(
                playlist_id=self.playlist_id, operation_type=self.name
            ) as recovery:
                self.recovery = recovery

                # Load previous state if resuming
                if self.resume:
                    recovery.load_state()

                # Get videos from playlist
                try:
                    videos = self.youtube.get_playlist_videos(self.playlist_id)
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

                # Find duplicates
                seen = {}
                duplicates = []
                for video in remaining:
                    video_id = video["video_id"]
                    if video_id in seen:
                        if (
                            not self.resume
                            or self.retry_failed
                            or video_id not in recovery.processed_videos
                        ):
                            duplicates.append(video_id)
                    else:
                        seen[video_id] = True

                if not duplicates:
                    self._logger.info("No duplicates found")
                    return True

                self._logger.info("Found %d duplicates", len(duplicates))

                if self.dry_run:
                    for video_id in duplicates:
                        self._logger.info("Would remove duplicate: %s", video_id)
                    return True

                # Remove duplicates in batches
                success = True
                for i in range(0, len(duplicates), self.batch_size):
                    batch = duplicates[i : i + self.batch_size]
                    try:
                        removed = self.youtube.batch_remove_videos_from_playlist(
                            batch, self.playlist_id
                        )
                        for video_id in removed:
                            recovery.processed_videos.add(video_id)
                        for video_id in set(batch) - set(removed):
                            recovery.failed_videos.add(video_id)
                            success = False
                        recovery.save_state()
                    except Exception as e:
                        self._logger.error("Failed to remove duplicates: %s", str(e))
                        for video_id in batch:
                            recovery.failed_videos.add(video_id)
                        recovery.save_state()
                        return False

                return success

        except Exception as e:
            self._logger.error("Error deduplicating playlist: %s", str(e))
            return False
