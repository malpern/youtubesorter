"""Tests for the deduplicate command."""

from unittest.mock import MagicMock, patch
import pytest

from src.youtubesorter.commands.deduplicate import DeduplicateCommand
from src.youtubesorter.errors import YouTubeError
from src.youtubesorter.core import YouTubeBase


class MockYouTubeBase(YouTubeBase):
    """Mock YouTube base class."""

    def __init__(self):
        """Initialize mock."""
        self.get_playlist_videos = MagicMock()
        self.batch_remove_videos_from_playlist = MagicMock()


@pytest.fixture
def mock_youtube():
    """Create mock YouTube client."""
    return MockYouTubeBase()


def test_deduplicate_command_init(mock_youtube):
    """Test deduplicate command initialization."""
    cmd = DeduplicateCommand(
        youtube=mock_youtube,
        playlist_id="playlist123",
    )
    assert cmd.youtube == mock_youtube
    assert cmd.name == "deduplicate"
    assert cmd.help == "Remove duplicate videos from a playlist"
    assert cmd.playlist_id == "playlist123"
    assert not cmd.resume
    assert not cmd.resume_destination
    assert not cmd.retry_failed
    assert not cmd.dry_run
    assert cmd.limit is None


def test_deduplicate_command_validate_missing_playlist(mock_youtube):
    """Test validate with missing playlist ID."""
    with pytest.raises(ValueError, match="Playlist ID is required"):
        cmd = DeduplicateCommand(
            youtube=mock_youtube,
            playlist_id="",
        )
        cmd.validate()


def test_deduplicate_command_validate_resume_destination_without_resume(mock_youtube):
    """Test validate with resume destination but no resume flag."""
    with pytest.raises(ValueError, match="--resume-destination requires --resume"):
        cmd = DeduplicateCommand(
            youtube=mock_youtube,
            playlist_id="playlist123",
            resume_destination="dest1",
        )
        cmd.validate()


@patch("src.youtubesorter.commands.deduplicate.find_latest_state")
def test_deduplicate_command_validate_resume_no_state(mock_find_state, mock_youtube):
    """Test validate with resume but no state file."""
    mock_find_state.return_value = None
    with pytest.raises(ValueError, match="No recovery state found for playlist playlist123"):
        cmd = DeduplicateCommand(
            youtube=mock_youtube,
            playlist_id="playlist123",
            resume=True,
        )
        cmd.validate()


@patch("src.youtubesorter.commands.deduplicate.find_latest_state")
@patch("src.youtubesorter.commands.deduplicate.RecoveryManager")
def test_deduplicate_command_validate_resume_destination_not_found(
    mock_recovery_manager, mock_find_state, mock_youtube
):
    """Test validate with resume destination not in state."""
    mock_find_state.return_value = "state.json"
    mock_recovery = MagicMock()
    mock_recovery.destination_metadata = {}
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    with pytest.raises(ValueError, match="Destination dest1 not found in recovery state"):
        cmd = DeduplicateCommand(
            youtube=mock_youtube,
            playlist_id="playlist123",
            resume=True,
            resume_destination="dest1",
        )
        cmd.validate()


@patch("src.youtubesorter.commands.deduplicate.find_latest_state")
@patch("src.youtubesorter.commands.deduplicate.RecoveryManager")
def test_deduplicate_command_validate_resume_destination_completed(
    mock_recovery_manager, mock_find_state, mock_youtube
):
    """Test validate with completed resume destination."""
    mock_find_state.return_value = "state.json"
    mock_recovery = MagicMock()
    mock_recovery.destination_metadata = {"dest1": {}}
    mock_recovery.get_destination_progress.return_value = {"completed": True}
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    with pytest.raises(ValueError, match="Destination dest1 already completed"):
        cmd = DeduplicateCommand(
            youtube=mock_youtube,
            playlist_id="playlist123",
            resume=True,
            resume_destination="dest1",
        )
        cmd.validate()


@patch("src.youtubesorter.commands.deduplicate.RecoveryManager")
def test_deduplicate_command_run_no_videos(mock_recovery_manager, mock_youtube):
    """Test run with no videos to process."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = set()
    mock_recovery.get_remaining_videos.return_value = []
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = []

    cmd = DeduplicateCommand(
        youtube=mock_youtube,
        playlist_id="playlist123",
    )
    assert cmd._run()


@patch("src.youtubesorter.commands.deduplicate.RecoveryManager")
def test_deduplicate_command_run_no_duplicates(mock_recovery_manager, mock_youtube):
    """Test run with no duplicate videos."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = set()
    videos = [
        {"video_id": "vid1", "title": "Video 1"},
        {"video_id": "vid2", "title": "Video 2"},
    ]
    mock_recovery.get_remaining_videos.return_value = videos
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = videos

    cmd = DeduplicateCommand(
        youtube=mock_youtube,
        playlist_id="playlist123",
    )
    assert cmd._run()
    mock_youtube.batch_remove_videos_from_playlist.assert_not_called()


@patch("src.youtubesorter.commands.deduplicate.RecoveryManager")
def test_deduplicate_command_run_with_duplicates(mock_recovery_manager, mock_youtube):
    """Test run with duplicate videos."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = set()
    videos = [
        {"video_id": "vid1", "title": "Video 1"},
        {"video_id": "vid1", "title": "Video 1"},  # Duplicate
    ]
    mock_recovery.get_remaining_videos.return_value = videos
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = videos
    mock_youtube.batch_remove_videos_from_playlist.return_value = {"vid1"}

    cmd = DeduplicateCommand(
        youtube=mock_youtube,
        playlist_id="playlist123",
    )
    assert cmd._run()
    mock_youtube.batch_remove_videos_from_playlist.assert_called_once_with(["vid1"], "playlist123")


@patch("src.youtubesorter.commands.deduplicate.RecoveryManager")
def test_deduplicate_command_run_dry_run(mock_recovery_manager, mock_youtube):
    """Test run in dry run mode."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = set()
    videos = [
        {"video_id": "vid1", "title": "Video 1"},
        {"video_id": "vid1", "title": "Video 1"},  # Duplicate
    ]
    mock_recovery.get_remaining_videos.return_value = videos
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = videos

    cmd = DeduplicateCommand(
        youtube=mock_youtube,
        playlist_id="playlist123",
        dry_run=True,
    )
    assert cmd._run()
    mock_youtube.batch_remove_videos_from_playlist.assert_not_called()


@patch("src.youtubesorter.commands.deduplicate.RecoveryManager")
def test_deduplicate_command_run_with_error(mock_recovery_manager, mock_youtube):
    """Test run with error during video removal."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = set()
    videos = [
        {"video_id": "vid1", "title": "Video 1"},
        {"video_id": "vid1", "title": "Video 1"},  # Duplicate
    ]
    mock_recovery.get_remaining_videos.return_value = videos
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = videos
    mock_youtube.batch_remove_videos_from_playlist.side_effect = YouTubeError("Test error")

    cmd = DeduplicateCommand(
        youtube=mock_youtube,
        playlist_id="playlist123",
    )
    assert not cmd._run()
    assert "vid1" in mock_recovery.failed_videos


@patch("src.youtubesorter.commands.deduplicate.RecoveryManager")
def test_deduplicate_command_run_with_playlist_error(mock_recovery_manager, mock_youtube):
    """Test run with error getting playlist videos."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = set()
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.side_effect = YouTubeError("Test error")

    cmd = DeduplicateCommand(
        youtube=mock_youtube,
        playlist_id="playlist123",
    )
    assert not cmd._run()


@patch("src.youtubesorter.commands.deduplicate.RecoveryManager")
def test_deduplicate_command_run_with_partial_error(mock_recovery_manager, mock_youtube):
    """Test run with partial error during video removal."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = set()
    videos = [
        {"video_id": "vid1", "title": "Video 1"},
        {"video_id": "vid1", "title": "Video 1"},  # Duplicate
        {"video_id": "vid2", "title": "Video 2"},
        {"video_id": "vid2", "title": "Video 2"},  # Duplicate
    ]
    mock_recovery.get_remaining_videos.return_value = videos
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = videos
    mock_youtube.batch_remove_videos_from_playlist.return_value = {"vid1"}  # Only vid1 removed

    cmd = DeduplicateCommand(
        youtube=mock_youtube,
        playlist_id="playlist123",
    )
    assert not cmd._run()  # Should return False as not all duplicates were removed
    assert "vid1" in mock_recovery.processed_videos
    assert "vid2" in mock_recovery.failed_videos
