"""Tests for move command functionality."""

import pytest
from unittest.mock import MagicMock, patch

from src.youtubesorter.commands.move import MoveCommand
from src.youtubesorter.errors import PlaylistNotFoundError, YouTubeError


@pytest.fixture
def mock_youtube() -> MagicMock:
    """Create mock YouTube API with common responses.
    
    Returns:
        MagicMock: Configured mock YouTube API
    """
    mock = MagicMock()
    
    # Configure default video list response
    mock.get_playlist_videos.return_value = [
        {
            "video_id": "vid1",
            "title": "Video 1",
            "description": "Description 1"
        },
        {
            "video_id": "vid2",
            "title": "Video 2",
            "description": "Description 2"
        }
    ]
    
    # Configure default move response
    mock.batch_move_videos_to_playlist.return_value = ["vid1", "vid2"]
    
    return mock


def test_move_command_init():
    """Test move command initialization."""
    cmd = MoveCommand(
        youtube=MagicMock(),
        source_playlist="source1",
        target_playlist="target1",
        dry_run=True,
        verbose=True
    )
    
    assert cmd.source_playlist == "source1"
    assert cmd.target_playlist == "target1"
    assert cmd.dry_run is True
    assert cmd.verbose is True


def test_move_command_run_empty_playlist(mock_youtube: MagicMock):
    """Test move command with empty playlist."""
    mock_youtube.get_playlist_videos.return_value = []
    
    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source1",
        target_playlist="target1"
    )
    
    assert cmd._run()
    mock_youtube.get_playlist_videos.assert_called_once_with("source1")
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


def test_move_command_run_with_videos(mock_youtube: MagicMock):
    """Test move command with videos."""
    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source1",
        target_playlist="target1"
    )
    
    assert cmd._run()
    
    mock_youtube.get_playlist_videos.assert_called_once_with("source1")
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        playlist_id="target1",
        video_ids=["vid1", "vid2"],
        source_playlist_id="source1",
        remove_from_source=True
    )


def test_move_command_run_dry_run(mock_youtube: MagicMock):
    """Test move command in dry run mode."""
    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="source1",
        target_playlist="target1",
        dry_run=True
    )
    
    assert cmd._run()
    
    mock_youtube.get_playlist_videos.assert_called_once_with("source1")
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


def test_move_command_run_with_recovery(mock_youtube: MagicMock):
    """Test move command with recovery state."""
    with patch("src.youtubesorter.commands.move.RecoveryManager") as mock_recovery:
        mock_manager = MagicMock()
        mock_manager.processed_videos = set()
        mock_manager.failed_videos = set()
        mock_recovery.return_value.__enter__.return_value = mock_manager
        
        cmd = MoveCommand(
            youtube=mock_youtube,
            source_playlist="source1",
            target_playlist="target1",
            resume=True
        )
        cmd.recovery = mock_manager
        
        assert cmd._run()
        
        # Verify videos were moved
        mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
            playlist_id="target1",
            video_ids=["vid1", "vid2"],
            source_playlist_id="source1",
            remove_from_source=True
        )
        
        # Verify recovery state was updated
        assert mock_manager.processed_videos == {"vid1", "vid2"}
        mock_manager.save_state.assert_called_once()


def test_move_command_run_with_failed_videos(mock_youtube: MagicMock):
    """Test move command handling failed videos."""
    mock_youtube.batch_move_videos_to_playlist.return_value = ["vid1"]  # vid2 fails
    
    with patch("src.youtubesorter.commands.move.RecoveryManager") as mock_recovery:
        mock_manager = MagicMock()
        mock_manager.processed_videos = set()
        mock_manager.failed_videos = set()
        mock_recovery.return_value.__enter__.return_value = mock_manager
        
        cmd = MoveCommand(
            youtube=mock_youtube,
            source_playlist="source1",
            target_playlist="target1"
        )
        cmd.recovery = mock_manager
        
        assert cmd._run()
        
        # Verify recovery state tracks failed videos
        assert mock_manager.processed_videos == {"vid1"}
        assert mock_manager.failed_videos == {"vid2"}
        mock_manager.save_state.assert_called_once()


def test_move_command_run_playlist_not_found(mock_youtube: MagicMock):
    """Test move command with non-existent playlist."""
    mock_youtube.get_playlist_videos.side_effect = PlaylistNotFoundError("Playlist not found")
    
    cmd = MoveCommand(
        youtube=mock_youtube,
        source_playlist="nonexistent",
        target_playlist="target1"
    )
    
    with pytest.raises(PlaylistNotFoundError):
        cmd._run()


def test_move_command_run_api_error(mock_youtube: MagicMock):
    """Test move command handling API errors."""
    mock_youtube.batch_move_videos_to_playlist.side_effect = YouTubeError("API Error")
    
    with patch("src.youtubesorter.commands.move.RecoveryManager") as mock_recovery:
        mock_manager = MagicMock()
        mock_manager.processed_videos = set()
        mock_manager.failed_videos = set()
        mock_recovery.return_value.__enter__.return_value = mock_manager
        
        cmd = MoveCommand(
            youtube=mock_youtube,
            source_playlist="source1",
            target_playlist="target1"
        )
        cmd.recovery = mock_manager
        
        with pytest.raises(YouTubeError):
            cmd._run()
        
        # Verify all videos marked as failed
        assert mock_manager.failed_videos == {"vid1", "vid2"}
        mock_manager.save_state.assert_called_once()
