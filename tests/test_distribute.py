"""Test cases for video distribution."""

from unittest import TestCase
from unittest.mock import patch, MagicMock

from src.youtubesorter import distribute
from src.youtubesorter.core import YouTubeBase


class TestDistribute(TestCase):
    """Test cases for video distribution."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_youtube = MagicMock()
        self.mock_videos = [
            {"video_id": "video1", "title": "Test 1"},
            {"video_id": "video2", "title": "Test 2"},
        ]

    def test_distribute_videos_success(self):
        """Test successful video distribution."""
        youtube = MagicMock(spec=YouTubeBase)
        youtube.get_playlist_videos.return_value = self.mock_videos
        youtube.batch_move_videos_to_playlist.return_value = ["video1", "video2"]

        with patch("src.youtubesorter.common.classify_video_titles") as mock_classify:
            mock_classify.return_value = [True, True]

            success = distribute.distribute_videos(
                youtube,
                "source_playlist",
                ["target1"],
                ["prompt1"],
                verbose=True,
            )

            youtube.get_playlist_videos.assert_called_once_with("source_playlist")
            mock_classify.assert_called_once_with(self.mock_videos, "prompt1")
            youtube.batch_move_videos_to_playlist.assert_called_once_with(
                "source_playlist", "target1", ["video1", "video2"]
            )

            self.assertTrue(success)
