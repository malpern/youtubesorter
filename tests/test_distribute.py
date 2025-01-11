"""Test cases for video distribution."""

from unittest import TestCase
from unittest.mock import patch, MagicMock

from src.youtubesorter import distribute
from src.youtubesorter.api import YouTubeAPI


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
        api = YouTubeAPI(self.mock_youtube)
        with patch.object(YouTubeAPI, "get_playlist_videos") as mock_get:
            with patch("src.youtubesorter.common.classify_video_titles") as mock_classify:
                with patch.object(YouTubeAPI, "batch_move_videos_to_playlist") as mock_move:
                    mock_get.return_value = self.mock_videos
                    mock_classify.return_value = [True, True]
                    mock_move.return_value = ["video1", "video2"]

                    successful, failed = distribute.distribute_videos(
                        api,
                        "source_playlist",
                        ["target1"],
                        ["prompt1"],
                        verbose=True,
                    )

                    mock_get.assert_called_once_with("source_playlist")
                    mock_classify.assert_called_once_with(self.mock_videos, "prompt1")
                    mock_move.assert_called_once_with(
                        ["video1", "video2"], "source_playlist", "target1"
                    )

                    self.assertEqual(successful, ["video1", "video2"])
                    self.assertEqual(failed, [])
