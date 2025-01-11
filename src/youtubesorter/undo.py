"""Undo operation management."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .logging_config import get_logger

logger = get_logger(__name__)

UNDO_DIR = Path.home() / ".youtubesorter" / "undo"


@dataclass
class UndoOperation:
    """Class representing an operation that can be undone."""

    timestamp: float
    operation_type: str  # 'distribute' or 'consolidate'
    source_playlists: List[str]
    target_playlists: List[str]
    was_move: bool
    videos: List[Dict]  # List of video info dicts
    target_mapping: Dict[str, List[str]]  # Maps target playlist to video IDs


class UndoManager:
    """Manages undo operations."""

    def __init__(self, operation_type: str):
        """Initialize undo manager.

        Args:
            operation_type: Type of operation ('distribute' or 'consolidate')
        """
        self.operation_type = operation_type
        self.state_file = f".youtubesorter_{operation_type}_undo.json"

    def save_operation(self, operation: UndoOperation) -> None:
        """Save an operation to the undo state file.

        Args:
            operation: The operation to save
        """
        if operation.operation_type != self.operation_type:
            raise ValueError(
                f"Operation type mismatch: {operation.operation_type} != {self.operation_type}"
            )

        state = {
            "timestamp": operation.timestamp,
            "operation_type": operation.operation_type,
            "source_playlists": operation.source_playlists,
            "target_playlists": operation.target_playlists,
            "was_move": operation.was_move,
            "videos": operation.videos,
            "target_mapping": operation.target_mapping,
        }

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        logger.info("Saved undo operation to %s", self.state_file)

    def get_last_operation(self) -> Optional[UndoOperation]:
        """Get the last operation from the undo state file.

        Returns:
            The last operation if one exists, None otherwise
        """
        if not os.path.exists(self.state_file):
            return None

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            return UndoOperation(
                timestamp=state["timestamp"],
                operation_type=state["operation_type"],
                source_playlists=state["source_playlists"],
                target_playlists=state["target_playlists"],
                was_move=state["was_move"],
                videos=state["videos"],
                target_mapping=state["target_mapping"],
            )
        except Exception as e:
            logger.error("Error loading undo operation: %s", str(e))
            return None

    def clear_state(self) -> None:
        """Clear the undo state file."""
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
                logger.info("Cleared undo state file %s", self.state_file)
            except Exception as e:
                logger.error("Error clearing undo state: %s", str(e))

    def _load_state(self) -> None:
        """Load undo state from file."""
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                self.state = json.load(f)
        except Exception as e:
            logger.error("Error loading undo state: %s", str(e))

    def _save_state(self) -> None:
        """Save undo state to file."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error("Error saving undo state: %s", str(e))


def undo_operation(youtube, operation: UndoOperation, dry_run: bool = False) -> bool:
    """Undo an operation.

    Args:
        youtube: YouTube API client
        operation: Operation to undo
        dry_run: Whether to perform a dry run

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if dry_run:
            logger.info("Would undo %s operation:", operation.operation_type)
            logger.info("  Source playlists: %s", ", ".join(operation.source_playlists))
            logger.info("  Target playlists: %s", ", ".join(operation.target_playlists))
            logger.info("  Videos: %d", len(operation.videos))
            logger.info("  Was move: %s", operation.was_move)
            return True

        # Move videos back to source playlists
        if operation.was_move:
            for video in operation.videos:
                video_id = video["id"]
                # Remove from target playlists
                for target_id in operation.target_playlists:
                    if (
                        target_id in operation.target_mapping
                        and video_id in operation.target_mapping[target_id]
                    ):
                        youtube.remove_video_from_playlist(video_id, target_id)

                # Add back to source playlists
                for source_id in operation.source_playlists:
                    youtube.add_video_to_playlist(video_id, source_id)
        else:
            # Just remove from target playlists
            for video in operation.videos:
                video_id = video["id"]
                for target_id in operation.target_playlists:
                    if (
                        target_id in operation.target_mapping
                        and video_id in operation.target_mapping[target_id]
                    ):
                        youtube.remove_video_from_playlist(video_id, target_id)

        logger.info("Successfully undid %s operation", operation.operation_type)
        return True

    except Exception as e:
        logger.error("Error undoing operation: %s", str(e))
        return False
