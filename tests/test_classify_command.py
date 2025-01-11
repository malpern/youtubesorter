"""Tests for the classify command."""

from unittest.mock import MagicMock, patch
import pytest

from src.youtubesorter.commands.classify import ClassifyCommand
from src.youtubesorter.errors import YouTubeError
from src.youtubesorter.core import YouTubeBase


class MockYouTubeBase(YouTubeBase):
    """Mock YouTube base class."""

    def __init__(self):
        """Initialize mock."""
        self.get_playlist_videos = MagicMock()
        self.batch_add_videos_to_playlist = MagicMock()


@pytest.fixture
def mock_youtube():
    """Create mock YouTube client."""
    return MockYouTubeBase()


def test_classify_command_init(mock_youtube):
    """Test classify command initialization."""
    cmd = ClassifyCommand(
        youtube=mock_youtube,
        source_playlist_id="source123",
        target_playlists=["target1", "target2"],
    )
    assert cmd.youtube == mock_youtube
    assert cmd.name == "classify"
    assert cmd.help == "Classify videos into multiple playlists"
    assert cmd.source_playlist_id == "source123"
    assert cmd.target_playlists == ["target1", "target2"]
    assert not cmd.resume
    assert not cmd.resume_destination
    assert not cmd.retry_failed
    assert not cmd.dry_run
    assert cmd.limit is None


def test_classify_command_validate_missing_source(mock_youtube):
    """Test validate with missing source playlist."""
    with pytest.raises(ValueError, match="Source playlist ID is required"):
        cmd = ClassifyCommand(
            youtube=mock_youtube,
            source_playlist_id="",
            target_playlists=["target1"],
        )
        cmd.validate()


def test_classify_command_validate_missing_targets(mock_youtube):
    """Test validate with missing target playlists."""
    with pytest.raises(ValueError, match="At least one target playlist ID is required"):
        cmd = ClassifyCommand(
            youtube=mock_youtube,
            source_playlist_id="source123",
            target_playlists=[],
        )
        cmd.validate()


def test_classify_command_validate_resume_destination_without_resume(mock_youtube):
    """Test validate with resume destination but no resume flag."""
    with pytest.raises(ValueError, match="--resume-destination requires --resume"):
        cmd = ClassifyCommand(
            youtube=mock_youtube,
            source_playlist_id="source123",
            target_playlists=["target1"],
            resume_destination="target1",
        )
        cmd.validate()


@patch("src.youtubesorter.commands.classify.find_latest_state")
def test_classify_command_validate_resume_no_state(mock_find_state, mock_youtube):
    """Test validate with resume but no state file."""
    mock_find_state.return_value = None
    with pytest.raises(ValueError, match="No recovery state found for playlist source123"):
        cmd = ClassifyCommand(
            youtube=mock_youtube,
            source_playlist_id="source123",
            target_playlists=["target1"],
            resume=True,
        )
        cmd.validate()


@patch("src.youtubesorter.commands.classify.find_latest_state")
@patch("src.youtubesorter.commands.classify.RecoveryManager")
def test_classify_command_validate_resume_destination_not_found(
    mock_recovery_manager, mock_find_state, mock_youtube
):
    """Test validate with resume destination not in state."""
    mock_find_state.return_value = "state.json"
    mock_recovery = MagicMock()
    mock_recovery.destination_metadata = {}
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    with pytest.raises(ValueError, match="Destination target1 not found in recovery state"):
        cmd = ClassifyCommand(
            youtube=mock_youtube,
            source_playlist_id="source123",
            target_playlists=["target1"],
            resume=True,
            resume_destination="target1",
        )
        cmd.validate()


@patch("src.youtubesorter.commands.classify.find_latest_state")
@patch("src.youtubesorter.commands.classify.RecoveryManager")
def test_classify_command_validate_resume_destination_completed(
    mock_recovery_manager, mock_find_state, mock_youtube
):
    """Test validate with completed resume destination."""
    mock_find_state.return_value = "state.json"
    mock_recovery = MagicMock()
    mock_recovery.destination_metadata = {"target1": {}}
    mock_recovery.get_destination_progress.return_value = {"completed": True}
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    with pytest.raises(ValueError, match="Destination target1 already completed"):
        cmd = ClassifyCommand(
            youtube=mock_youtube,
            source_playlist_id="source123",
            target_playlists=["target1"],
            resume=True,
            resume_destination="target1",
        )
        cmd.validate()


def test_classify_command_classify_video(mock_youtube):
    """Test classify_video method."""
    cmd = ClassifyCommand(
        youtube=mock_youtube,
        source_playlist_id="source123",
        target_playlists=["target1", "target2"],
    )
    video = {"video_id": "vid1", "title": "Test Video"}
    assert cmd.classify_video(video) == "target1"


@patch("src.youtubesorter.commands.classify.RecoveryManager")
def test_classify_command_run_no_videos(mock_recovery_manager, mock_youtube):
    """Test run with no videos to process."""
    mock_recovery = MagicMock()
    mock_recovery.get_remaining_videos.return_value = []
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = []

    cmd = ClassifyCommand(
        youtube=mock_youtube,
        source_playlist_id="source123",
        target_playlists=["target1"],
    )
    assert cmd._run()


@patch("src.youtubesorter.commands.classify.RecoveryManager")
def test_classify_command_run_with_videos(mock_recovery_manager, mock_youtube):
    """Test run with videos to process."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = set()
    videos = [{"video_id": "vid1", "title": "Test Video"}]
    mock_recovery.get_remaining_videos.return_value = videos
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = videos
    mock_youtube.batch_add_videos_to_playlist.return_value = {"vid1"}

    cmd = ClassifyCommand(
        youtube=mock_youtube,
        source_playlist_id="source123",
        target_playlists=["target1"],
    )
    assert cmd._run()
    mock_youtube.batch_add_videos_to_playlist.assert_called_once_with(["vid1"], "target1")


@patch("src.youtubesorter.commands.classify.RecoveryManager")
def test_classify_command_run_dry_run(mock_recovery_manager, mock_youtube):
    """Test run in dry run mode."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = set()
    videos = [{"video_id": "vid1", "title": "Test Video"}]
    mock_recovery.get_remaining_videos.return_value = videos
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = videos

    cmd = ClassifyCommand(
        youtube=mock_youtube,
        source_playlist_id="source123",
        target_playlists=["target1"],
        dry_run=True,
    )
    assert cmd._run()
    mock_youtube.batch_add_videos_to_playlist.assert_not_called()


@patch("src.youtubesorter.commands.classify.RecoveryManager")
def test_classify_command_run_with_error(mock_recovery_manager, mock_youtube):
    """Test run with error during video processing."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = set()
    videos = [{"video_id": "vid1", "title": "Test Video"}]
    mock_recovery.get_remaining_videos.return_value = videos
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.return_value = videos
    mock_youtube.batch_add_videos_to_playlist.side_effect = YouTubeError("Test error")

    cmd = ClassifyCommand(
        youtube=mock_youtube,
        source_playlist_id="source123",
        target_playlists=["target1"],
    )
    assert cmd._run()  # Should still return True as it's a per-video error
    assert "vid1" in mock_recovery.failed_videos


@patch("src.youtubesorter.commands.classify.RecoveryManager")
def test_classify_command_run_with_playlist_error(mock_recovery_manager, mock_youtube):
    """Test run with error getting playlist videos."""
    mock_recovery = MagicMock()
    mock_recovery.processed_videos = set()
    mock_recovery.failed_videos = set()
    mock_recovery_manager.return_value.__enter__.return_value = mock_recovery

    mock_youtube.get_playlist_videos.side_effect = YouTubeError("Test error")

    cmd = ClassifyCommand(
        youtube=mock_youtube,
        source_playlist_id="source123",
        target_playlists=["target1"],
    )
    assert not cmd._run()  # Should return False for playlist-level errors
