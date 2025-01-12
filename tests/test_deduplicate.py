"""Test cases for deduplicate command."""

from unittest.mock import MagicMock, patch

import pytest

from src.youtubesorter.deduplicate import DeduplicateCommand
from src.youtubesorter.core import YouTubeBase


@pytest.fixture
def youtube():
    """Create mock YouTube API client."""
    mock = MagicMock(spec=YouTubeBase)
    mock.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Video 1"},
        {"video_id": "vid1", "title": "Video 1"},  # Duplicate
        {"video_id": "vid2", "title": "Video 2"},
    ]
    mock.batch_remove_videos_from_playlist.side_effect = lambda playlist_id, video_ids: video_ids
    return mock


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

    result = cmd.run()

    assert result is True
    youtube.batch_remove_videos_from_playlist.assert_called_once_with(
        playlist_id="source1",
        video_ids=["vid1"]
    )
