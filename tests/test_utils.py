"""Tests for utility functions."""

import unittest

from src import utils


class TestPlaylistUrlParsing(unittest.TestCase):
    """Test cases for playlist URL parsing."""

    def test_parse_raw_id(self):
        """Test parsing raw playlist IDs."""
        test_cases = [
            "PLZDXCYiIjJ8lw_7kvf9XWKrG_SJyGBz7f",
            "PLZDXCYiIjJ8m_SZsaimYCKhhNNNr-1XA3",
            "PL1234567890abcdef",
            "PLabc_123-456_789",
        ]
        for playlist_id in test_cases:
            with self.subTest(playlist_id=playlist_id):
                result = utils.parse_playlist_url(playlist_id)
                self.assertEqual(result, playlist_id)

    def test_parse_playlist_url(self):
        """Test parsing playlist URLs."""
        test_cases = [
            (
                "https://www.youtube.com/playlist" "?list=PLZDXCYiIjJ8lw_7kvf9XWKrG_SJyGBz7f",
                "PLZDXCYiIjJ8lw_7kvf9XWKrG_SJyGBz7f",
            ),
            (
                "https://youtube.com/playlist" "?list=PLZDXCYiIjJ8m_SZsaimYCKhhNNNr-1XA3",
                "PLZDXCYiIjJ8m_SZsaimYCKhhNNNr-1XA3",
            ),
            (
                "https://m.youtube.com/playlist" "?list=PL1234567890abcdef&index=1",
                "PL1234567890abcdef",
            ),
        ]
        for url, expected_id in test_cases:
            with self.subTest(url=url):
                result = utils.parse_playlist_url(url)
                self.assertEqual(result, expected_id)

    def test_invalid_input(self):
        """Test handling of invalid inputs."""
        test_cases = [
            "",  # Empty string
            "not a playlist",  # Random text
            "https://youtube.com/watch?v=12345",  # Video URL
            "https://youtube.com/playlist",  # Missing list parameter
            "https://youtube.com/playlist?list=",  # Empty list parameter
            "!@#$%^&*()",  # Invalid characters
        ]
        for invalid_input in test_cases:
            with self.subTest(invalid_input=invalid_input):
                with self.assertRaises(ValueError):
                    utils.parse_playlist_url(invalid_input)
