"""Common test fixtures and utilities."""

import os
import pytest
from typing import Generator
from unittest.mock import MagicMock

from src.youtubesorter.config import RECOVERY_DIR


@pytest.fixture(autouse=True)
def clean_test_state() -> Generator[None, None, None]:
    """Ensure each test starts with a clean state.
    
    This fixture runs automatically before and after each test to:
    1. Clear any cached state
    2. Remove state files
    3. Reset any global state
    
    Yields:
        None
    """
    # Setup - clear state before test
    if os.path.exists(RECOVERY_DIR):
        for f in os.listdir(RECOVERY_DIR):
            if f.endswith('.json'):
                os.remove(os.path.join(RECOVERY_DIR, f))
    
    yield
    
    # Teardown - clear state after test
    if os.path.exists(RECOVERY_DIR):
        for f in os.listdir(RECOVERY_DIR):
            if f.endswith('.json'):
                os.remove(os.path.join(RECOVERY_DIR, f))


@pytest.fixture
def youtube_client() -> MagicMock:
    """Create a mock YouTube API client.
    
    Returns:
        MagicMock: Mock YouTube API client with common methods configured
    """
    mock = MagicMock()
    
    # Configure common mock responses
    mock.playlistItems.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "id": "item1",
                "snippet": {
                    "resourceId": {"videoId": "vid1"},
                    "title": "Video 1",
                    "description": "Description 1"
                }
            },
            {
                "id": "item2", 
                "snippet": {
                    "resourceId": {"videoId": "vid2"},
                    "title": "Video 2",
                    "description": "Description 2"
                }
            }
        ]
    }
    
    mock.playlists.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "id": "playlist1",
                "snippet": {
                    "title": "Playlist 1",
                    "description": "Description 1"
                }
            }
        ]
    }
    
    return mock 