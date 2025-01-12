"""Manages recovery state for interrupted operations."""

import json
import logging
import os
from typing import Dict, List, Optional, Set

from . import errors
from .api import YouTubeAPI
from .config import RECOVERY_DIR
from .logging_config import get_logger

logger = get_logger(__name__)


class RecoveryManager:
    """Manages recovery state for interrupted operations."""

    def __init__(
        self,
        playlist_id: str,
        operation_type: str,
        state_file: Optional[str] = None,
    ) -> None:
        """Initialize recovery manager.

        Args:
            playlist_id: Source playlist ID
            operation_type: Type of operation (move, filter, etc.)
            state_file: Path to state file
        """
        self.playlist_id = playlist_id
        self.operation_type = operation_type
        if state_file is None:
            os.makedirs(RECOVERY_DIR, exist_ok=True)
            state_file = os.path.join(RECOVERY_DIR, f"recovery_{playlist_id}_{operation_type}.json")
        self.state_file = state_file
        self.destination_metadata: Dict = {}
        self.destination_progress: Dict = {}
        self.videos: Dict = {}
        self.video_assignments: Dict[str, str] = {}  # For backward compatibility
        self.processed_videos: Set[str] = set()  # For backward compatibility
        self.failed_videos: Set[str] = set()  # For backward compatibility

        if os.path.exists(self.state_file):
            self.load_state()

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        self.save_state()
        return False  # Don't suppress exceptions

    def load_state(self) -> None:
        """Load recovery state from file."""
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                self.destination_metadata = state.get("destination_metadata", {})
                self.destination_progress = state.get("destination_progress", {})
                self.videos = state.get("videos", {})

                # Handle backward compatibility
                if "video_assignments" in state:
                    self.video_assignments = state["video_assignments"]
                if "processed_videos" in state:
                    self.processed_videos = set(state["processed_videos"])
                if "failed_videos" in state:
                    self.failed_videos = set(state["failed_videos"])

                # Convert old format to new format if needed
                if self.processed_videos and not any(
                    "processed_videos" in p for p in self.destination_progress.values()
                ):
                    for dest_id in self.destination_progress:
                        self.destination_progress[dest_id]["processed_videos"] = list(
                            self.processed_videos
                        )

        except Exception as e:
            logger.error("Error loading recovery state: %s", str(e))

    def save_state(self) -> None:
        """Save recovery state to file."""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            state = {
                "playlist_id": self.playlist_id,
                "operation_type": self.operation_type,
                "destination_metadata": self.destination_metadata,
                "destination_progress": self.destination_progress,
                "videos": self.videos,
                "video_assignments": self.video_assignments,  # For backward compatibility
                "processed_videos": list(self.processed_videos),  # For backward compatibility
                "failed_videos": list(self.failed_videos),  # For backward compatibility
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error("Error saving recovery state: %s", str(e))

    def add_destination(self, dest_id: str, metadata: Dict) -> None:
        """Add a destination to track.

        Args:
            dest_id: Destination ID
            metadata: Destination metadata
        """
        self.destination_metadata[dest_id] = metadata
        if dest_id not in self.destination_progress:
            self.destination_progress[dest_id] = {
                "completed": False,
                "processed_videos": [],
                "failed_videos": [],
                "failure_count": 0,
            }
        self.save_state()

    def get_destination_metadata(self, dest_id: str) -> Optional[Dict]:
        """Get metadata for a destination.

        Args:
            dest_id: Destination ID

        Returns:
            Destination metadata if found, None otherwise
        """
        return self.destination_metadata.get(dest_id)

    def get_destination_progress(self, dest_id: str) -> Optional[Dict]:
        """Get progress for a destination.

        Args:
            dest_id: Destination ID

        Returns:
            Destination progress if found, None otherwise
        """
        return self.destination_progress.get(dest_id)

    def mark_destination_complete(self, dest_id: str) -> None:
        """Mark a destination as complete.

        Args:
            dest_id: Destination ID
        """
        if dest_id in self.destination_progress:
            self.destination_progress[dest_id]["completed"] = True
            self.save_state()

    def get_incomplete_destinations(self) -> List[str]:
        """Get list of incomplete destinations.

        Returns:
            List of destination IDs that are not complete
        """
        return [
            dest_id
            for dest_id, progress in self.destination_progress.items()
            if not progress.get("completed", False)
        ]

    def get_remaining_videos(
        self, api: Optional[YouTubeAPI] = None, use_cache: bool = True
    ) -> List[str]:
        """Get list of videos not yet processed for any destination.

        Args:
            api: Optional YouTube API client (for backward compatibility)
            use_cache: Whether to use cached playlist data (for backward compatibility)

        Returns:
            List of video IDs not yet processed
        """
        all_videos = set(self.videos.keys())
        processed = set()
        failed = set()

        for progress in self.destination_progress.values():
            processed.update(progress.get("processed_videos", []))
            failed.update(progress.get("failed_videos", []))

        # For backward compatibility
        processed.update(self.processed_videos)
        failed.update(self.failed_videos)

        return list(all_videos - processed - failed)

    def get_videos_for_destination(self, dest_id: str) -> List[Dict]:
        """Get list of videos assigned to a destination.

        Args:
            dest_id: Destination ID

        Returns:
            List of video data for videos assigned to the destination
        """
        if dest_id not in self.destination_progress:
            return []

        progress = self.destination_progress[dest_id]
        processed = progress.get("processed_videos", [])
        return [
            {"video_id": video_id} for video_id in processed
        ]  # Minimal video data for compatibility

    def assign_video(
        self, video_id: str, dest_id: str, video_data: Optional[Dict] = None, success: bool = True
    ) -> None:
        """Assign a video to a destination.

        Args:
            video_id: Video ID
            dest_id: Destination ID
            video_data: Optional video metadata
            success: Whether assignment was successful (for backward compatibility)
        """
        if video_data:
            self.videos[video_id] = video_data
        else:
            self.videos[video_id] = {"video_id": video_id}  # Minimal video data

        if success:
            if dest_id in self.destination_progress:
                progress = self.destination_progress[dest_id]
                if video_id not in progress["processed_videos"]:
                    progress["processed_videos"].append(video_id)
                if video_id in progress["failed_videos"]:
                    progress["failed_videos"].remove(video_id)

            # For backward compatibility
            self.video_assignments[video_id] = dest_id
            self.processed_videos.add(video_id)
            if video_id in self.failed_videos:
                self.failed_videos.remove(video_id)
        else:
            if dest_id in self.destination_progress:
                progress = self.destination_progress[dest_id]
                if video_id not in progress["failed_videos"]:
                    progress["failed_videos"].append(video_id)
                if video_id in progress["processed_videos"]:
                    progress["processed_videos"].remove(video_id)
                progress["failure_count"] += 1

            # For backward compatibility
            self.failed_videos.add(video_id)
            if video_id in self.processed_videos:
                self.processed_videos.remove(video_id)

        self.save_state()

    def mark_video_failed(self, video_id: str, dest_id: str) -> None:
        """Mark a video as failed for a destination.

        Args:
            video_id: Video ID
            dest_id: Destination ID
        """
        self.assign_video(video_id, dest_id, success=False)
