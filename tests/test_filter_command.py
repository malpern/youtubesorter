"""Tests for the filter command."""

from unittest.mock import MagicMock, patch

import pytest

from src.youtubesorter.commands.filter import FilterCommand
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


@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_init(mock_recovery_cls, mock_youtube):
    """Test filter command initialization."""
    cmd = FilterCommand(
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


@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_validate_no_source(mock_recovery_cls, mock_youtube):
    """Test filter command validation with no source playlist."""
    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="",
        target_playlist="target_id",
    )
    try:
        cmd.validate()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Source playlist ID is required"


@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_validate_no_target(mock_recovery_cls, mock_youtube):
    """Test filter command validation with no target playlist."""
    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="",
    )
    try:
        cmd.validate()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Target playlist ID is required"


@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_validate_resume_destination_without_resume(mock_recovery_cls, mock_youtube):
    """Test filter command validation with resume destination but no resume."""
    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        resume_destination="dest",
    )
    try:
        cmd.validate()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "--resume-destination requires --resume"


@patch("src.youtubesorter.commands.filter.find_latest_state")
@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_validate_resume_no_state(mock_recovery_cls, mock_find_state, mock_youtube):
    """Test filter command validation with resume but no state."""
    mock_find_state.return_value = None

    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        resume=True,
    )
    try:
        cmd.validate()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "No recovery state found for playlist"


@patch("src.youtubesorter.commands.filter.find_latest_state")
@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_validate_resume_destination_not_found(
    mock_recovery_cls, mock_find_state, mock_youtube
):
    """Test filter command validation with resume destination not found."""
    mock_find_state.return_value = "state.json"
    mock_recovery = MagicMock()
    mock_recovery.destination_metadata = {}
    mock_recovery_cls.return_value = mock_recovery

    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        resume=True,
        resume_destination="dest",
    )
    try:
        cmd.validate()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Destination dest not found in recovery state"


@patch("src.youtubesorter.commands.filter.find_latest_state")
@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_validate_resume_destination_completed(
    mock_recovery_cls, mock_find_state, mock_youtube
):
    """Test filter command validation with completed resume destination."""
    mock_find_state.return_value = "state.json"
    mock_recovery = MagicMock()
    mock_recovery.destination_metadata = {"dest": {}}
    mock_recovery.get_destination_progress.return_value = {"completed": True}
    mock_recovery_cls.return_value = mock_recovery

    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        resume=True,
        resume_destination="dest",
    )
    try:
        cmd.validate()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Destination dest already completed"


@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_run_empty_playlist(mock_recovery_cls, mock_youtube):
    """Test filter command with empty playlist."""
    mock_recovery = MagicMock()
    mock_recovery_cls.return_value = mock_recovery
    mock_recovery.__enter__.return_value = mock_recovery
    mock_recovery.get_remaining_videos.return_value = []

    mock_youtube.get_playlist_videos.return_value = []

    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
    )
    assert cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_run_no_matches(mock_recovery_cls, mock_youtube):
    """Test filter command with no matching videos."""
    mock_recovery = MagicMock()
    mock_recovery_cls.return_value = mock_recovery
    mock_recovery.__enter__.return_value = mock_recovery
    mock_recovery.get_remaining_videos.return_value = [
        {"video_id": "vid1", "title": "Video 1"},
        {"video_id": "vid2", "title": "Video 2"},
    ]

    mock_youtube.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Video 1"},
        {"video_id": "vid2", "title": "Video 2"},
    ]

    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        filter_pattern="no match",
    )
    assert cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_run_with_matches(mock_recovery_cls, mock_youtube):
    """Test filter command with matching videos."""
    mock_recovery = MagicMock()
    mock_recovery_cls.return_value = mock_recovery
    mock_recovery.__enter__.return_value = mock_recovery
    mock_recovery.get_remaining_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
        {"video_id": "vid2", "title": "Video 2"},
    ]

    mock_youtube.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
        {"video_id": "vid2", "title": "Video 2"},
    ]
    mock_youtube.batch_move_videos_to_playlist.return_value = ["vid1"]

    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        filter_pattern="test",
    )
    assert cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        ["vid1"], "source_id", "target_id"
    )


@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_run_dry_run(mock_recovery_cls, mock_youtube):
    """Test filter command in dry run mode."""
    mock_recovery = MagicMock()
    mock_recovery_cls.return_value = mock_recovery
    mock_recovery.__enter__.return_value = mock_recovery
    mock_recovery.get_remaining_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
    ]

    mock_youtube.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
    ]

    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        filter_pattern="test",
        dry_run=True,
    )
    assert cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_run_with_resume(mock_recovery_cls, mock_youtube):
    """Test filter command with resume."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = {"vid1"}
    mock_recovery.failed_videos = set()
    mock_recovery_cls.return_value = mock_recovery
    mock_recovery.__enter__.return_value = mock_recovery
    mock_recovery.get_remaining_videos.return_value = [
        {"video_id": "vid2", "title": "Test Video 2"},
    ]

    mock_youtube.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
        {"video_id": "vid2", "title": "Test Video 2"},
    ]
    mock_youtube.batch_move_videos_to_playlist.return_value = ["vid2"]

    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        filter_pattern="test",
        resume=True,
    )
    assert cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        ["vid2"], "source_id", "target_id"
    )


@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_run_with_retry_failed(mock_recovery_cls, mock_youtube):
    """Test filter command with retry failed."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = {"vid1"}
    mock_recovery_cls.return_value = mock_recovery
    mock_recovery.__enter__.return_value = mock_recovery
    mock_recovery.get_remaining_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
        {"video_id": "vid2", "title": "Test Video 2"},
    ]

    mock_youtube.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
        {"video_id": "vid2", "title": "Test Video 2"},
    ]
    mock_youtube.batch_move_videos_to_playlist.return_value = ["vid1", "vid2"]

    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        filter_pattern="test",
        resume=True,
        retry_failed=True,
    )
    assert cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        ["vid1", "vid2"], "source_id", "target_id"
    )


@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_run_with_error(mock_recovery_cls, mock_youtube):
    """Test filter command with error."""
    mock_recovery = MagicMock()
    mock_recovery_cls.return_value = mock_recovery
    mock_recovery.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.side_effect = YouTubeError("Test error")

    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
    )
    assert not cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_run_with_move_error(mock_recovery_cls, mock_youtube):
    """Test filter command with move error."""
    mock_recovery = MagicMock()
    mock_recovery.failed_videos = set()
    mock_recovery_cls.return_value = mock_recovery
    mock_recovery.__enter__.return_value = mock_recovery
    mock_recovery.get_remaining_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
    ]

    mock_youtube.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
    ]
    mock_youtube.batch_move_videos_to_playlist.side_effect = YouTubeError("Test error")

    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        filter_pattern="test",
    )
    assert not cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        ["vid1"], "source_id", "target_id"
    )
    assert mock_recovery.failed_videos == {"vid1"}


@patch("src.youtubesorter.commands.filter.RecoveryManager")
def test_filter_command_run_with_partial_move_error(mock_recovery_cls, mock_youtube):
    """Test filter command with partial move error."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = set()
    mock_recovery_cls.return_value = mock_recovery
    mock_recovery.__enter__.return_value = mock_recovery
    mock_recovery.get_remaining_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
        {"video_id": "vid2", "title": "Test Video 2"},
    ]

    mock_youtube.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Test Video 1"},
        {"video_id": "vid2", "title": "Test Video 2"},
    ]
    mock_youtube.batch_move_videos_to_playlist.return_value = ["vid1"]  # Only vid1 succeeds

    cmd = FilterCommand(
        youtube=mock_youtube,
        source_playlist="source_id",
        target_playlist="target_id",
        filter_pattern="test",
    )
    assert not cmd._run()  # Should return False as there was a partial failure
    mock_youtube.get_playlist_videos.assert_called_once_with("source_id")
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        ["vid1", "vid2"], "source_id", "target_id"
    )
    assert mock_recovery.processed_videos == {"vid1"}
    assert mock_recovery.failed_videos == {"vid2"}
