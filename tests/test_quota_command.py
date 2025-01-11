"""Tests for the quota command."""

from unittest.mock import MagicMock, patch

import pytest

from src.youtubesorter.commands.quota import QuotaCommand
from src.youtubesorter.errors import YouTubeError
from src.youtubesorter.core import YouTubeBase


class MockYouTubeBase(YouTubeBase):
    """Mock YouTube base class."""

    def __init__(self):
        """Initialize mock."""
        self.get_quota_info = MagicMock()


@pytest.fixture
def mock_youtube():
    """Create mock YouTube client."""
    return MockYouTubeBase()


def test_quota_command_init(mock_youtube):
    """Test quota command initialization."""
    cmd = QuotaCommand(youtube=mock_youtube)
    assert cmd.youtube == mock_youtube
    assert cmd.name == "quota"
    assert cmd.help == "Check YouTube API quota usage"


def test_quota_command_run_success(mock_youtube):
    """Test quota command run success."""
    mock_youtube.get_quota_info.return_value = {
        "quota_used": 100,
        "quota_remaining": 9900,
        "quota_limit": 10000,
    }

    cmd = QuotaCommand(youtube=mock_youtube)
    assert cmd._run()
    mock_youtube.get_quota_info.assert_called_once()


def test_quota_command_run_error(mock_youtube):
    """Test quota command run with error."""
    mock_youtube.get_quota_info.side_effect = YouTubeError("Test error")

    cmd = QuotaCommand(youtube=mock_youtube)
    assert not cmd._run()
    mock_youtube.get_quota_info.assert_called_once()


@patch("src.youtubesorter.commands.quota.logger")
def test_quota_command_run_logs_info(mock_logger, mock_youtube):
    """Test quota command logs quota information."""
    quota_info = {
        "quota_used": 100,
        "quota_remaining": 9900,
        "quota_limit": 10000,
    }
    mock_youtube.get_quota_info.return_value = quota_info

    cmd = QuotaCommand(youtube=mock_youtube)
    cmd._run()

    mock_logger.info.assert_called_once_with("Quota usage: %s", quota_info)


@patch("src.youtubesorter.commands.quota.logger")
def test_quota_command_run_logs_error(mock_logger, mock_youtube):
    """Test quota command logs error."""
    error_msg = "Test error"
    mock_youtube.get_quota_info.side_effect = Exception(error_msg)

    cmd = QuotaCommand(youtube=mock_youtube)
    cmd._run()

    mock_logger.error.assert_called_once_with("Failed to get quota information: %s", error_msg)
