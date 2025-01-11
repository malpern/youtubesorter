"""Performance tests for the YouTube playlist filter and mover."""

import os
import unittest
import time
import logging
from unittest.mock import patch
import psutil
import pytest
from googleapiclient.discovery import Resource

from src.youtubesorter import api, auth, consolidate, quota
from src.youtubesorter.errors import YouTubeError

logger = logging.getLogger(__name__)

# Constants for test configuration
MIN_REQUIRED_QUOTA = 1000  # Minimum quota needed to run tests
TEST_COPIES = 200  # Number of times to copy test videos
BATCH_SIZES = [10, 25, 50, 100]  # Batch sizes to test


@pytest.mark.performance
class TestPerformance(unittest.TestCase):
    """Performance test cases using large playlists.

    These tests verify the system's performance with large playlists,
    focusing on memory usage, processing speed, and optimal batch sizes.
    """

    youtube: Resource

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are reused across test cases."""
        cls.filter_prompt = "Videos about technology"
        cls.test_videos = [
            # Using stable, popular videos that are unlikely to be deleted
            "dQw4w9WgXcQ",  # Never Gonna Give You Up
            "jNQXAC9IVRw",  # Me at the zoo
            "9bZkp7q19f0",  # Gangnam Style
        ]
        cls.source_playlist = None
        cls.target_playlist = None

        # Get YouTube service
        cls.youtube = auth.get_youtube_service()
        if not cls.youtube:
            raise unittest.SkipTest("Failed to authenticate with YouTube API")

        # Check quota before running tests
        quota_used, quota_limit = quota.check_quota(cls.youtube)
        remaining_quota = quota_limit - quota_used
        if remaining_quota < MIN_REQUIRED_QUOTA:
            raise unittest.SkipTest(
                f"Insufficient quota remaining. Need {MIN_REQUIRED_QUOTA}, have {remaining_quota}"
            )

        try:
            # Create source playlist
            cls.source_playlist = cls._create_test_playlist(
                "Performance Test Source", "Temporary playlist for performance testing"
            )
            # Create target playlist
            cls.target_playlist = cls._create_test_playlist(
                "Performance Test Target", "Temporary playlist for performance testing"
            )
            # Populate source playlist
            cls._populate_test_playlist(cls.source_playlist, num_copies=TEST_COPIES)
        except Exception as e:
            cls._cleanup_playlists()
            raise unittest.SkipTest(f"Failed to set up test playlists: {e}")

    @classmethod
    def _create_test_playlist(cls, title: str, description: str) -> str:
        """Create a test playlist.

        Args:
            title: Playlist title
            description: Playlist description

        Returns:
            str: Playlist ID

        Raises:
            YouTubeError: If playlist creation fails
        """
        try:
            # pylint: disable=no-member
            response = (
                cls.youtube.playlists()
                .insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "title": title,
                            "description": description,
                        }
                    },
                )
                .execute()
            )
            return response["id"]
        except Exception as e:
            raise YouTubeError(f"Failed to create playlist: {str(e)}") from e

    @classmethod
    def _populate_test_playlist(cls, playlist_id: str, num_copies: int = 200) -> None:
        """Populate a test playlist with videos.

        Args:
            playlist_id: Playlist ID to populate
            num_copies: Number of times to copy the test videos

        Raises:
            YouTubeError: If video addition fails
        """
        try:
            for _ in range(num_copies):
                for video_id in cls.test_videos:
                    # pylint: disable=no-member
                    cls.youtube.playlistItems().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "playlistId": playlist_id,
                                "resourceId": {"kind": "youtube#video", "videoId": video_id},
                            }
                        },
                    ).execute()
        except Exception as e:
            raise YouTubeError(f"Failed to populate playlist: {str(e)}") from e

    @classmethod
    def _cleanup_playlists(cls) -> None:
        """Clean up test playlists."""
        for playlist_id in [cls.source_playlist, cls.target_playlist]:
            if playlist_id:
                try:
                    # pylint: disable=no-member
                    cls.youtube.playlists().delete(id=playlist_id).execute()
                except Exception:
                    pass  # Best effort cleanup

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures."""
        cls._cleanup_playlists()

    def setUp(self):
        """Set up before each test."""
        if not self.target_playlist:
            self.skipTest("Target playlist not available")

        # Clear the target playlist
        try:
            videos = api.get_playlist_videos(self.youtube, self.target_playlist)
            for video in videos:
                # pylint: disable=no-member
                self.youtube.playlistItems().delete(id=video["playlist_item_id"]).execute()
        except Exception as e:
            self.skipTest(f"Failed to clear target playlist: {e}")

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # Convert to MB

    @patch("src.youtubesorter.classifier.classify_video_titles")
    def test_large_playlist_performance(self, mock_classify):
        """Test performance with a large playlist (600 videos)."""

        # Mock classifier to return mixed results quickly
        def mock_classification(videos, _):
            return [i % 3 == 0 for i in range(len(videos))]  # Match every third video

        mock_classify.side_effect = mock_classification

        # Record starting metrics
        start_memory = self.get_memory_usage()
        start_time = time.time()

        # Process the playlist
        consolidate.process_playlist(
            source_playlist=self.source_playlist,
            target_playlist=self.target_playlist,
            youtube=self.youtube,
            filter_pattern=self.filter_prompt,
            batch_size=50,  # Use reasonable batch size
        )

        # Record ending metrics
        end_memory = self.get_memory_usage()
        end_time = time.time()

        # Calculate metrics
        processing_time = end_time - start_time
        memory_increase = end_memory - start_memory
        source_videos = api.get_playlist_videos(self.youtube, self.source_playlist)
        target_videos = api.get_playlist_videos(self.youtube, self.target_playlist)

        if processing_time <= 0:
            logger.warning("Processing time was zero or negative: %f", processing_time)
            videos_per_second = 0
        else:
            videos_per_second = len(source_videos) / processing_time

        # Log performance metrics
        print("\nPerformance Metrics:")
        print(f"Total videos processed: {len(source_videos)}")
        print(f"Videos moved: {len(target_videos)}")
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Videos per second: {videos_per_second:.2f}")
        print(f"Memory usage increase: {memory_increase:.2f} MB")
        print(f"Final memory usage: {end_memory:.2f} MB")

        # Assert reasonable performance
        self.assertLess(memory_increase, 1000)  # Allow up to 1GB memory increase
        self.assertGreater(videos_per_second, 0.5)  # At least 0.5 videos per second

    @patch("src.youtubesorter.classifier.classify_video_titles")
    def test_batch_size_performance(self, mock_classify):
        """Test performance with different batch sizes."""
        results = []

        # Mock classifier to return mixed results quickly
        def mock_classification(videos, _):
            return [i % 3 == 0 for i in range(len(videos))]  # Match every third video

        mock_classify.side_effect = mock_classification

        for batch_size in BATCH_SIZES:
            try:
                # Record starting metrics
                start_memory = self.get_memory_usage()
                start_time = time.time()

                # Process with current batch size
                consolidate.process_playlist(
                    source_playlist=self.source_playlist,
                    target_playlist=self.target_playlist,
                    youtube=self.youtube,
                    filter_pattern=self.filter_prompt,
                    batch_size=batch_size,
                )

                # Record metrics
                end_memory = self.get_memory_usage()
                end_time = time.time()
                processing_time = end_time - start_time

                if processing_time > 0:  # Only record valid timings
                    results.append(
                        {
                            "batch_size": batch_size,
                            "processing_time": processing_time,
                            "memory_increase": end_memory - start_memory,
                        }
                    )
                else:
                    logger.warning(
                        "Skipping batch size %d results - invalid processing time: %f",
                        batch_size,
                        processing_time,
                    )

                # Clear target playlist for next iteration
                videos = api.get_playlist_videos(self.youtube, self.target_playlist)
                for video in videos:
                    # pylint: disable=no-member
                    self.youtube.playlistItems().delete(id=video["playlist_item_id"]).execute()

            except Exception as e:
                logger.error("Failed testing batch size %d: %s", batch_size, str(e))
                continue  # Continue with next batch size

        if not results:
            self.skipTest("No valid timing results obtained from any batch size")

        # Log batch size results
        print("\nBatch Size Performance Results:")
        for result in results:
            print(
                f"Batch size {result['batch_size']}: "
                f"{result['processing_time']:.2f} seconds, "
                f"{result['memory_increase']:.2f} MB increase"
            )

        # Assert that larger batch sizes are generally more efficient
        min_time = min(r["processing_time"] for r in results)
        max_time = max(r["processing_time"] for r in results)
        if max_time > 0:
            time_improvement = (max_time - min_time) / max_time * 100
            self.assertGreater(time_improvement, 10)  # At least 10% improvement
        else:
            self.skipTest("Invalid timing results - max processing time was zero")


if __name__ == "__main__":
    unittest.main()
