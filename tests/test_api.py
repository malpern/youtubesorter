"""Tests for the YouTube API wrapper."""

import pytest
from unittest.mock import MagicMock, patch

from src.youtubesorter.api import (
    YouTubeAPI,
    get_playlist_videos,
    batch_move_videos_to_playlist,
    get_playlist_info,
)
from src.youtubesorter.errors import PlaylistNotFoundError, YouTubeError


@pytest.fixture
def youtube_client():
    """Create a mock YouTube client."""
    client = MagicMock()

    # Mock playlist items list
    playlist_items = MagicMock()
    client.playlistItems.return_value.list.return_value = playlist_items
    playlist_items.execute.return_value = {
        "items": [
            {
                "id": "item1",
                "contentDetails": {"videoId": "vid1"},
                "snippet": {"title": "Video 1", "description": "Description 1"},
            },
            {
                "id": "item2",
                "contentDetails": {"videoId": "vid2"},
                "snippet": {"title": "Video 2", "description": "Description 2"},
            },
        ]
    }

    # Mock playlist items insert
    client.playlistItems.return_value.insert.return_value.execute.return_value = {}

    # Mock playlist items delete
    client.playlistItems.return_value.delete.return_value.execute.return_value = {}

    # Mock playlists list
    playlists = MagicMock()
    client.playlists.return_value.list.return_value = playlists
    playlists.execute.return_value = {
        "items": [
            {
                "id": "playlist1",
                "snippet": {"title": "Playlist 1", "description": "Description 1"},
            }
        ]
    }

    return client


@pytest.fixture
def api(youtube_client):
    """Create a YouTubeAPI instance with mock client."""
    return YouTubeAPI(youtube_client)


def test_get_playlist_videos(api, youtube_client):
    """Test getting videos from a playlist."""
    videos = api.get_playlist_videos("playlist1")

    assert len(videos) == 2
    assert videos[0]["video_id"] == "vid1"
    assert videos[0]["title"] == "Video 1"
    assert videos[0]["description"] == "Description 1"

    youtube_client.playlistItems.return_value.list.assert_called_once_with(
        part="snippet,contentDetails",
        playlistId="playlist1",
        maxResults=50,
        pageToken=None,
    )


def test_get_playlist_videos_pagination(api, youtube_client):
    """Test getting videos with pagination."""
    # First response has next page token
    first_response = {
        "items": [
            {
                "id": "item1",
                "contentDetails": {"videoId": "vid1"},
                "snippet": {"title": "Video 1", "description": "Desc 1"},
            }
        ],
        "nextPageToken": "token1",
    }
    # Second response has no next page token
    second_response = {
        "items": [
            {
                "id": "item2",
                "contentDetails": {"videoId": "vid2"},
                "snippet": {"title": "Video 2", "description": "Desc 2"},
            }
        ],
    }

    youtube_client.playlistItems.return_value.list.return_value.execute.side_effect = [
        first_response,
        second_response,
    ]

    videos = api.get_playlist_videos("playlist1")

    assert len(videos) == 2
    assert videos[0]["video_id"] == "vid1"
    assert videos[1]["video_id"] == "vid2"

    # Verify both pages were requested
    list_calls = youtube_client.playlistItems.return_value.list.call_args_list
    assert len(list_calls) == 2
    assert list_calls[0].kwargs["pageToken"] is None
    assert list_calls[1].kwargs["pageToken"] == "token1"


def test_get_playlist_videos_not_found(api, youtube_client):
    """Test getting videos from a non-existent playlist."""
    youtube_client.playlistItems.return_value.list.return_value.execute.side_effect = Exception(
        "playlistNotFound"
    )

    with pytest.raises(PlaylistNotFoundError):
        api.get_playlist_videos("nonexistent")


def test_get_playlist_videos_api_error(api, youtube_client):
    """Test handling API errors when getting videos."""
    youtube_client.playlistItems.return_value.list.return_value.execute.side_effect = Exception(
        "API Error"
    )

    with pytest.raises(YouTubeError):
        api.get_playlist_videos("playlist1")


def test_batch_add_videos_to_playlist(api, youtube_client):
    """Test adding multiple videos to a playlist."""
    video_ids = ["vid1", "vid2"]
    successful = api.batch_add_videos_to_playlist("playlist1", video_ids)

    assert successful == video_ids
    assert youtube_client.playlistItems.return_value.insert.call_count == 2


def test_batch_add_videos_to_playlist_partial_failure(api, youtube_client):
    """Test handling partial failure when adding videos."""
    # First video succeeds, second fails
    youtube_client.playlistItems.return_value.insert.return_value.execute.side_effect = [
        {},
        Exception("API Error"),
    ]

    video_ids = ["vid1", "vid2"]
    successful = api.batch_add_videos_to_playlist("playlist1", video_ids)

    assert successful == ["vid1"]


def test_batch_add_videos_playlist_not_found(api, youtube_client):
    """Test adding videos to a non-existent playlist."""
    youtube_client.playlistItems.return_value.insert.return_value.execute.side_effect = Exception(
        "playlistNotFound"
    )

    with pytest.raises(PlaylistNotFoundError):
        api.batch_add_videos_to_playlist("nonexistent", ["vid1"])


def test_batch_remove_videos_from_playlist(api, youtube_client):
    """Test removing multiple videos from a playlist."""
    # Mock getting playlist items
    youtube_client.playlistItems.return_value.list.return_value.execute.return_value = {
        "items": [
            {"id": "item1", "contentDetails": {"videoId": "vid1"}},
            {"id": "item2", "contentDetails": {"videoId": "vid2"}},
        ]
    }

    successful = api.batch_remove_videos_from_playlist("playlist1", ["vid1", "vid2"])

    assert successful == ["vid1", "vid2"]
    assert youtube_client.playlistItems.return_value.delete.call_count == 2


def test_batch_remove_videos_playlist_not_found(api, youtube_client):
    """Test removing videos from a non-existent playlist."""
    youtube_client.playlistItems.return_value.list.return_value.execute.side_effect = Exception(
        "playlistNotFound"
    )

    with pytest.raises(PlaylistNotFoundError):
        api.batch_remove_videos_from_playlist("nonexistent", ["vid1"])


def test_batch_move_videos_to_playlist(api, youtube_client):
    """Test moving videos between playlists."""
    # Mock getting playlist items for removal
    youtube_client.playlistItems.return_value.list.return_value.execute.return_value = {
        "items": [
            {"id": "item1", "contentDetails": {"videoId": "vid1"}},
            {"id": "item2", "contentDetails": {"videoId": "vid2"}},
        ]
    }

    video_ids = ["vid1", "vid2"]
    successful = api.batch_move_videos_to_playlist("source", "target", video_ids)

    assert successful == video_ids
    assert youtube_client.playlistItems.return_value.insert.call_count == 2
    assert youtube_client.playlistItems.return_value.delete.call_count == 2


def test_batch_move_videos_without_remove(api, youtube_client):
    """Test moving videos without removing from source."""
    video_ids = ["vid1", "vid2"]
    successful = api.batch_move_videos_to_playlist(
        "source", "target", video_ids, remove_from_source=False
    )

    assert successful == video_ids
    assert youtube_client.playlistItems.return_value.insert.call_count == 2
    assert youtube_client.playlistItems.return_value.delete.call_count == 0


def test_get_playlist_info(api, youtube_client):
    """Test getting playlist information."""
    info = api.get_playlist_info("playlist1")

    assert info["title"] == "Playlist 1"
    assert info["description"] == "Description 1"

    youtube_client.playlists.return_value.list.assert_called_once_with(
        part="snippet",
        id="playlist1",
    )


def test_get_playlist_info_not_found(api, youtube_client):
    """Test getting info for a non-existent playlist."""
    youtube_client.playlists.return_value.list.return_value.execute.side_effect = Exception(
        "playlistNotFound"
    )

    with pytest.raises(PlaylistNotFoundError):
        api.get_playlist_info("nonexistent")


# Test module-level functions


@patch("src.youtubesorter.api.get_youtube_service")
def test_module_get_playlist_videos(mock_get_service, youtube_client):
    """Test module-level get_playlist_videos function."""
    mock_get_service.return_value = youtube_client

    videos = get_playlist_videos("playlist1")
    assert len(videos) == 2
    assert videos[0]["video_id"] == "vid1"


@patch("src.youtubesorter.api.get_youtube_service")
def test_module_get_playlist_videos_no_service(mock_get_service):
    """Test handling no YouTube service."""
    mock_get_service.return_value = None

    with pytest.raises(YouTubeError):
        get_playlist_videos("playlist1")


@patch("src.youtubesorter.api.get_youtube_service")
def test_module_batch_move_videos(mock_get_service, youtube_client):
    """Test module-level batch_move_videos_to_playlist function."""
    mock_get_service.return_value = youtube_client

    # Mock getting playlist items for removal
    youtube_client.playlistItems.return_value.list.return_value.execute.return_value = {
        "items": [
            {"id": "item1", "contentDetails": {"videoId": "vid1"}},
            {"id": "item2", "contentDetails": {"videoId": "vid2"}},
        ]
    }

    video_ids = ["vid1", "vid2"]
    successful = batch_move_videos_to_playlist("source", "target", video_ids)
    assert successful == video_ids


@patch("src.youtubesorter.api.get_youtube_service")
def test_module_get_playlist_info(mock_get_service, youtube_client):
    """Test module-level get_playlist_info function."""
    mock_get_service.return_value = youtube_client

    info = get_playlist_info("playlist1")
    assert info["title"] == "Playlist 1"
    assert info["description"] == "Description 1"


def test_get_playlist_videos_no_service():
    """Test getting videos when YouTube service is not available."""
    with patch("src.youtubesorter.api.get_youtube_service", return_value=None):
        with pytest.raises(YouTubeError, match="Failed to get YouTube service"):
            get_playlist_videos("playlist1")


def test_batch_move_videos_no_service():
    """Test moving videos when YouTube service is not available."""
    with patch("src.youtubesorter.api.get_youtube_service", return_value=None):
        with pytest.raises(YouTubeError, match="Failed to get YouTube service"):
            batch_move_videos_to_playlist("source", "target", ["vid1"])


def test_get_playlist_info_no_service():
    """Test getting playlist info when YouTube service is not available."""
    with patch("src.youtubesorter.api.get_youtube_service", return_value=None):
        with pytest.raises(YouTubeError, match="Failed to get YouTube service"):
            get_playlist_info("playlist1")


def test_batch_add_videos_api_error(api, youtube_client):
    """Test handling API errors when adding videos."""
    youtube_client.playlistItems.return_value.insert.return_value.execute.side_effect = Exception(
        "API Error"
    )

    successful = api.batch_add_videos_to_playlist("playlist1", ["vid1"])
    assert successful == []


def test_batch_remove_videos_pagination(api, youtube_client):
    """Test removing videos with pagination."""
    # First response has next page token
    first_response = {
        "items": [
            {"id": "item1", "contentDetails": {"videoId": "vid1"}},
        ],
        "nextPageToken": "token1",
    }
    # Second response has the second video
    second_response = {
        "items": [
            {"id": "item2", "contentDetails": {"videoId": "vid2"}},
        ]
    }

    youtube_client.playlistItems.return_value.list.return_value.execute.side_effect = [
        first_response,
        second_response,
    ]

    successful = api.batch_remove_videos_from_playlist("playlist1", ["vid1", "vid2"])
    assert successful == ["vid1", "vid2"]

    # Verify both pages were requested
    list_calls = youtube_client.playlistItems.return_value.list.call_args_list
    assert len(list_calls) == 2
    assert list_calls[0].kwargs["pageToken"] is None
    assert list_calls[1].kwargs["pageToken"] == "token1"


def test_batch_remove_videos_api_error(api, youtube_client):
    """Test handling API errors when removing videos."""
    youtube_client.playlistItems.return_value.list.return_value.execute.return_value = {
        "items": [
            {"id": "item1", "contentDetails": {"videoId": "vid1"}},
            {"id": "item2", "contentDetails": {"videoId": "vid2"}},
        ]
    }

    # First delete succeeds, second fails
    youtube_client.playlistItems.return_value.delete.return_value.execute.side_effect = [
        {},
        Exception("API Error"),
    ]

    successful = api.batch_remove_videos_from_playlist("playlist1", ["vid1", "vid2"])
    assert successful == ["vid1"]


def test_get_playlist_videos_with_cache(api, youtube_client):
    """Test getting videos with cache enabled."""
    with patch("src.youtubesorter.api.get_youtube_service") as mock_service:
        mock_service.return_value = youtube_client
        videos = get_playlist_videos("playlist1", use_cache=True)
        assert len(videos) == 2


def test_get_playlist_videos_without_cache(api, youtube_client):
    """Test getting videos with cache disabled."""
    with patch("src.youtubesorter.api.get_youtube_service") as mock_service:
        mock_service.return_value = youtube_client
        videos = get_playlist_videos("playlist1", use_cache=False)
        assert len(videos) == 2
