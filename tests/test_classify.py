"""Tests for the classify command."""

from unittest.mock import patch, MagicMock
import pytest

from src.youtubesorter.commands.classify import ClassifyCommand
from src.youtubesorter.core import YouTubeBase


@pytest.fixture
def youtube():
    """Create mock YouTube client."""
    mock = MagicMock(spec=YouTubeBase)
    mock.get_playlist_videos.return_value = [
        {
            "video_id": "video1",
            "title": "Test Video 1",
            "description": "",
        },
        {
            "video_id": "video2",
            "title": "Test Video 2",
            "description": "",
        },
        {
            "video_id": "video3",
            "title": "Test Video 3",
            "description": "",
        },
    ]
    return mock


def test_classify_command_init(youtube):
    """Test ClassifyCommand initialization."""
    target_playlists = ["target1", "target2"]
    cmd = ClassifyCommand(
        youtube=youtube,
        source_playlist_id="source1",
        target_playlists=target_playlists,
        resume=True,
    )
    assert cmd.source_playlist_id == "source1"
    assert cmd.target_playlists == target_playlists
    assert cmd.resume is True
    assert cmd.youtube == youtube
    assert cmd.name == "classify"
    assert cmd.help == "Classify videos into multiple playlists"


def test_classify_command_validate(youtube):
    """Test command validation."""
    # Test valid command
    cmd = ClassifyCommand(
        youtube=youtube,
        source_playlist_id="source1",
        target_playlists=["target1", "target2"],
    )
    assert cmd.validate() is None

    # Test missing source playlist
    cmd = ClassifyCommand(
        youtube=youtube,
        source_playlist_id="",
        target_playlists=["target1"],
    )
    with pytest.raises(ValueError, match="Source playlist ID is required"):
        cmd.validate()

    # Test missing target playlists
    cmd = ClassifyCommand(
        youtube=youtube,
        source_playlist_id="source1",
        target_playlists=[],
    )
    with pytest.raises(ValueError, match="At least one target playlist ID is required"):
        cmd.validate()


def test_classify_command_run(youtube):
    """Test command execution."""
    target_playlists = ["target1", "target2"]
    cmd = ClassifyCommand(
        youtube=youtube,
        source_playlist_id="source1",
        target_playlists=target_playlists,
    )

    # Mock recovery manager
    with patch("src.youtubesorter.recovery.RecoveryManager") as mock_recovery:
        mock_recovery.return_value.__enter__.return_value.get_remaining_videos.return_value = [
            {"video_id": "video1", "title": "Test Video 1"}
        ]

        assert cmd.run() is True


def test_classify_command_resume(youtube):
    """Test resuming command execution."""
    target_playlists = ["target1", "target2"]
    cmd = ClassifyCommand(
        youtube=youtube,
        source_playlist_id="source1",
        target_playlists=target_playlists,
        resume=True,
    )

    # Mock recovery manager
    with patch("src.youtubesorter.recovery.RecoveryManager") as mock_recovery:
        mock_recovery.return_value.__enter__.return_value.get_remaining_videos.return_value = [
            {"video_id": "video1", "title": "Test Video 1"}
        ]

        assert cmd.run() is True


def test_classify_command_no_matches(youtube):
    """Test command execution with no matching videos."""
    target_playlists = ["target1", "target2"]
    cmd = ClassifyCommand(
        youtube=youtube,
        source_playlist_id="source1",
        target_playlists=target_playlists,
    )

    # Mock recovery manager
    with patch("src.youtubesorter.recovery.RecoveryManager") as mock_recovery:
        mock_recovery.return_value.__enter__.return_value.get_remaining_videos.return_value = []
        assert cmd.run() is True


def test_classify_command_api_error(youtube):
    """Test command execution with API error."""
    target_playlists = ["target1", "target2"]
    cmd = ClassifyCommand(
        youtube=youtube,
        source_playlist_id="source1",
        target_playlists=target_playlists,
    )

    # Mock YouTube API to raise error
    youtube.get_playlist_videos.side_effect = Exception("API Error")

    # Mock recovery manager
    with patch("src.youtubesorter.recovery.RecoveryManager") as mock_recovery:
        mock_recovery.return_value.__enter__.return_value.get_remaining_videos.return_value = []
        assert cmd.run() is False


def test_classify_command_classify_video(youtube):
    """Test video classification."""
    target_playlists = ["target1", "target2"]
    cmd = ClassifyCommand(
        youtube=youtube,
        source_playlist_id="source1",
        target_playlists=target_playlists,
    )

    video = {
        "video_id": "video1",
        "title": "Test Video",
    }

    # Test basic classification
    target_id = cmd.classify_video(video)
    assert target_id in target_playlists
