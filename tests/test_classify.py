"""Tests for the classify command."""

from unittest.mock import patch, MagicMock
import pytest

from src.youtubesorter.commands.classify import ClassifyCommand
from src.youtubesorter.core import YouTubeBase
from src.youtubesorter.errors import YouTubeError, PlaylistNotFoundError


@pytest.fixture
def youtube() -> MagicMock:
    """Create mock YouTube client with standard responses.
    
    Returns:
        MagicMock: Configured mock YouTube API client
    """
    mock = MagicMock(spec=YouTubeBase)
    mock.get_playlist_videos.return_value = [
        {
            "snippet": {
                "resourceId": {
                    "videoId": "video1"
                },
                "title": "Test Video 1",
                "description": "",
            }
        },
        {
            "snippet": {
                "resourceId": {
                    "videoId": "video2"
                },
                "title": "Test Video 2",
                "description": "",
            }
        },
        {
            "snippet": {
                "resourceId": {
                    "videoId": "video3"
                },
                "title": "Test Video 3",
                "description": "",
            }
        },
    ]
    
    # Configure default responses
    mock.batch_add_videos_to_playlist.return_value = ["video1"]
    mock.get_playlist_info.return_value = {
        "title": "Test Playlist",
        "description": "Test Description"
    }
    
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


def test_classify_command_run():
    """Test that classify command successfully processes videos."""
    mock_youtube = MagicMock()
    mock_youtube.get_playlist_videos.return_value = [{
        "snippet": {
            "resourceId": {"videoId": "video1"},
            "title": "Test Video 1",
            "description": ""
        }
    }]
    
    cmd = ClassifyCommand(
        youtube=mock_youtube,
        source_playlist_id="source1",
        target_playlists=["target1"]
    )
    
    with patch("src.youtubesorter.commands.classify.RecoveryManager") as mock_recovery:
        mock_manager = MagicMock()
        mock_manager.processed_videos = set()
        mock_manager.failed_videos = set()
        mock_recovery.return_value = mock_manager
        cmd.recovery = mock_manager
        
        result = cmd._run()
        
        assert result is True
        mock_youtube.get_playlist_videos.assert_called_once_with("source1")
        mock_youtube.batch_add_videos_to_playlist.assert_called_once_with(["video1"], "target1")


def test_classify_command_resume():
    """Test that classify command resumes from previous state."""
    mock_youtube = MagicMock()
    mock_youtube.get_playlist_videos.return_value = [{
        "snippet": {
            "resourceId": {"videoId": "video2"},
            "title": "Test Video 2",
            "description": ""
        }
    }]

    cmd = ClassifyCommand(
        youtube=mock_youtube,
        source_playlist_id="source1", 
        target_playlists=["target1"],
        resume=True
    )

    with patch("src.youtubesorter.commands.classify.RecoveryManager") as mock_recovery:
        mock_manager = MagicMock()
        mock_manager.processed_videos = {"video1"}
        mock_manager.failed_videos = set()
        mock_manager.get_remaining_videos.return_value = [{
            "snippet": {
                "resourceId": {"videoId": "video2"},
                "title": "Test Video 2",
                "description": ""
            }
        }]
        mock_recovery.return_value.__enter__.return_value = mock_manager
        cmd.recovery = mock_manager

        result = cmd._run()

        assert result is True
        mock_youtube.batch_add_videos_to_playlist.assert_called_once_with(
            ["video2"], "target1"
        )
        assert "video2" in mock_manager.processed_videos


def test_classify_command_retry_failed():
    """Test that classify command retries failed videos."""
    mock_youtube = MagicMock()
    mock_youtube.get_playlist_videos.return_value = [{
        "snippet": {
            "resourceId": {"videoId": "video1"},
            "title": "Test Video 1",
            "description": ""
        }
    }]

    cmd = ClassifyCommand(
        youtube=mock_youtube,
        source_playlist_id="source1",
        target_playlists=["target1"],
        retry_failed=True
    )

    with patch("src.youtubesorter.commands.classify.RecoveryManager") as mock_recovery:
        mock_manager = MagicMock()
        mock_manager.processed_videos = set()
        mock_manager.failed_videos = {"video1"}
        mock_manager.get_remaining_videos.return_value = [{
            "snippet": {
                "resourceId": {"videoId": "video1"},
                "title": "Test Video 1",
                "description": ""
            }
        }]
        mock_recovery.return_value.__enter__.return_value = mock_manager
        cmd.recovery = mock_manager

        result = cmd._run()

        assert result is True
        mock_youtube.batch_add_videos_to_playlist.assert_called_once_with(
            ["video1"], "target1"
        )
        assert "video1" in mock_manager.processed_videos


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
        mock_manager = MagicMock()
        mock_manager.get_remaining_videos.return_value = [
            {
                "snippet": {
                    "resourceId": {
                        "videoId": "video1"
                    },
                    "title": "Test Video 1",
                    "description": "",
                }
            }
        ]
        mock_manager.processed_videos = set()
        mock_manager.failed_videos = set()
        mock_recovery.return_value.__enter__.return_value = mock_manager
        cmd.recovery = mock_manager  # Set recovery manager before running

        assert cmd.run() is True


def test_classify_command_api_error():
    """Test that classify command handles API errors."""
    mock_youtube = MagicMock()
    mock_youtube.get_playlist_videos.side_effect = YouTubeError("API Error")

    cmd = ClassifyCommand(
        youtube=mock_youtube,
        source_playlist_id="source1",
        target_playlists=["target1"]
    )

    with patch("src.youtubesorter.commands.classify.RecoveryManager") as mock_recovery:
        mock_manager = MagicMock()
        mock_manager.processed_videos = set()
        mock_manager.failed_videos = set()
        mock_recovery.return_value.__enter__.return_value = mock_manager
        cmd.recovery = mock_manager

        with pytest.raises(YouTubeError, match="API Error"):
            cmd._run()

        mock_youtube.get_playlist_videos.assert_called_once_with("source1")
        mock_youtube.batch_add_videos_to_playlist.assert_not_called()


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


def test_classify_command_run_playlist_not_found(youtube):
    """Test classify command handles playlist not found."""
    cmd = ClassifyCommand(
        youtube=youtube,
        source_playlist_id="source1",
        target_playlists=["target1"]
    )
    
    # Configure mock to raise PlaylistNotFoundError
    youtube.get_playlist_videos.side_effect = PlaylistNotFoundError("Playlist not found")
    
    # Run command and verify error
    with pytest.raises(PlaylistNotFoundError, match="Playlist not found"):
        cmd._run()


def test_classify_command_run_api_error(youtube):
    """Test classify command handles API error."""
    cmd = ClassifyCommand(
        youtube=youtube,
        source_playlist_id="source1",
        target_playlists=["target1"]
    )
    
    # Configure mock to raise YouTubeError
    youtube.get_playlist_videos.side_effect = YouTubeError("API Error")
    
    # Run command and verify error
    with pytest.raises(YouTubeError, match="API Error"):
        cmd._run()
