"""Integration tests for YouTube API wrapper with minimal mocking."""

import unittest
from unittest.mock import MagicMock, patch

from src.youtubesorter.api import YouTubeAPI
from src.youtubesorter.errors import PlaylistNotFoundError, YouTubeError


class TestAPIIntegration(unittest.TestCase):
    """Integration tests for YouTube API operations with minimal mocking."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock only the YouTube service, not individual methods
        self.mock_youtube = MagicMock()
        self.api = YouTubeAPI(self.mock_youtube)

    def test_get_playlist_videos_complete_flow(self):
        """Test the complete flow of getting videos from a playlist."""
        # Mock the YouTube API response at the service level
        mock_response = {
            "items": [
                {
                    "id": "item1",
                    "snippet": {
                        "resourceId": {"videoId": "video1"},
                        "title": "Test Video 1",
                        "description": "Description 1",
                    },
                },
                {
                    "id": "item2",
                    "snippet": {
                        "resourceId": {"videoId": "video2"},
                        "title": "Test Video 2",
                        "description": "Description 2",
                    },
                },
            ],
            "nextPageToken": "token123",
        }

        next_page_response = {
            "items": [
                {
                    "id": "item3",
                    "snippet": {
                        "resourceId": {"videoId": "video3"},
                        "title": "Test Video 3",
                        "description": "Description 3",
                    },
                }
            ]
        }

        # Set up the mock to return different responses for each call
        mock_request = MagicMock()
        mock_request.execute.side_effect = [mock_response, next_page_response]
        self.mock_youtube.playlistItems.return_value.list.return_value = mock_request

        # Get videos
        videos = self.api.get_playlist_videos("test_playlist")

        # Verify results
        self.assertEqual(len(videos), 3)
        self.assertEqual(videos[0]["video_id"], "video1")
        self.assertEqual(videos[0]["title"], "Test Video 1")
        self.assertEqual(videos[0]["description"], "Description 1")
        self.assertEqual(videos[1]["video_id"], "video2")
        self.assertEqual(videos[2]["video_id"], "video3")

        # Verify API was called correctly
        list_call = self.mock_youtube.playlistItems.return_value.list
        list_call.assert_called_with(
            part="snippet",
            playlistId="test_playlist",
            maxResults=50,
            pageToken="token123",
        )

    def test_batch_move_videos_to_playlist(self):
        """Test batch moving videos between playlists."""
        # Mock successful video retrieval
        self.mock_youtube.playlistItems.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "id": "item1",
                    "snippet": {
                        "resourceId": {"videoId": "video1"},
                        "title": "Video 1"
                    },
                },
                {
                    "id": "item2",
                    "snippet": {
                        "resourceId": {"videoId": "video2"},
                        "title": "Video 2"
                    },
                },
            ]
        }

        # Mock successful insert operations
        self.mock_youtube.playlistItems.return_value.insert.return_value.execute.return_value = True
        self.mock_youtube.playlistItems.return_value.delete.return_value.execute.return_value = True

        # Test batch move operation
        moved = self.api.batch_move_videos_to_playlist(
            target_playlist="target_playlist",
            video_ids=["video1", "video2"],
            source_playlist="source_playlist",
            remove_from_source=True
        )

        # Verify results
        self.assertEqual(len(moved), 2)
        self.assertIn("video1", moved)
        self.assertIn("video2", moved)

    def test_error_handling_and_recovery(self):
        """Test error handling and recovery in API operations."""
        # Mock API error for first attempt
        mock_execute = MagicMock()
        mock_execute.execute.side_effect = Exception("playlistNotFound")
        self.mock_youtube.playlistItems.return_value.list.return_value = mock_execute

        # Verify it raises YouTubeError with the correct message
        with self.assertRaises(YouTubeError) as context:
            self.api.get_playlist_videos("test_playlist")

        self.assertIn("Playlist test_playlist not found", str(context.exception))

        # Verify the API was called
        self.assertEqual(mock_execute.execute.call_count, 1)

    def test_playlist_not_found_handling(self):
        """Test handling of non-existent playlists."""
        # Mock empty response for non-existent playlist
        self.mock_youtube.playlists.return_value.list.return_value.execute.return_value = {
            "items": []
        }

        # Verify it raises the correct error
        with self.assertRaises(PlaylistNotFoundError):
            self.api.get_playlist_info("nonexistent_playlist")

    def test_quota_exceeded_handling(self):
        """Test handling of quota exceeded errors."""
        # Mock quota exceeded error
        self.mock_youtube.playlistItems.return_value.list.return_value.execute.side_effect = (
            Exception("quotaExceeded")
        )

        # Verify it raises YouTubeError with quota message
        with self.assertRaises(YouTubeError) as context:
            self.api.get_playlist_videos("test_playlist")

        self.assertIn("Failed to get playlist videos", str(context.exception))
