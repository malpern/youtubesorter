"""Tests for base YouTubeCommand class."""

from unittest.mock import MagicMock

import pytest

from src.youtubesorter.commands.base import YouTubeCommand
from src.youtubesorter.core import YouTubeBase
from src.youtubesorter.errors import YouTubeError


class MockYouTubeBase(YouTubeBase):
    """Mock YouTube base class for testing."""

    def __init__(self):
        """Initialize mock."""
        mock_youtube = MagicMock()
        super().__init__(mock_youtube)
        self.authenticated = True


@pytest.fixture
def mock_youtube():
    """Create mock YouTube client."""
    return MockYouTubeBase()


def test_youtube_command_init(mock_youtube):
    """Test YouTubeCommand initialization."""
    cmd = YouTubeCommand(youtube=mock_youtube)
    assert cmd.youtube == mock_youtube
    assert not cmd.dry_run
    assert not cmd.verbose
    assert cmd._total_items == 0
    assert cmd._current_item == 0
    assert not cmd._validated


def test_youtube_command_validate_no_youtube():
    """Test YouTubeCommand validation with no YouTube client."""
    cmd = YouTubeCommand(youtube=None)
    with pytest.raises(ValueError, match="YouTube API client is required"):
        cmd.validate()


def test_youtube_command_validate_success(mock_youtube):
    """Test YouTubeCommand validation success."""
    cmd = YouTubeCommand(youtube=mock_youtube)
    cmd.validate()
    assert cmd._validated


def test_youtube_command_run_without_validation(mock_youtube):
    """Test YouTubeCommand run without prior validation."""
    cmd = YouTubeCommand(youtube=mock_youtube)
    assert not cmd.run()  # Base _run() returns False
    assert cmd._validated  # Should auto-validate


def test_youtube_command_run_with_error(mock_youtube):
    """Test YouTubeCommand run with error."""
    cmd = YouTubeCommand(youtube=mock_youtube)
    cmd._run = MagicMock(side_effect=Exception("Test error"))
    with pytest.raises(YouTubeError, match="Test error"):
        cmd.run()


def test_youtube_command_run_success(mock_youtube):
    """Test YouTubeCommand run success."""
    cmd = YouTubeCommand(youtube=mock_youtube)
    cmd._run = MagicMock(return_value=True)
    assert cmd.run()


def test_youtube_command_progress_tracking(mock_youtube):
    """Test YouTubeCommand progress tracking."""
    cmd = YouTubeCommand(youtube=mock_youtube)

    # Test setting total items
    cmd.set_total_items(10)
    assert cmd._total_items == 10
    assert cmd._current_item == 0

    # Test updating progress
    cmd.update_progress()
    assert cmd._current_item == 1

    # Test multiple updates
    cmd.update_progress()
    cmd.update_progress()
    assert cmd._current_item == 3
