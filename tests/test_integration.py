"""Integration tests for YouTube operations."""

import unittest
from unittest.mock import patch, MagicMock

from src.youtubesorter import common
from src.youtubesorter.api import YouTubeAPI


class TestIntegration(unittest.TestCase):
    """Integration test cases."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_youtube = MagicMock()
        self.source_playlist = "source_playlist"
        self.target_playlist = "target_playlist"
        self.test_videos = [
            {"video_id": "video1", "title": "Test Video 1"},
            {"video_id": "video2", "title": "Test Video 2"},
            {"video_id": "video3", "title": "Test Video 3"},
        ]

        # Mock batch move operation
        self.mock_batch_move = patch("src.youtubesorter.api.batch_move_videos_to_playlist").start()
        self.mock_batch_move.return_value = ["video1", "video2", "video3"]

        # Mock get videos operation
        self.mock_get_videos = patch("src.youtubesorter.api.get_playlist_videos").start()
        self.mock_get_videos.return_value = self.test_videos

        # Mock classifier
        self.mock_classify = patch("src.youtubesorter.classifier.classify_video_titles").start()
        self.mock_classify.return_value = [True, True, True]

    def tearDown(self):
        """Clean up test fixtures."""
        patch.stopall()

    def test_process_videos_success(self):
        """Test successful video processing."""
        api = YouTubeAPI(self.mock_youtube)
        with patch.object(YouTubeAPI, "get_playlist_videos") as mock_get:
            with patch.object(YouTubeAPI, "batch_move_videos_to_playlist") as mock_move:
                with patch("src.youtubesorter.common.classify_video_titles") as mock_classify:
                    mock_get.return_value = self.test_videos
                    mock_move.return_value = ["video1", "video2", "video3"]
                    mock_classify.return_value = [True, True, True]

                    successful, failed, skipped = common.process_videos(
                        api,
                        self.source_playlist,
                        "test filter",
                        self.target_playlist,
                    )

                    mock_get.assert_called_once_with(self.source_playlist)
                    mock_classify.assert_called_once_with(self.test_videos, "test filter")
                    mock_move.assert_called_once_with(
                        target_playlist_id=self.target_playlist,
                        video_ids=["video1", "video2", "video3"],
                        source_playlist_id=self.source_playlist,
                        remove_from_source=True
                    )

                    self.assertEqual(successful, ["video1", "video2", "video3"])
                    self.assertEqual(failed, [])
                    self.assertEqual(skipped, [])
