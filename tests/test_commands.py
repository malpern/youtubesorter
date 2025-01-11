"""Test cases for base command class."""

import unittest
from unittest.mock import MagicMock, patch
import pytest
from src.youtubesorter.commands import YouTubeCommand
from src.youtubesorter.commands.filter import FilterCommand
from src.youtubesorter.commands.move import MoveCommand
from src.youtubesorter.errors import YouTubeError


class TestYouTubeCommand(unittest.TestCase):
    """Tests for base YouTubeCommand class."""

    class TestCommand(YouTubeCommand):
        """Test command implementation."""

        def __init__(
            self, youtube=None, fail_validation: bool = False, should_fail: bool = False
        ) -> None:
            """Initialize test command."""
            super().__init__(youtube)
            self.fail_validation = fail_validation
            self.should_fail = should_fail
            self.ran = False

        def validate(self) -> None:
            """Validate command parameters."""
            if not self.youtube:
                raise YouTubeError("YouTube service not available")
            if self.fail_validation:
                raise ValueError("Validation failed")

        def _run(self) -> bool:
            """Run the command."""
            if self.should_fail:
                raise Exception("Command failed")
            self.ran = True
            return True

        def execute(self) -> bool:
            """Execute the command."""
            if not self.youtube:
                raise YouTubeError("YouTube service not available")
            self.validate()
            return self.run()

    def setUp(self) -> None:
        """Set up test environment."""
        self.mock_youtube = MagicMock()

    @pytest.mark.unit
    def test_all_commands_inherit_from_base(self) -> None:
        """Test that all command classes inherit from YouTubeCommand."""
        self.assertTrue(issubclass(FilterCommand, YouTubeCommand))
        self.assertTrue(issubclass(MoveCommand, YouTubeCommand))

    def test_normal_execution(self) -> None:
        """Test normal command execution flow."""
        cmd = self.TestCommand(self.mock_youtube)
        result = cmd.run()
        self.assertTrue(result)

    def test_validation_error(self) -> None:
        """Test handling of validation errors."""
        with patch("src.youtubesorter.auth.get_youtube_service") as mock_get_service:
            mock_get_service.return_value = self.mock_youtube

            cmd = self.TestCommand(youtube=self.mock_youtube, fail_validation=True)

            with self.assertRaises(ValueError):
                cmd.execute()

    def test_runtime_error(self) -> None:
        """Test handling of runtime errors."""
        with patch("src.youtubesorter.auth.get_youtube_service") as mock_get_service:
            mock_get_service.return_value = self.mock_youtube

            cmd = self.TestCommand(youtube=self.mock_youtube, should_fail=True)

            with self.assertRaises(YouTubeError):
                cmd.execute()

    def test_auth_failure(self) -> None:
        """Test handling of authentication failure."""
        with patch("src.youtubesorter.auth.get_youtube_service") as mock_get_service:
            mock_get_service.return_value = None

            cmd = self.TestCommand(youtube=None)

            with self.assertRaises(YouTubeError):
                cmd.execute()

    def test_dry_run(self) -> None:
        """Test dry run mode."""
        with patch("src.youtubesorter.auth.get_youtube_service") as mock_get_service:
            mock_get_service.return_value = self.mock_youtube

            cmd = self.TestCommand(youtube=self.mock_youtube)
            cmd.execute()

            self.assertTrue(cmd.ran)


class TestMoveCommand(unittest.TestCase):
    """Tests for MoveCommand class."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.mock_youtube = MagicMock()
        self.source_playlist = "source123"
        self.target_playlist = "target456"
        self.command = MoveCommand(
            youtube=self.mock_youtube,
            source_playlist=self.source_playlist,
            target_playlist=self.target_playlist,
        )

    def test_validate_resume_without_state(self) -> None:
        """Test validation when resume is requested but no state exists."""
        self.command.resume = True
        with patch("src.youtubesorter.utils.find_latest_state", return_value=None):
            with self.assertRaises(ValueError) as ctx:
                self.command.validate()
            self.assertIn("No recovery state found", str(ctx.exception))

    def test_validate_resume_destination_without_resume(self) -> None:
        """Test validation when resume-destination is specified without resume."""
        self.command.resume = False
        self.command.resume_destination = "dest123"
        with self.assertRaises(ValueError) as ctx:
            self.command.validate()
        self.assertIn("requires --resume", str(ctx.exception))

    def test_validate_resume_destination_not_found(self) -> None:
        """Test validation when specified destination doesn't exist in state."""
        self.command.resume = True
        self.command.resume_destination = "nonexistent"

        # Mock recovery manager
        mock_manager = MagicMock()
        mock_manager.destination_metadata = {"other_dest": {}}

        with patch("glob.glob") as mock_glob:
            mock_glob.return_value = ["state.json"]
            with patch("os.path.getmtime") as mock_getmtime:
                mock_getmtime.return_value = 123456789
                with patch("src.youtubesorter.recovery.RecoveryManager", return_value=mock_manager):
                    with self.assertRaises(ValueError) as ctx:
                        self.command.validate()
                    self.assertIn("not found in recovery state", str(ctx.exception))

    def test_validate_resume_destination_already_completed(self) -> None:
        """Test validation when specified destination is already completed."""
        self.command.resume = True
        self.command.resume_destination = "dest123"

        # Mock recovery manager with proper initialization
        mock_manager = MagicMock()
        mock_manager.destination_metadata = {"dest123": {"id": "dest123"}}
        mock_manager.get_destination_progress.return_value = {"completed": True}
        mock_manager.operation_type = "move"  # Set correct operation type
        mock_manager.playlist_id = "source123"  # Set correct playlist ID

        with patch("src.youtubesorter.utils.find_latest_state", return_value="state.json"):
            with patch("src.youtubesorter.recovery.RecoveryManager", return_value=mock_manager):
                # Initialize recovery manager before validation
                self.command.recovery = mock_manager
                with self.assertRaises(ValueError) as ctx:
                    self.command.validate()
                self.assertIn("already completed", str(ctx.exception))

    def test_run_with_resume_destination(self) -> None:
        """Test running command with destination-specific resume."""
        self.command.resume = True
        self.command.resume_destination = "dest123"
        self.command.youtube = MagicMock()

        # Mock recovery manager with proper initialization
        mock_manager = MagicMock()
        mock_manager.processed_videos = {"video1"}
        mock_manager.failed_videos = {"video2"}
        mock_manager.get_videos_for_destination.return_value = {"video3", "video4"}
        mock_manager.destination_metadata = {"dest123": {"id": "dest123"}}
        mock_manager.destination_progress = {"dest123": {"completed": False}}
        mock_manager.get_destination_progress.return_value = {"completed": False}

        # Set up the recovery manager before validation
        self.command.recovery = mock_manager

        # Mock API responses
        mock_videos = [
            {"video_id": "video3", "title": "Test 3"},
            {"video_id": "video4", "title": "Test 4"},
            {"video_id": "video5", "title": "Test 5"},
        ]

        with patch("glob.glob") as mock_glob:
            mock_glob.return_value = ["state.json"]
            with patch("os.path.getmtime") as mock_getmtime:
                mock_getmtime.return_value = 123456789
                with patch("src.youtubesorter.api.get_playlist_videos", return_value=mock_videos):
                    with patch(
                        "src.youtubesorter.api.batch_move_videos_to_playlist",
                        return_value=["video3", "video4"],
                    ):
                        with patch(
                            "src.youtubesorter.recovery.RecoveryManager", return_value=mock_manager
                        ):
                            with patch(
                                "src.youtubesorter.api.get_playlist_info",
                                return_value={"name": "Test Playlist"},
                            ):
                                quota_info = {"used": 0, "remaining": 10000, "limit": 10000}
                                with patch(
                                    "src.youtubesorter.quota.check_quota", return_value=quota_info
                                ):
                                    # Run the command
                                    result = self.command.run()
                                    self.assertTrue(result)


class TestFilterCommand(unittest.TestCase):
    """Tests for FilterCommand class."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.mock_youtube = MagicMock()
        self.source_playlist = "source123"
        self.target_playlist = "target456"
        self.filter_pattern = "test prompt"
        self.command = FilterCommand(
            youtube=self.mock_youtube,
            source_playlist=self.source_playlist,
            target_playlist=self.target_playlist,
            filter_pattern=self.filter_pattern,
        )

    def test_validate_resume_without_state(self) -> None:
        """Test validation when resume is requested but no state exists."""
        self.command.resume = True
        with patch("glob.glob", return_value=[]):
            with self.assertRaises(ValueError) as ctx:
                self.command.validate()
            self.assertIn("No recovery state found", str(ctx.exception))

    def test_validate_resume_destination_without_resume(self) -> None:
        """Test validation when resume-destination is specified without resume."""
        self.command.resume = False
        self.command.resume_destination = "dest123"
        with self.assertRaises(ValueError) as ctx:
            self.command.validate()
        self.assertIn("requires --resume", str(ctx.exception))

    def test_validate_resume_destination_not_found(self) -> None:
        """Test validation when specified destination doesn't exist in state."""
        self.command.resume = True
        self.command.resume_destination = "nonexistent"

        # Mock recovery manager
        mock_manager = MagicMock()
        mock_manager.destination_metadata = {"other_dest": {}}

        with patch("glob.glob") as mock_glob:
            mock_glob.return_value = ["state.json"]
            with patch("os.path.getmtime") as mock_getmtime:
                mock_getmtime.return_value = 123456789
                with patch("src.youtubesorter.recovery.RecoveryManager", return_value=mock_manager):
                    with self.assertRaises(ValueError) as ctx:
                        self.command.validate()
                    self.assertIn("not found in recovery state", str(ctx.exception))

    def test_validate_resume_destination_already_completed(self) -> None:
        """Test validation when specified destination is already completed."""
        self.command.resume = True
        self.command.resume_destination = "dest123"

        # Mock recovery manager with proper initialization
        mock_manager = MagicMock()
        mock_manager.destination_metadata = {"dest123": {"id": "dest123"}}
        mock_manager.get_destination_progress.return_value = {"completed": True}
        mock_manager.operation_type = "filter"  # Set correct operation type
        mock_manager.playlist_id = "source123"  # Set correct playlist ID

        with patch("src.youtubesorter.utils.find_latest_state", return_value="state.json"):
            with patch("src.youtubesorter.recovery.RecoveryManager", return_value=mock_manager):
                # Initialize recovery manager before validation
                self.command.recovery = mock_manager
                with self.assertRaises(ValueError) as ctx:
                    self.command.validate()
                self.assertIn("already completed", str(ctx.exception))

    def test_run_with_resume_destination(self) -> None:
        """Test running command with destination-specific resume."""
        self.command.resume = True
        self.command.resume_destination = "dest123"
        self.command.youtube = MagicMock()

        # Mock recovery manager with proper initialization
        mock_manager = MagicMock()
        mock_manager.processed_videos = {"video1"}
        mock_manager.failed_videos = {"video2"}
        mock_manager.destination_metadata = {"dest123": {"id": "dest123"}}
        mock_manager.destination_progress = {"dest123": {"completed": False}}
        mock_manager.get_destination_progress.return_value = {"completed": False}

        # Set up the recovery manager before validation
        self.command.recovery = mock_manager

        # Mock API responses
        mock_videos = [
            {"video_id": "video3", "title": "Test 3"},
            {"video_id": "video4", "title": "Test 4"},
            {"video_id": "video5", "title": "Test 5"},
        ]

        with patch("glob.glob") as mock_glob:
            mock_glob.return_value = ["state.json"]
            with patch("os.path.getmtime") as mock_getmtime:
                mock_getmtime.return_value = 123456789
                with patch("src.youtubesorter.api.get_playlist_videos", return_value=mock_videos):
                    with patch(
                        "src.youtubesorter.common.process_videos",
                        return_value=(["video3", "video4"], [], []),
                    ):
                        with patch(
                            "src.youtubesorter.recovery.RecoveryManager", return_value=mock_manager
                        ):
                            with patch(
                                "src.youtubesorter.api.get_playlist_info",
                                return_value={"name": "Test Playlist"},
                            ):
                                quota_info = {"used": 0, "remaining": 10000, "limit": 10000}
                                with patch(
                                    "src.youtubesorter.quota.check_quota", return_value=quota_info
                                ):
                                    # Run the command
                                    result = self.command.run()
                                    self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
