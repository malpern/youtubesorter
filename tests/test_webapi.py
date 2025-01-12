"""Test cases for web API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

from src.youtubesorter.webapi import app
from src.youtubesorter.errors import YouTubeError
from src.youtubesorter.api import YouTubeAPI

client = TestClient(app)


@pytest.fixture
def mock_youtube_api(mocker):
    """Mock YouTube API client."""
    mock = Mock(spec=YouTubeAPI)
    # Mock playlist info
    mock.get_playlist_info.return_value = {"title": "Test Playlist"}
    
    # Mock playlist videos with duplicates
    mock.get_playlist_videos.return_value = [
        {"id": "123", "video_id": "123", "title": "Test Video 1"},
        {"id": "123", "video_id": "123", "title": "Test Video 1"},  # Duplicate
        {"id": "456", "video_id": "456", "title": "Test Video 2"}
    ]
    
    # Mock video operations
    mock.batch_move_videos_to_playlist.return_value = ["123", "456"]
    mock.batch_add_videos_to_playlist.return_value = ["123", "456"]
    mock.batch_remove_videos_from_playlist.return_value = ["123"]  # Return the removed duplicate
    
    # Mock common functions
    mocker.patch('src.youtubesorter.common.save_operation_state', return_value=None)
    mocker.patch('src.youtubesorter.common.load_operation_state', return_value={"processed": [], "failed": [], "skipped": []})
    mocker.patch('src.youtubesorter.common.find_latest_state', return_value="state.json")
    mocker.patch('src.youtubesorter.common.clear_operation_state', return_value=None)
    
    # Mock get_youtube_client
    mocker.patch('src.youtubesorter.webapi.get_youtube_client', return_value=mock)
    return mock


def test_consolidate_endpoint(mock_youtube_api):
    """Test consolidate endpoint."""
    # Test data
    request_data = {
        "source_playlists": ["PL123", "PL456"],
        "target_playlist": "PL789",
        "copy": True,
        "verbose": True
    }
    
    # Make request
    response = client.post("/consolidate", json=request_data)
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_distribute_endpoint(mock_youtube_api):
    """Test distribute endpoint."""
    # Test data
    request_data = {
        "source_playlist": "PL123",
        "target_playlists": ["PL456", "PL789"],
        "filter_prompts": ["music", "gaming"],
        "verbose": True
    }
    
    # Make request
    response = client.post("/distribute", json=request_data)
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_deduplicate_endpoint(mock_youtube_api):
    """Test deduplicate endpoint."""
    # Test data
    request_data = {
        "playlist_id": "PL123",
        "verbose": True
    }
    
    # Make request
    response = client.post("/deduplicate", json=request_data)
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_error_handling(mock_youtube_api):
    """Test error handling."""
    # Mock API error
    mock_youtube_api.get_playlist_info.side_effect = YouTubeError("API Error")
    
    # Test data
    request_data = {
        "source_playlists": ["PL123"],
        "target_playlist": "PL456",
        "verbose": True
    }
    
    # Make request
    response = client.post("/consolidate", json=request_data)
    
    # Verify response
    assert response.status_code == 500
    assert response.json()["detail"] == "API Error" 