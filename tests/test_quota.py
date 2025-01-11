"""Tests for quota management."""

import unittest
from unittest.mock import patch, MagicMock
import pytest

from src.youtubesorter.quota import check_quota, with_quota_check


@pytest.mark.quota
class TestQuota(unittest.TestCase):
    """Test cases for quota management."""

    @patch("src.youtubesorter.quota.auth.get_youtube_service")
    def test_check_quota(self, mock_get_service):
        """Test checking quota usage."""
        # Mock YouTube service and response
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_request = MagicMock()
        mock_request.execute.return_value = {
            "responseDetails": {"quotaUsed": "5000", "quotaLimit": "10000"}
        }
        mock_service.channels().list.return_value = mock_request

        # Check quota
        used, remaining = check_quota()

        # Verify results
        self.assertEqual(used, 5000)
        self.assertEqual(remaining, 5000)
        mock_service.channels().list.assert_called_with(part="snippet", mine=True, maxResults=1)

    @patch("src.youtubesorter.quota.auth.get_youtube_service")
    def test_check_quota_no_service(self, mock_get_service):
        """Test handling of missing YouTube service."""
        mock_get_service.return_value = None

        with self.assertRaises(Exception) as context:
            check_quota()

        self.assertEqual(str(context.exception), "Failed to get YouTube service")

    @patch("src.youtubesorter.quota.check_quota")
    def test_quota_check_decorator_sufficient(self, mock_check):
        """Test quota check decorator with sufficient quota."""
        mock_check.return_value = (5000, 5000)  # Used, Remaining

        # Define test function with decorator
        @with_quota_check(min_required=1000)
        def test_func():
            return "success"

        # Call function and verify
        result = test_func()
        self.assertEqual(result, "success")
        mock_check.assert_called_once()

    @patch("src.youtubesorter.quota.check_quota")
    def test_quota_check_decorator_insufficient(self, mock_check):
        """Test quota check decorator with insufficient quota."""
        mock_check.return_value = (9900, 100)  # Used, Remaining

        # Define test function with decorator
        @with_quota_check(min_required=500)
        def test_func():
            return "success"

        # Call function and verify it raises
        with self.assertRaises(Exception) as context:
            test_func()

        self.assertIn("Insufficient quota remaining", str(context.exception))
        mock_check.assert_called_once()


if __name__ == "__main__":
    unittest.main()
