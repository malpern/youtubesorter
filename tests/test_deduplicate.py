"""Test cases for deduplicate command."""

from unittest.mock import MagicMock, patch

import pytest

from src.youtubesorter.deduplicate import DeduplicateCommand


@pytest.fixture
def youtube():
    """Create mock YouTube API client."""
    return MagicMock()


def test_deduplicate_command_init(youtube):
    """Test DeduplicateCommand initialization."""
    cmd = DeduplicateCommand(
        youtube=youtube,
        playlist_id="source1",
    )

    assert cmd.youtube == youtube
    assert cmd.playlist_id == "source1"


def test_deduplicate_command_validate(youtube):
    """Test command validation."""
    # Test valid command
    cmd = DeduplicateCommand(
        youtube=youtube,
        playlist_id="source1",
    )

    # Test validation
    assert cmd.validate() is True


def test_deduplicate_command_run(youtube):
    """Test command execution."""
    cmd = DeduplicateCommand(
        youtube=youtube,
        playlist_id="source1",
    )

    # Mock API responses
    mock_api = MagicMock()
    mock_api.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Video 1"},
        {"video_id": "vid1", "title": "Video 1"},  # Duplicate
        {"video_id": "vid2", "title": "Video 2"},
    ]
    mock_api.batch_remove_videos_from_playlist.return_value = ["vid1"]

    with patch("src.youtubesorter.deduplicate.YouTubeAPI", return_value=mock_api):
        result = cmd.run()

    assert result is True
    mock_api.batch_remove_videos_from_playlist.assert_called_once_with(["vid1"], "source1")
