"""Tests for clear playlist functionality."""

import unittest
from unittest.mock import MagicMock, patch

from src.youtubesorter.clear_playlist import (
    create_parser,
    clear_playlist,
    main,
)


class TestClearPlaylist(unittest.TestCase):
    """Test cases for clear playlist functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.youtube = MagicMock()
        self.playlist_id = "test_playlist_123"
        self.test_videos = [
            {"video_id": "vid1", "title": "Video 1"},
            {"video_id": "vid2", "title": "Video 2"},
            {"video_id": "vid3", "title": "Video 3"},
        ]

    def test_create_parser(self):
        """Test argument parser creation."""
        parser = create_parser()

        # Test with valid playlist ID
        args = parser.parse_args(["test_playlist_123"])
        self.assertEqual(args.playlist_id, "test_playlist_123")

        # Test without playlist ID
        with self.assertRaises(SystemExit):
            parser.parse_args([])

    @patch("src.youtubesorter.clear_playlist.api.get_playlist_videos")
    @patch("src.youtubesorter.clear_playlist.api.YouTubeAPI")
    @patch("builtins.input", return_value="yes")
    def test_clear_playlist_success(self, mock_input, mock_api_class, mock_get_videos):
        """Test successful playlist clearing."""
        # Setup mocks
        mock_get_videos.return_value = self.test_videos
        mock_api = MagicMock()
        mock_api.batch_remove_videos_from_playlist.return_value = [
            "vid1",
            "vid2",
            "vid3",
        ]  # All videos removed successfully
        mock_api_class.return_value = mock_api

        # Execute
        result = clear_playlist(self.youtube, self.playlist_id)

        # Verify
        self.assertTrue(result)
        mock_get_videos.assert_called_once_with(self.youtube, self.playlist_id)
        mock_api.batch_remove_videos_from_playlist.assert_called_once_with(
            self.playlist_id, ["vid1", "vid2", "vid3"]
        )
        mock_input.assert_called_once()

    @patch("src.youtubesorter.clear_playlist.api.get_playlist_videos")
    @patch("builtins.input", return_value="no")
    def test_clear_playlist_cancelled(self, mock_input, mock_get_videos):
        """Test cancellation of playlist clearing."""
        # Setup
        mock_get_videos.return_value = self.test_videos

        # Execute
        result = clear_playlist(self.youtube, self.playlist_id)

        # Verify
        self.assertFalse(result)
        mock_get_videos.assert_called_once()
        mock_input.assert_called_once()

    @patch("src.youtubesorter.clear_playlist.api.get_playlist_videos")
    def test_clear_playlist_empty(self, mock_get_videos):
        """Test clearing empty playlist."""
        # Setup
        mock_get_videos.return_value = []

        # Execute
        result = clear_playlist(self.youtube, self.playlist_id)

        # Verify
        self.assertTrue(result)
        mock_get_videos.assert_called_once()

    @patch("src.youtubesorter.clear_playlist.api.get_playlist_videos")
    @patch("src.youtubesorter.clear_playlist.api.YouTubeAPI")
    @patch("builtins.input", return_value="yes")
    def test_clear_playlist_partial_success(self, mock_input, mock_api_class, mock_get_videos):
        """Test partial success in clearing playlist."""
        # Setup
        mock_get_videos.return_value = self.test_videos
        mock_api = MagicMock()
        mock_api.batch_remove_videos_from_playlist.return_value = [
            "vid1",
            "vid2",
        ]  # Only 2 videos removed successfully
        mock_api_class.return_value = mock_api

        # Execute
        result = clear_playlist(self.youtube, self.playlist_id)

        # Verify
        self.assertTrue(result)  # Still returns True as operation completed
        mock_get_videos.assert_called_once()
        mock_api.batch_remove_videos_from_playlist.assert_called_once_with(
            self.playlist_id, ["vid1", "vid2", "vid3"]
        )
        mock_input.assert_called_once()

    @patch("src.youtubesorter.clear_playlist.api.get_playlist_videos")
    def test_clear_playlist_api_error(self, mock_get_videos):
        """Test handling of API errors."""
        # Setup
        mock_get_videos.side_effect = Exception("API Error")

        # Execute
        result = clear_playlist(self.youtube, self.playlist_id)

        # Verify
        self.assertFalse(result)
        mock_get_videos.assert_called_once()

    @patch("src.youtubesorter.clear_playlist.auth.get_youtube_service")
    @patch("src.youtubesorter.clear_playlist.clear_playlist")
    def test_main_success(self, mock_clear_playlist, mock_get_service):
        """Test successful execution of main function."""
        # Setup
        mock_get_service.return_value = self.youtube
        mock_clear_playlist.return_value = True
        test_args = ["script_name", "test_playlist_123"]

        with patch("sys.argv", test_args):
            # Execute
            result = main()

            # Verify
            self.assertTrue(result)
            mock_get_service.assert_called_once()
            mock_clear_playlist.assert_called_once_with(self.youtube, "test_playlist_123")

    @patch("src.youtubesorter.clear_playlist.auth.get_youtube_service")
    def test_main_auth_failure(self, mock_get_service):
        """Test main function with authentication failure."""
        # Setup
        mock_get_service.return_value = None
        test_args = ["script_name", "test_playlist_123"]

        with patch("sys.argv", test_args):
            # Execute
            result = main()

            # Verify
            self.assertIsNone(result)
            mock_get_service.assert_called_once()


if __name__ == "__main__":
    unittest.main()
