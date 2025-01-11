"""Tests for undo functionality."""

import json
import os
import time
import unittest
from unittest.mock import MagicMock, patch, call

from src.youtubesorter.undo import UndoManager, UndoOperation, undo_operation


class TestUndoManager(unittest.TestCase):
    """Test cases for undo manager."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_operation = UndoOperation(
            timestamp=time.time(),
            operation_type="distribute",
            source_playlists=["source1"],
            target_playlists=["target1", "target2"],
            was_move=True,
            videos=[{"id": "vid1", "title": "Video 1"}, {"id": "vid2", "title": "Video 2"}],
            target_mapping={"target1": ["vid1"], "target2": ["vid2"]},
        )
        self.manager = UndoManager("distribute")

    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.manager.state_file):
            os.remove(self.manager.state_file)

    def test_save_operation(self):
        """Test saving an operation."""
        self.manager.save_operation(self.test_operation)

        # Verify file exists and contains correct data
        self.assertTrue(os.path.exists(self.manager.state_file))
        with open(self.manager.state_file, "r") as f:
            state = json.load(f)
            self.assertEqual(state["operation_type"], "distribute")
            self.assertEqual(state["source_playlists"], ["source1"])
            self.assertEqual(state["target_playlists"], ["target1", "target2"])
            self.assertTrue(state["was_move"])
            self.assertEqual(len(state["videos"]), 2)
            self.assertEqual(len(state["target_mapping"]), 2)

    def test_save_operation_type_mismatch(self):
        """Test error on operation type mismatch."""
        # Create operation with different type
        operation = UndoOperation(
            timestamp=time.time(),
            operation_type="consolidate",
            source_playlists=["source1"],
            target_playlists=["target1"],
            was_move=True,
            videos=[{"id": "vid1", "title": "Video 1"}],
            target_mapping={"target1": ["vid1"]},
        )

        # Verify error is raised
        with self.assertRaises(ValueError):
            self.manager.save_operation(operation)

    def test_get_last_operation(self):
        """Test retrieving last operation."""
        # Save operation
        self.manager.save_operation(self.test_operation)

        # Get operation back
        operation = self.manager.get_last_operation()

        # Verify operation matches
        self.assertEqual(operation.operation_type, self.test_operation.operation_type)
        self.assertEqual(operation.source_playlists, self.test_operation.source_playlists)
        self.assertEqual(operation.target_playlists, self.test_operation.target_playlists)
        self.assertEqual(operation.was_move, self.test_operation.was_move)
        self.assertEqual(operation.videos, self.test_operation.videos)
        self.assertEqual(operation.target_mapping, self.test_operation.target_mapping)

    def test_get_last_operation_no_file(self):
        """Test retrieving operation when no file exists."""
        operation = self.manager.get_last_operation()
        self.assertIsNone(operation)

    def test_get_last_operation_invalid_json(self):
        """Test retrieving operation with invalid JSON."""
        # Write invalid JSON to file
        with open(self.manager.state_file, "w") as f:
            f.write("invalid json")

        operation = self.manager.get_last_operation()
        self.assertIsNone(operation)

    def test_get_last_operation_missing_fields(self):
        """Test retrieving operation with missing required fields."""
        # Write state with missing fields
        state = {
            "timestamp": time.time(),
            "operation_type": "distribute",
            # Missing other required fields
        }
        with open(self.manager.state_file, "w") as f:
            json.dump(state, f)

        operation = self.manager.get_last_operation()
        self.assertIsNone(operation)

    def test_clear_state(self):
        """Test clearing undo state."""
        # Save operation
        self.manager.save_operation(self.test_operation)
        self.assertTrue(os.path.exists(self.manager.state_file))

        # Clear state
        self.manager.clear_state()
        self.assertFalse(os.path.exists(self.manager.state_file))

    def test_clear_state_no_file(self):
        """Test clearing state when no file exists."""
        self.manager.clear_state()  # Should not raise error

    def test_clear_state_permission_error(self):
        """Test clearing state with permission error."""
        self.manager.save_operation(self.test_operation)

        with patch("os.remove", side_effect=PermissionError("Permission denied")):
            self.manager.clear_state()
            self.assertTrue(os.path.exists(self.manager.state_file))

    def test_load_state_error(self):
        """Test error handling in _load_state."""
        with patch("builtins.open", side_effect=Exception("Test error")):
            self.manager._load_state()
            self.assertFalse(hasattr(self.manager, "state"))

    def test_save_state_error(self):
        """Test error handling in _save_state."""
        self.manager.state = {"test": "data"}
        with patch("builtins.open", side_effect=Exception("Test error")):
            self.manager._save_state()


class TestUndoOperation(unittest.TestCase):
    """Test cases for undo_operation function."""

    def setUp(self):
        """Set up test fixtures."""
        self.youtube = MagicMock()
        self.operation = UndoOperation(
            timestamp=time.time(),
            operation_type="distribute",
            source_playlists=["source1"],
            target_playlists=["target1", "target2"],
            was_move=True,
            videos=[{"id": "vid1", "title": "Video 1"}, {"id": "vid2", "title": "Video 2"}],
            target_mapping={"target1": ["vid1"], "target2": ["vid2"]},
        )

    def test_undo_operation_dry_run(self):
        """Test dry run of undo operation."""
        result = undo_operation(self.youtube, self.operation, dry_run=True)
        self.assertTrue(result)
        self.youtube.remove_video_from_playlist.assert_not_called()
        self.youtube.add_video_to_playlist.assert_not_called()

    def test_undo_move_operation(self):
        """Test undoing a move operation."""
        result = undo_operation(self.youtube, self.operation)
        self.assertTrue(result)

        # Verify videos were removed from target playlists
        self.youtube.remove_video_from_playlist.assert_has_calls(
            [call("vid1", "target1"), call("vid2", "target2")], any_order=True
        )

        # Verify videos were added back to source playlists
        self.youtube.add_video_to_playlist.assert_has_calls(
            [call("vid1", "source1"), call("vid2", "source1")], any_order=True
        )

    def test_undo_copy_operation(self):
        """Test undoing a copy operation."""
        self.operation.was_move = False
        result = undo_operation(self.youtube, self.operation)
        self.assertTrue(result)

        # Verify videos were only removed from target playlists
        self.youtube.remove_video_from_playlist.assert_has_calls(
            [call("vid1", "target1"), call("vid2", "target2")], any_order=True
        )
        self.youtube.add_video_to_playlist.assert_not_called()

    def test_undo_operation_api_error(self):
        """Test handling of API errors during undo."""
        self.youtube.remove_video_from_playlist.side_effect = Exception("API Error")
        result = undo_operation(self.youtube, self.operation)
        self.assertFalse(result)

    def test_undo_operation_partial_mapping(self):
        """Test undoing operation with partial target mapping."""
        # Create operation with only one video mapped
        self.operation = UndoOperation(
            timestamp=time.time(),
            operation_type="distribute",
            source_playlists=["source1"],
            target_playlists=["target1", "target2"],
            was_move=True,
            videos=[{"id": "vid1", "title": "Video 1"}],
            target_mapping={"target1": ["vid1"]},
        )
        result = undo_operation(self.youtube, self.operation)
        self.assertTrue(result)

        # Verify only mapped video was processed
        self.youtube.remove_video_from_playlist.assert_called_once_with("vid1", "target1")
        self.youtube.add_video_to_playlist.assert_called_once_with("vid1", "source1")


if __name__ == "__main__":
    unittest.main()
