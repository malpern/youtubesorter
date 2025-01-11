"""Tests for the recovery manager."""

import json
import os
from unittest.mock import MagicMock, patch, mock_open
import pytest

from src.youtubesorter.recovery import RecoveryManager


@pytest.fixture
def recovery_manager():
    """Create a recovery manager instance."""
    manager = RecoveryManager(
        playlist_id="playlist123",
        operation_type="test",
        state_file="data/recovery/test_recovery.json",
    )
    yield manager
    # Clean up state file after test
    if os.path.exists("data/recovery/test_recovery.json"):
        os.remove("data/recovery/test_recovery.json")


def test_recovery_manager_init():
    """Test recovery manager initialization."""
    manager = RecoveryManager(
        playlist_id="playlist123",
        operation_type="test",
    )
    assert manager.playlist_id == "playlist123"
    assert manager.operation_type == "test"
    assert manager.state_file == "data/recovery/recovery_playlist123_test.json"
    assert manager.destination_metadata == {}
    assert manager.destination_progress == {}
    assert manager.videos == {}
    assert manager.video_assignments == {}
    assert manager.processed_videos == set()
    assert manager.failed_videos == set()


def test_recovery_manager_context_manager(recovery_manager):
    """Test recovery manager context manager."""
    with patch("builtins.open", mock_open()) as mock_file:
        with recovery_manager:
            pass
        mock_file.assert_called_once_with("data/recovery/test_recovery.json", "w", encoding="utf-8")


def test_recovery_manager_load_state():
    """Test loading recovery state from file."""
    state = {
        "playlist_id": "playlist123",
        "operation_type": "test",
        "destination_metadata": {"dest1": {"name": "Test"}},
        "destination_progress": {
            "dest1": {
                "completed": False,
                "processed_videos": ["vid1"],
                "failed_videos": [],
                "failure_count": 0,
            }
        },
        "videos": {"vid1": {"title": "Test"}},
        "video_assignments": {"vid1": "dest1"},
        "processed_videos": ["vid1"],
        "failed_videos": [],
    }
    with patch("builtins.open", mock_open(read_data=json.dumps(state))):
        manager = RecoveryManager(
            playlist_id="playlist123",
            operation_type="test",
        )
        manager.load_state()
        assert manager.destination_metadata == {"dest1": {"name": "Test"}}
        assert manager.destination_progress == {
            "dest1": {
                "completed": False,
                "processed_videos": ["vid1"],
                "failed_videos": [],
                "failure_count": 0,
            }
        }
        assert manager.videos == {"vid1": {"title": "Test"}}
        assert manager.video_assignments == {"vid1": "dest1"}
        assert manager.processed_videos == {"vid1"}
        assert manager.failed_videos == set()


def test_recovery_manager_save_state(recovery_manager):
    """Test saving recovery state to file."""
    recovery_manager.destination_metadata = {"dest1": {"name": "Test"}}
    recovery_manager.destination_progress = {
        "dest1": {
            "completed": False,
            "processed_videos": ["vid1"],
            "failed_videos": [],
            "failure_count": 0,
        }
    }
    recovery_manager.videos = {"vid1": {"title": "Test"}}
    recovery_manager.video_assignments = {"vid1": "dest1"}
    recovery_manager.processed_videos = {"vid1"}
    recovery_manager.failed_videos = set()

    mock_file = mock_open()
    with patch("builtins.open", mock_file):
        recovery_manager.save_state()
        mock_file.assert_called_once_with("data/recovery/test_recovery.json", "w", encoding="utf-8")
        # Get the actual data written to the file
        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        # Parse it back to compare
        actual_state = json.loads(written_data)
        expected_state = {
            "playlist_id": "playlist123",
            "operation_type": "test",
            "destination_metadata": {"dest1": {"name": "Test"}},
            "destination_progress": {
                "dest1": {
                    "completed": False,
                    "processed_videos": ["vid1"],
                    "failed_videos": [],
                    "failure_count": 0,
                }
            },
            "videos": {"vid1": {"title": "Test"}},
            "video_assignments": {"vid1": "dest1"},
            "processed_videos": ["vid1"],
            "failed_videos": [],
        }
        assert actual_state == expected_state


def test_recovery_manager_add_destination(recovery_manager):
    """Test adding a destination."""
    metadata = {"name": "Test Destination"}
    recovery_manager.add_destination("dest1", metadata)
    assert recovery_manager.destination_metadata["dest1"] == metadata
    assert recovery_manager.destination_progress["dest1"] == {
        "completed": False,
        "processed_videos": [],
        "failed_videos": [],
        "failure_count": 0,
    }


def test_recovery_manager_get_destination_metadata(recovery_manager):
    """Test getting destination metadata."""
    metadata = {"name": "Test Destination"}
    recovery_manager.destination_metadata["dest1"] = metadata
    assert recovery_manager.get_destination_metadata("dest1") == metadata
    assert recovery_manager.get_destination_metadata("nonexistent") is None


def test_recovery_manager_get_destination_progress(recovery_manager):
    """Test getting destination progress."""
    progress = {
        "completed": False,
        "processed_videos": [],
        "failed_videos": [],
        "failure_count": 0,
    }
    recovery_manager.destination_progress["dest1"] = progress
    assert recovery_manager.get_destination_progress("dest1") == progress
    assert recovery_manager.get_destination_progress("nonexistent") is None


def test_recovery_manager_mark_destination_complete(recovery_manager):
    """Test marking a destination as complete."""
    recovery_manager.destination_progress["dest1"] = {
        "completed": False,
        "processed_videos": [],
        "failed_videos": [],
        "failure_count": 0,
    }
    recovery_manager.mark_destination_complete("dest1")
    assert recovery_manager.destination_progress["dest1"]["completed"] is True


def test_recovery_manager_get_incomplete_destinations(recovery_manager):
    """Test getting incomplete destinations."""
    recovery_manager.destination_progress = {
        "dest1": {"completed": False},
        "dest2": {"completed": True},
        "dest3": {"completed": False},
    }
    incomplete = recovery_manager.get_incomplete_destinations()
    assert set(incomplete) == {"dest1", "dest3"}


def test_recovery_manager_get_remaining_videos(recovery_manager):
    """Test getting remaining videos."""
    recovery_manager.videos = {
        "vid1": {"title": "Video 1"},
        "vid2": {"title": "Video 2"},
        "vid3": {"title": "Video 3"},
    }
    recovery_manager.destination_progress = {
        "dest1": {
            "processed_videos": ["vid1"],
            "failed_videos": ["vid2"],
        }
    }
    remaining = recovery_manager.get_remaining_videos()
    assert set(remaining) == {"vid3"}


def test_recovery_manager_get_videos_for_destination(recovery_manager):
    """Test getting videos for a destination."""
    recovery_manager.destination_progress["dest1"] = {
        "processed_videos": ["vid1", "vid2"],
        "failed_videos": ["vid3"],
    }
    videos = recovery_manager.get_videos_for_destination("dest1")
    assert len(videos) == 2
    assert all(isinstance(v, dict) for v in videos)
    assert all("video_id" in v for v in videos)
    assert {v["video_id"] for v in videos} == {"vid1", "vid2"}


def test_recovery_manager_assign_video_success(recovery_manager):
    """Test assigning a video successfully."""
    video_data = {"video_id": "vid1", "title": "Test Video"}
    recovery_manager.destination_progress["dest1"] = {
        "processed_videos": [],
        "failed_videos": [],
        "failure_count": 0,
    }
    recovery_manager.assign_video("vid1", "dest1", video_data, success=True)
    assert recovery_manager.videos["vid1"] == video_data
    assert "vid1" in recovery_manager.destination_progress["dest1"]["processed_videos"]
    assert "vid1" not in recovery_manager.destination_progress["dest1"]["failed_videos"]
    assert "vid1" in recovery_manager.processed_videos
    assert "vid1" not in recovery_manager.failed_videos


def test_recovery_manager_assign_video_failure(recovery_manager):
    """Test assigning a video with failure."""
    video_data = {"video_id": "vid1", "title": "Test Video"}
    recovery_manager.destination_progress["dest1"] = {
        "processed_videos": [],
        "failed_videos": [],
        "failure_count": 0,
    }
    recovery_manager.assign_video("vid1", "dest1", video_data, success=False)
    assert recovery_manager.videos["vid1"] == video_data
    assert "vid1" not in recovery_manager.destination_progress["dest1"]["processed_videos"]
    assert "vid1" in recovery_manager.destination_progress["dest1"]["failed_videos"]
    assert recovery_manager.destination_progress["dest1"]["failure_count"] == 1
    assert "vid1" not in recovery_manager.processed_videos
    assert "vid1" in recovery_manager.failed_videos


def test_recovery_manager_backward_compatibility(recovery_manager):
    """Test backward compatibility with old state format."""
    old_state = {
        "playlist_id": "playlist123",
        "operation_type": "test",
        "video_assignments": {"vid1": "dest1"},
        "processed_videos": ["vid1"],
        "failed_videos": ["vid2"],
    }
    with patch("builtins.open", mock_open(read_data=json.dumps(old_state))):
        recovery_manager.load_state()
        assert recovery_manager.video_assignments == {"vid1": "dest1"}
        assert recovery_manager.processed_videos == {"vid1"}
        assert recovery_manager.failed_videos == {"vid2"}


def test_recovery_manager_load_state_error():
    """Test error handling when loading state."""
    with patch("builtins.open", mock_open()) as mock_file:
        mock_file.side_effect = Exception("Test error")
        manager = RecoveryManager(
            playlist_id="playlist123",
            operation_type="test",
        )
        manager.load_state()  # Should not raise exception
        assert manager.destination_metadata == {}


def test_recovery_manager_save_state_error(recovery_manager):
    """Test error handling when saving state."""
    with patch("builtins.open", mock_open()) as mock_file:
        mock_file.side_effect = Exception("Test error")
        recovery_manager.save_state()  # Should not raise exception
