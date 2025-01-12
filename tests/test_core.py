"""Tests for core YouTube API functionality."""

import pytest
from unittest.mock import MagicMock, call

from src.youtubesorter.core import YouTubeBase
from src.youtubesorter.errors import PlaylistNotFoundError, YouTubeError


@pytest.fixture
def api(youtube_client: MagicMock) -> YouTubeBase:
    """Create YouTubeBase instance with mock client.
    
    Args:
        youtube_client: Mock YouTube API client
        
    Returns:
        YouTubeBase: API instance for testing
    """
    return YouTubeBase(youtube_client)


def test_get_playlist_info(api: YouTubeBase, youtube_client: MagicMock):
    """Test getting playlist information."""
    info = api.get_playlist_info("playlist1")
    
    assert info["title"] == "Playlist 1"
    assert info["description"] == "Description 1"
    
    youtube_client.playlists.return_value.list.assert_called_once_with(
        part="snippet",
        id="playlist1",
        maxResults=1
    )


def test_get_playlist_info_not_found(api: YouTubeBase, youtube_client: MagicMock):
    """Test getting info for non-existent playlist."""
    youtube_client.playlists.return_value.list.return_value.execute.side_effect = Exception(
        "playlistNotFound"
    )
    
    with pytest.raises(PlaylistNotFoundError):
        api.get_playlist_info("nonexistent")


def test_get_playlist_videos(api: YouTubeBase, youtube_client: MagicMock):
    """Test getting videos from playlist."""
    videos = api.get_playlist_videos("playlist1")
    
    assert len(videos) == 2
    assert videos[0]["video_id"] == "vid1"
    assert videos[0]["title"] == "Video 1"
    
    youtube_client.playlistItems.return_value.list.assert_called_with(
        part="snippet",
        playlistId="playlist1",
        maxResults=50,
        pageToken=None
    )


def test_get_playlist_videos_pagination(api: YouTubeBase, youtube_client: MagicMock):
    """Test getting videos with pagination."""
    # First page has next token
    first_response = {
        "items": [
            {
                "snippet": {
                    "resourceId": {"videoId": "vid1"},
                    "title": "Video 1",
                    "description": "Description 1"
                }
            }
        ],
        "nextPageToken": "token1"
    }
    # Second page has no next token
    second_response = {
        "items": [
            {
                "snippet": {
                    "resourceId": {"videoId": "vid2"},
                    "title": "Video 2",
                    "description": "Description 2"
                }
            }
        ]
    }
    
    youtube_client.playlistItems.return_value.list.return_value.execute.side_effect = [
        first_response,
        second_response
    ]
    
    videos = api.get_playlist_videos("playlist1")
    
    assert len(videos) == 2
    assert videos[0]["video_id"] == "vid1"
    assert videos[1]["video_id"] == "vid2"
    
    # Verify both pages were requested
    calls = youtube_client.playlistItems.return_value.list.call_args_list
    assert len(calls) == 2
    assert calls[0] == call(part="snippet", playlistId="playlist1", maxResults=50, pageToken=None)
    assert calls[1] == call(part="snippet", playlistId="playlist1", maxResults=50, pageToken="token1")


def test_get_playlist_videos_not_found(api: YouTubeBase, youtube_client: MagicMock):
    """Test getting videos from non-existent playlist."""
    youtube_client.playlistItems.return_value.list.return_value.execute.side_effect = Exception(
        "playlistNotFound"
    )
    
    with pytest.raises(PlaylistNotFoundError):
        api.get_playlist_videos("nonexistent")


def test_batch_add_videos_to_playlist(api: YouTubeBase, youtube_client: MagicMock):
    """Test adding multiple videos to playlist."""
    video_ids = ["vid1", "vid2"]
    successful = api.batch_add_videos_to_playlist(
        playlist_id="playlist1",
        video_ids=video_ids
    )
    
    assert successful == video_ids
    assert youtube_client.playlistItems.return_value.insert.call_count == 2


def test_batch_add_videos_playlist_not_found(api: YouTubeBase, youtube_client: MagicMock):
    """Test adding videos to non-existent playlist."""
    youtube_client.playlistItems.return_value.insert.return_value.execute.side_effect = Exception(
        "playlistNotFound"
    )
    
    with pytest.raises(PlaylistNotFoundError):
        api.batch_add_videos_to_playlist(
            playlist_id="nonexistent",
            video_ids=["vid1"]
        )


def test_batch_add_videos_partial_failure(api: YouTubeBase, youtube_client: MagicMock):
    """Test handling partial failure when adding videos."""
    # First video succeeds, second fails
    youtube_client.playlistItems.return_value.insert.return_value.execute.side_effect = [
        {},
        Exception("API Error")
    ]
    
    successful = api.batch_add_videos_to_playlist(
        playlist_id="playlist1",
        video_ids=["vid1", "vid2"]
    )
    
    assert successful == ["vid1"]


def test_batch_remove_videos_from_playlist(api: YouTubeBase, youtube_client: MagicMock):
    """Test removing multiple videos from playlist."""
    successful = api.batch_remove_videos_from_playlist(
        playlist_id="playlist1",
        video_ids=["vid1", "vid2"]
    )
    
    assert successful == ["vid1", "vid2"]
    assert youtube_client.playlistItems.return_value.delete.call_count == 2


def test_batch_remove_videos_playlist_not_found(api: YouTubeBase, youtube_client: MagicMock):
    """Test removing videos from non-existent playlist."""
    youtube_client.playlistItems.return_value.list.return_value.execute.side_effect = Exception(
        "playlistNotFound"
    )
    
    with pytest.raises(PlaylistNotFoundError):
        api.batch_remove_videos_from_playlist(
            playlist_id="nonexistent",
            video_ids=["vid1"]
        )


def test_batch_remove_videos_partial_failure(api: YouTubeBase, youtube_client: MagicMock):
    """Test handling partial failure when removing videos."""
    # First delete succeeds, second fails
    youtube_client.playlistItems.return_value.delete.return_value.execute.side_effect = [
        {},
        Exception("API Error")
    ]
    
    successful = api.batch_remove_videos_from_playlist(
        playlist_id="playlist1",
        video_ids=["vid1", "vid2"]
    )
    
    assert successful == ["vid1"]


def test_batch_move_videos_to_playlist(api: YouTubeBase, youtube_client: MagicMock):
    """Test moving videos between playlists."""
    video_ids = ["vid1", "vid2"]
    successful = api.batch_move_videos_to_playlist(
        playlist_id="target1",
        video_ids=video_ids,
        source_playlist_id="source1",
        remove_from_source=True
    )
    
    assert successful == video_ids
    assert youtube_client.playlistItems.return_value.insert.call_count == 2
    assert youtube_client.playlistItems.return_value.delete.call_count == 2


def test_batch_move_videos_without_remove(api: YouTubeBase, youtube_client: MagicMock):
    """Test moving videos without removing from source."""
    video_ids = ["vid1", "vid2"]
    successful = api.batch_move_videos_to_playlist(
        playlist_id="target1",
        video_ids=video_ids,
        remove_from_source=False
    )
    
    assert successful == video_ids
    assert youtube_client.playlistItems.return_value.insert.call_count == 2
    assert youtube_client.playlistItems.return_value.delete.call_count == 0
