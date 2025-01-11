"""Filter command for YouTube playlists."""

from typing import Optional

from ..core import YouTubeBase
from ..errors import YouTubeError
from ..logging_config import get_logger
from ..recovery import RecoveryManager
from ..utils import find_latest_state
from . import YouTubeCommand

# Get logger for this module
logger = get_logger(__name__)


class FilterCommand(YouTubeCommand):
    """Command for filtering videos between playlists."""

    def __init__(
        self,
        youtube: YouTubeBase,
        source_playlist: str,
        target_playlist: str,
        filter_pattern: Optional[str] = None,
        dry_run: bool = False,
        resume: bool = False,
        resume_destination: Optional[str] = None,
        retry_failed: bool = False,
        verbose: bool = False,
        limit: Optional[int] = None,
    ) -> None:
        """Initialize command.

        Args:
            youtube: YouTube API client
            source_playlist: Source playlist ID
            target_playlist: Target playlist ID
            filter_pattern: Optional filter pattern
            dry_run: Whether to perform a dry run
            resume: Whether to resume from previous state
            resume_destination: Optional destination to resume from
            retry_failed: Whether to retry failed videos
            verbose: Whether to show verbose output
            limit: Maximum number of videos to process
        """
        super().__init__(youtube)
        self.source_playlist = source_playlist
        self.target_playlist = target_playlist
        self.filter_pattern = filter_pattern
        self.dry_run = dry_run
        self.resume = resume
        self.resume_destination = resume_destination
        self.retry_failed = retry_failed
        self.verbose = verbose
        self.limit = limit
        self.recovery: Optional[RecoveryManager] = None

    def validate(self) -> None:
        """Validate command parameters."""
        if not self.source_playlist:
            raise ValueError("Source playlist ID is required")
        if not self.target_playlist:
            raise ValueError("Target playlist ID is required")

        if self.resume_destination and not self.resume:
            raise ValueError("--resume-destination requires --resume")

        if self.resume:
            # Only create a new recovery manager if one doesn't exist
            if not self.recovery:
                state_file = find_latest_state(self.source_playlist)
                if not state_file:
                    raise ValueError("No recovery state found for playlist")

                # Initialize recovery manager
                self.recovery = RecoveryManager(
                    self.source_playlist,
                    "filter",
                    state_file=state_file,
                )

            # Check destination state after initializing recovery manager
            if self.resume_destination:
                if (
                    not self.recovery
                    or self.resume_destination not in self.recovery.destination_metadata
                ):
                    raise ValueError(
                        f"Destination {self.resume_destination} not found in recovery state"
                    )
                progress = self.recovery.get_destination_progress(self.resume_destination)
                if progress and progress.get("completed", False):
                    raise ValueError(f"Destination {self.resume_destination} already completed")

    def _run(self) -> bool:
        """Run the filter command.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Initialize recovery state if needed
            if not self.recovery:
                self.recovery = RecoveryManager(self.source_playlist, "filter")

            # Get videos from source playlist
            videos = self.youtube.get_playlist_videos(self.source_playlist)
            if not videos:
                logger.info("No videos found in source playlist")
                return True

            # Filter videos and handle resume state
            filtered_videos = []
            for video in videos:
                video_id = video["video_id"]

                # Skip already processed videos when resuming
                if self.resume and video_id in self.recovery.processed_videos:
                    continue

                # Skip failed videos unless retry_failed is True
                if (
                    self.resume
                    and video_id in self.recovery.failed_videos
                    and not self.retry_failed
                ):
                    continue

                # Apply filter pattern
                if self.filter_pattern and self.filter_pattern.lower() in video["title"].lower():
                    filtered_videos.append(video_id)

            if not filtered_videos:
                logger.info("No videos to process")
                return True

            # Move filtered videos
            if not self.dry_run:
                try:
                    moved = self.youtube.batch_move_videos_to_playlist(
                        filtered_videos,
                        self.source_playlist,
                        self.target_playlist,
                    )

                    # Update recovery state
                    for video_id in filtered_videos:
                        if video_id in moved:
                            self.recovery.processed_videos.add(video_id)
                        else:
                            self.recovery.failed_videos.add(video_id)
                    self.recovery.save_state()

                    logger.info("Moved %d videos to target playlist", len(moved))
                    # Return False if any videos failed to move
                    return len(moved) == len(filtered_videos)
                except YouTubeError as e:
                    for video_id in filtered_videos:
                        self.recovery.failed_videos.add(video_id)
                    self.recovery.save_state()
                    logger.error("Filter command failed: %s", str(e))
                    return False
            else:
                logger.info("Would move %d videos to target playlist", len(filtered_videos))
                return True

        except Exception as e:
            logger.error("Filter command failed: %s", str(e))
            return False
