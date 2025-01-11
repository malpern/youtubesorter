import pytest
from unittest.mock import patch
from src.youtubesorter.errors import (
    YouTubeError,
    RateLimitError,
    VideoNotFoundError,
    PlaylistNotFoundError,
    with_retry,
)


class TestErrors:
    @patch("time.sleep")
    def test_retry_success_first_try(self, mock_sleep):
        attempts = 0

        def test_func():
            nonlocal attempts
            attempts += 1
            return "success"

        decorated = with_retry(max_retries=3)(test_func)
        result = decorated()

        assert result == "success"
        assert attempts == 1
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    def test_retry_success_after_retry(self, mock_sleep):
        attempts = 0

        def test_func():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RateLimitError()
            return "success"

        decorated = with_retry(max_retries=3)(test_func)
        result = decorated()

        assert result == "success"
        assert attempts == 2
        mock_sleep.assert_called_once_with(2.0)

    @patch("time.sleep")
    def test_retry_max_retries_exceeded(self, mock_sleep):
        attempts = 0

        def test_func():
            nonlocal attempts
            attempts += 1
            raise RateLimitError()

        decorated = with_retry(max_retries=3)(test_func)

        with pytest.raises(RateLimitError):
            decorated()

        assert attempts == 4  # Initial try + 3 retries
        assert mock_sleep.call_count == 3

    @patch("time.sleep")
    def test_retry_non_retryable_error(self, mock_sleep):
        attempts = 0

        def test_func():
            nonlocal attempts
            attempts += 1
            raise ValueError("non-retryable")

        decorated = with_retry(max_retries=3)(test_func)

        with pytest.raises(ValueError):
            decorated()

        assert attempts == 1
        mock_sleep.assert_not_called()

    def test_youtube_error_message(self):
        error = YouTubeError("Test error message")
        assert str(error) == "Test error message"

    def test_video_not_found_error_message(self):
        error = VideoNotFoundError("Video not found")
        assert str(error) == "Video not found"

    def test_playlist_not_found_error_message(self):
        error = PlaylistNotFoundError("Playlist not found")
        assert str(error) == "Playlist not found"

    def test_rate_limit_error_message_without_retry(self):
        error = RateLimitError()
        assert str(error) == "Rate limit exceeded"

    def test_rate_limit_error_message_with_retry(self):
        error = RateLimitError(retry_after=30)
        assert str(error) == "Rate limit exceeded. Retry after 30 seconds"
