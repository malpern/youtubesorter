"""Tests for the move command."""

from unittest.mock import MagicMock, patch

import pytest

from src.youtubesorter.commands.move import MoveCommand
from src.youtubesorter.errors import YouTubeError
from src.youtubesorter.core import YouTubeBase


class MockYouTubeBase(YouTubeBase):
    """Mock YouTube base class."""

    def __init__(self):
        """Initialize mock."""
        self.get_playlist_videos = MagicMock()
        self.batch_add_videos_to_playlist = MagicMock()
        self.batch_move_videos_to_playlist = MagicMock()


@pytest.fixture
def mock_youtube():
    """Create mock YouTube client."""
    return MockYouTubeBase()


def test_move_command_init(mock_youtube):
    """Test move command initialization."""
    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        filter_pattern="test pattern",
    )
    assert cmd.source_playlist == "source_id"
    assert cmd.target_playlist == "target_id"
    assert cmd.filter_pattern == "test pattern"
    assert not cmd.dry_run
    assert not cmd.resume
    assert not cmd.retry_failed
    assert not cmd.verbose
    assert cmd.limit is None


def test_move_command_validate_no_source(mock_youtube):
    """Test move command validation with no source playlist."""
    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="",
        target_playlist="target_id",
    )
    with pytest.raises(ValueError, match="Source playlist ID is required"):
        cmd.validate()


def test_move_command_validate_no_target(mock_youtube):
    """Test move command validation with no target playlist."""
    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="",
    )
    with pytest.raises(ValueError, match="Target playlist ID is required"):
        cmd.validate()


def test_move_command_validate_resume_destination_without_resume(mock_youtube):
    """Test move command validation with resume destination but no resume."""
    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        resume_destination="dest",
    )
    with pytest.raises(ValueError, match="--resume-destination requires --resume"):
        cmd.validate()


@patch("src.youtubesorter.commands.move.find_latest_state")
def test_move_command_validate_resume_no_state(mock_find_state, mock_youtube):
    """Test move command validation with resume but no state."""
    mock_find_state.return_value = None

    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        resume=True,
    )
    with pytest.raises(ValueError, match="No recovery state found for playlist"):
        cmd.validate()


@patch("src.youtubesorter.commands.move.find_latest_state")
@patch("src.youtubesorter.commands.move.RecoveryManager")
def test_move_command_validate_resume_destination_not_found(
    mock_recovery_cls, mock_find_state, mock_youtube
):
    """Test move command validation with resume destination not found."""
    mock_find_state.return_value = "state.json"
    mock_recovery = MagicMock()
    mock_recovery.destination_metadata = {}
    mock_recovery_cls.return_value = mock_recovery

    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        resume=True,
        resume_destination="dest",
    )
    with pytest.raises(ValueError, match="Destination dest not found in recovery state"):
        cmd.validate()


@patch("src.youtubesorter.commands.move.find_latest_state")
@patch("src.youtubesorter.commands.move.RecoveryManager")
def test_move_command_validate_resume_destination_completed(
    mock_recovery_cls, mock_find_state, mock_youtube
):
    """Test move command validation with completed resume destination."""
    mock_find_state.return_value = "state.json"
    mock_recovery = MagicMock()
    mock_recovery.destination_metadata = {"dest": {}}
    mock_recovery.get_destination_progress.return_value = {"completed": True}
    mock_recovery_cls.return_value = mock_recovery

    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        resume=True,
        resume_destination="dest",
    )
    with pytest.raises(ValueError, match="Destination dest already completed"):
        cmd.validate()


def test_move_command_run_empty_playlist(mock_youtube):
    """Test move command with empty playlist."""
    mock_youtube.get_playlist_videos.return_value = []

    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
    )
    assert cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


def test_move_command_run_with_videos(mock_youtube):
    """Test move command with videos."""
    mock_youtube.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
        {"video_id": "vid2", "title": "Video 2"},
    ]
    mock_youtube.batch_move_videos_to_playlist.return_value = ["vid1", "vid2"]

    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
    )
    assert cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        ["vid1", "vid2"], "source_id", "target_id"
    )


def test_move_command_run_dry_run(mock_youtube):
    """Test move command in dry run mode."""
    mock_youtube.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
    ]

    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        dry_run=True,
    )
    assert cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


@patch("src.youtubesorter.commands.move.RecoveryManager")
def test_move_command_run_with_resume(mock_recovery_cls, mock_youtube):
    """Test move command with resume."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = {"vid1"}
    mock_recovery.failed_videos = set()
    mock_recovery_cls.return_value = mock_recovery
    mock_recovery.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
        {"video_id": "vid2", "title": "Test Video 2"},
    ]
    mock_youtube.batch_move_videos_to_playlist.return_value = ["vid2"]

    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        resume=True,
    )
    assert cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        ["vid2"], "source_id", "target_id"
    )


@patch("src.youtubesorter.commands.move.RecoveryManager")
def test_move_command_run_with_retry_failed(mock_recovery_cls, mock_youtube):
    """Test move command with retry failed."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = {"vid1"}
    mock_recovery_cls.return_value = mock_recovery
    mock_recovery.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
        {"video_id": "vid2", "title": "Test Video 2"},
    ]
    mock_youtube.batch_move_videos_to_playlist.return_value = ["vid1", "vid2"]

    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        resume=True,
        retry_failed=True,
    )
    assert cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        ["vid1", "vid2"], "source_id", "target_id"
    )


def test_move_command_run_with_error(mock_youtube):
    """Test move command with error."""
    mock_youtube.get_playlist_videos.side_effect = YouTubeError("Test error")

    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
    )
    assert not cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


@patch("src.youtubesorter.commands.move.RecoveryManager")
def test_move_command_run_with_move_error(mock_recovery_cls, mock_youtube):
    """Test move command with move error."""
    mock_recovery = MagicMock()
    mock_recovery.failed_videos = set()
    mock_recovery_cls.return_value = mock_recovery
    mock_recovery.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
    ]
    mock_youtube.batch_move_videos_to_playlist.side_effect = YouTubeError("Test error")

    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        resume=True,
    )
    assert not cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        ["vid1"], "source_id", "target_id"
    )
    assert mock_recovery.failed_videos == {"vid1"}


@patch("src.youtubesorter.commands.move.RecoveryManager")
def test_move_command_run_with_partial_move_error(mock_recovery_cls, mock_youtube):
    """Test move command with partial move error."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = set()
    mock_recovery_cls.return_value = mock_recovery
    mock_recovery.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
        {"video_id": "vid2", "title": "Test Video 2"},
    ]
    mock_youtube.batch_move_videos_to_playlist.return_value = ["vid1"]  # Only vid1 succeeds

    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        resume=True,
    )
    assert cmd._run()  # Should still return True as it's a partial success
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        ["vid1", "vid2"], "source_id", "target_id"
    )
    assert mock_recovery.processed_videos == {"vid1"}
    assert mock_recovery.failed_videos == {"vid2"}
