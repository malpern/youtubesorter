"""Test cases for common module."""

import logging
import os
from unittest.mock import Mock, patch

import pytest

from src.youtubesorter import common
from src.youtubesorter.errors import PlaylistNotFoundError


def test_save_operation_state():
    """Test saving operation state."""
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = Mock()
        mock_open.return_value.write = Mock()

        common.save_operation_state(
            "playlist1",
            ["video1", "video2"],
            ["video3"],
            ["video4"],
            state_file="test.json",
        )

        mock_open.assert_called_once()
        assert mock_open.call_args[0][0] == "test.json"
        assert mock_open.call_args[0][1] == "w"
