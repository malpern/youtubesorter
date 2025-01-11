"""Tests for the core module."""

from unittest.mock import MagicMock, patch

import pytest

from src.youtubesorter.core import YouTubeBase
from src.youtubesorter.errors import PlaylistNotFoundError


@pytest.fixture
def youtube_client():
    """Create a mock YouTube client."""
    return MagicMock()


@pytest.fixture
def youtube_base(youtube_client):
    """Create a YouTubeBase instance with mock client."""
    return YouTubeBase(youtube_client)


def test_get_playlist_info_success(youtube_base, youtube_client):
    """Test successful retrieval of playlist info."""
    # Mock response data
    mock_response = {
        "items": [
            {
                "id": "playlist1",
                "snippet": {
                    "title": "Test Playlist",
                    "description": "Test Description",
                },
            }
        ]
    }

    # Set up mock
    mock_request = MagicMock()
    mock_request.execute.return_value = mock_response
    youtube_client.playlists.return_value.list.return_value = mock_request

    # Call function
    info = youtube_base.get_playlist_info("playlist1")

    # Verify results
    assert info == {
        "id": "playlist1",
        "title": "Test Playlist",
        "description": "Test Description",
    }
    youtube_client.playlists.return_value.list.assert_called_once_with(
        part="snippet",
        id="playlist1",
        maxResults=1,
    )


def test_get_playlist_info_not_found(youtube_base, youtube_client):
    """Test handling of playlist not found error."""
    # Mock empty response
    mock_response = {"items": []}
    mock_request = MagicMock()
    mock_request.execute.return_value = mock_response
    youtube_client.playlists.return_value.list.return_value = mock_request

    # Verify error is raised
    with pytest.raises(PlaylistNotFoundError):
        youtube_base.get_playlist_info("nonexistent")


def test_get_playlist_info_api_error(youtube_base, youtube_client):
    """Test handling of API error."""
    # Mock API error
    mock_request = MagicMock()
    mock_request.execute.side_effect = Exception("API error")
    youtube_client.playlists.return_value.list.return_value = mock_request

    # Verify error is propagated
    with pytest.raises(Exception):
        youtube_base.get_playlist_info("playlist1")


def test_get_playlist_info_missing_description(youtube_base, youtube_client):
    """Test handling of missing description field."""
    # Mock response without description
    mock_response = {
        "items": [
            {
                "id": "playlist1",
                "snippet": {
                    "title": "Test Playlist",
                },
            }
        ]
    }

    # Set up mock
    mock_request = MagicMock()
    mock_request.execute.return_value = mock_response
    youtube_client.playlists.return_value.list.return_value = mock_request

    # Call function
    info = youtube_base.get_playlist_info("playlist1")

    # Verify results
    assert info == {
        "id": "playlist1",
        "title": "Test Playlist",
        "description": "",
    }


def test_get_playlist_videos_success(youtube_base, youtube_client):
    """Test successful retrieval of playlist videos."""
    # Mock response data for two pages
    mock_responses = [
        {
            "items": [
                {
                    "snippet": {
                        "resourceId": {"videoId": "vid1"},
                        "title": "Video 1",
                        "description": "Desc 1",
                    }
                }
            ],
            "nextPageToken": "token1",
        },
        {
            "items": [
                {
                    "snippet": {
                        "resourceId": {"videoId": "vid2"},
                        "title": "Video 2",
                        "description": "Desc 2",
                    }
                }
            ],
        },
    ]

    # Set up mock
    mock_request = MagicMock()
    mock_request.execute.side_effect = mock_responses
    youtube_client.playlistItems.return_value.list.return_value = mock_request

    # Call function
    videos = youtube_base.get_playlist_videos("playlist1")

    # Verify results
    assert len(videos) == 2
    assert videos[0] == {
        "video_id": "vid1",
        "title": "Video 1",
        "description": "Desc 1",
    }
    assert videos[1] == {
        "video_id": "vid2",
        "title": "Video 2",
        "description": "Desc 2",
    }

    # Verify API calls
    youtube_client.playlistItems.return_value.list.assert_any_call(
        part="snippet",
        playlistId="playlist1",
        maxResults=50,
        pageToken=None,
    )
    youtube_client.playlistItems.return_value.list.assert_any_call(
        part="snippet",
        playlistId="playlist1",
        maxResults=50,
        pageToken="token1",
    )


def test_get_playlist_videos_empty(youtube_base, youtube_client):
    """Test handling of empty playlist."""
    # Mock empty response
    mock_response = {"items": []}
    mock_request = MagicMock()
    mock_request.execute.return_value = mock_response
    youtube_client.playlistItems.return_value.list.return_value = mock_request

    # Call function
    videos = youtube_base.get_playlist_videos("playlist1")

    # Verify results
    assert videos == []


def test_get_playlist_videos_api_error(youtube_base, youtube_client):
    """Test handling of API error."""
    # Mock API error
    mock_request = MagicMock()
    mock_request.execute.side_effect = Exception("API error")
    youtube_client.playlistItems.return_value.list.return_value = mock_request

    # Call function
    videos = youtube_base.get_playlist_videos("playlist1")

    # Verify results
    assert videos == []


def test_get_playlist_videos_missing_description(youtube_base, youtube_client):
    """Test handling of missing description field."""
    # Mock response without description
    mock_response = {
        "items": [
            {
                "snippet": {
                    "resourceId": {"videoId": "vid1"},
                    "title": "Video 1",
                }
            }
        ]
    }

    # Set up mock
    mock_request = MagicMock()
    mock_request.execute.return_value = mock_response
    youtube_client.playlistItems.return_value.list.return_value = mock_request

    # Call function
    videos = youtube_base.get_playlist_videos("playlist1")

    # Verify results
    assert len(videos) == 1
    assert videos[0] == {
        "video_id": "vid1",
        "title": "Video 1",
        "description": "",
    }
