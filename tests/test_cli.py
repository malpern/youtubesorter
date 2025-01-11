"""Test cases for CLI functionality."""

from unittest import TestCase, main
from unittest.mock import patch, MagicMock, call

from src.youtubesorter import cli, common
from src.youtubesorter import commands


class TestCLI(TestCase):
    """Test cases for CLI functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        patcher = patch("src.youtubesorter.cli.logger", self.mock_logger)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_list_destinations_no_state(self):
        """Test listing destinations with no recovery state."""
        with patch("src.youtubesorter.utils.find_latest_state", return_value=None):
            cli.list_recovery_destinations("playlist123", "filter")
            self.mock_logger.info.assert_called_once_with(
                "No recovery state found for playlist %s", "playlist123"
            )

    def test_list_destinations_with_state(self):
        """Test listing destinations with existing recovery state."""
        # Mock recovery manager
        mock_manager = MagicMock()
        mock_manager.destination_metadata = {
            "dest1": {"title": "Playlist 1"},
            "dest2": {"title": "Playlist 2"},
        }
        mock_manager.operation_type = "filter"
        mock_manager.playlist_id = "playlist123"
        mock_manager.get_destination_progress.side_effect = [
            {"success_count": 10, "failure_count": 2, "completed": True},
            {"success_count": 5, "failure_count": 1, "completed": False},
        ]

        # Mock RecoveryManager class
        mock_recovery_manager = MagicMock(return_value=mock_manager)

        with patch("src.youtubesorter.utils.find_latest_state", return_value="state.json"):
            with patch("src.youtubesorter.cli.RecoveryManager", mock_recovery_manager):
                cli.list_recovery_destinations("playlist123", "filter")

                # Verify logger calls
                calls = [
                    call("Available destinations in recovery state:"),
                    call(
                        "  %s (%s): %d successful, %d failed - %s",
                        "Playlist 1",
                        "dest1",
                        10,
                        2,
                        "completed",
                    ),
                    call(
                        "  %s (%s): %d successful, %d failed - %s",
                        "Playlist 2",
                        "dest2",
                        5,
                        1,
                        "in progress",
                    ),
                ]
                self.mock_logger.info.assert_has_calls(calls, any_order=False)

    def test_main_auth_failure(self):
        """Test handling of authentication failure."""
        args = ["filter", "source123", "target456", "test prompt"]

        with patch("sys.argv", ["youtubesorter"] + args):
            with patch("src.youtubesorter.auth.get_youtube_service", return_value=None):
                result = cli.main()
                self.assertEqual(result, 1)
                self.mock_logger.error.assert_called_with(
                    "Command failed: %s", "Failed to get YouTube service"
                )

    def test_main_filter_with_resume_destination(self):
        """Test filter command with resume-destination option."""
        args = [
            "filter",
            "source123",
            "target456",
            "test prompt",
            "--resume",
            "--resume-destination",
            "dest123",
            "--verbose",
            "--dry-run",
            "--retry-failed",
            "--limit",
            "10",
        ]

        # Mock YouTube service and recovery manager
        mock_youtube = MagicMock()
        mock_manager = MagicMock()
        mock_manager.configure_mock(
            destination_metadata={"dest123": {"title": "Test Playlist"}},
            operation_type="filter",
            playlist_id="source123",
            processed_videos=set(),
            failed_videos=set(),
            video_assignments={},
        )
        mock_manager.get_destination_progress.return_value = {"completed": False}

        # Mock load_state to not change attributes
        mock_manager.load_state = MagicMock()

        # Mock playlist info
        mock_playlist_info = {"title": "Test Playlist", "description": "Test Description"}

        # Create mock command class for filter command
        mock_command = MagicMock(
            spec=commands.filter.FilterCommand
        )  # Use spec to get filter command behavior
        mock_command.validate.return_value = None  # Mock validate() to return None
        mock_command._validated = True  # Initialize _validated flag as True
        mock_command.run.return_value = True  # Mock run() to return True directly
        mock_command_class = MagicMock(return_value=mock_command)

        with patch("sys.argv", ["youtubesorter"] + args):
            with patch("src.youtubesorter.auth.get_youtube_service", return_value=mock_youtube):
                with patch("src.youtubesorter.utils.find_latest_state", return_value="state.json"):
                    with patch(
                        "src.youtubesorter.recovery.RecoveryManager", return_value=mock_manager
                    ):
                        with patch("src.youtubesorter.api.get_playlist_videos", return_value=[]):
                            with patch(
                                "src.youtubesorter.api.get_playlist_info",
                                return_value=mock_playlist_info,
                            ):
                                with patch(
                                    "src.youtubesorter.quota.check_quota", return_value=(0, 10000)
                                ):
                                    with patch(
                                        "src.youtubesorter.commands.FilterCommand",
                                        mock_command_class,
                                    ):
                                        # Run CLI
                                        result = cli.main()

                                        # Verify results
                                        self.assertEqual(result, 0)

    def test_main_move_with_resume_destination(self):
        """Test move command with resume-destination option."""
        args = [
            "move",
            "source123",
            "target456",
            "--resume",
            "--resume-destination",
            "dest123",
            "--verbose",
            "--dry-run",
            "--retry-failed",
            "--limit",
            "10",
        ]

        # Mock YouTube service and recovery manager
        mock_youtube = MagicMock()
        mock_manager = MagicMock()
        mock_manager.configure_mock(
            destination_metadata={"dest123": {"title": "Test Playlist"}},
            operation_type="move",
            playlist_id="source123",
            processed_videos=set(),
            failed_videos=set(),
            video_assignments={},
        )
        mock_manager.get_destination_progress.return_value = {"completed": False}

        # Mock load_state to not change attributes
        mock_manager.load_state = MagicMock()

        # Mock playlist info
        mock_playlist_info = {"title": "Test Playlist", "description": "Test Description"}

        # Create mock command class for move command
        mock_command = MagicMock(
            spec=commands.move.MoveCommand
        )  # Use spec to get move command behavior
        mock_command.validate.return_value = None  # Mock validate() to return None
        mock_command._validated = True  # Initialize _validated flag as True
        mock_command.run.return_value = True  # Mock run() to return True directly
        mock_command_class = MagicMock(return_value=mock_command)

        with patch("sys.argv", ["youtubesorter"] + args):
            with patch("src.youtubesorter.auth.get_youtube_service", return_value=mock_youtube):
                with patch("src.youtubesorter.utils.find_latest_state", return_value="state.json"):
                    with patch(
                        "src.youtubesorter.recovery.RecoveryManager", return_value=mock_manager
                    ):
                        with patch("src.youtubesorter.api.get_playlist_videos", return_value=[]):
                            with patch(
                                "src.youtubesorter.api.get_playlist_info",
                                return_value=mock_playlist_info,
                            ):
                                with patch(
                                    "src.youtubesorter.quota.check_quota", return_value=(0, 10000)
                                ):
                                    with patch(
                                        "src.youtubesorter.commands.MoveCommand",
                                        mock_command_class,
                                    ):
                                        # Run CLI
                                        result = cli.main()

                                        # Verify results
                                        self.assertEqual(result, 0)

    def test_main_list_destinations_invalid_command(self):
        """Test list-destinations command with invalid operation type."""
        args = ["list-destinations", "source123", "--operation", "invalid"]

        with patch("sys.argv", ["youtubesorter"] + args):
            result = cli.main()
            self.assertEqual(result, 1)

    def test_create_parser(self):
        """Test argument parser creation."""
        parser = cli.create_parser()

        # Test basic parser attributes
        self.assertEqual(parser.description, "YouTube playlist management tool")

        # Test move command
        args = parser.parse_args(["move", "source123", "target456"])
        self.assertEqual(args.command, "move")
        self.assertEqual(args.source, "source123")
        self.assertEqual(args.target, "target456")

        # Test filter command
        args = parser.parse_args(["filter", "source123", "target456", "test prompt"])
        self.assertEqual(args.command, "filter")
        self.assertEqual(args.prompt, "test prompt")

        # Test quota command
        args = parser.parse_args(["quota"])
        self.assertEqual(args.command, "quota")

        # Test undo command
        args = parser.parse_args(["undo"])
        self.assertEqual(args.command, "undo")

        # Test list-destinations command
        args = parser.parse_args(["list-destinations", "playlist123", "--operation", "move"])
        self.assertEqual(args.command, "list-destinations")
        self.assertEqual(args.playlist, "playlist123")
        self.assertEqual(args.operation, "move")

    def test_main_quota_command(self):
        """Test quota command execution."""
        args = ["quota", "--verbose"]

        with patch("sys.argv", ["youtubesorter"] + args):
            with patch("src.youtubesorter.auth.get_youtube_service") as mock_auth:
                with patch("src.youtubesorter.quota.check_quota", return_value=(5000, 10000)):
                    mock_auth.return_value = MagicMock()
                    result = cli.main()
                    self.assertEqual(result, 0)

    def test_main_undo_command_success(self):
        """Test successful undo command execution."""
        args = ["undo", "--verbose"]

        with patch("sys.argv", ["youtubesorter"] + args):
            with patch("src.youtubesorter.auth.get_youtube_service") as mock_auth:
                with patch("src.youtubesorter.quota.check_quota", return_value=(0, 10000)):
                    with patch("src.youtubesorter.common.undo_operation", return_value=True):
                        mock_auth.return_value = MagicMock()
                        result = cli.main()
                        self.assertEqual(result, 0)

    def test_main_undo_command_failure(self):
        """Test failed undo command execution."""
        args = ["undo", "--verbose"]

        with patch("sys.argv", ["youtubesorter"] + args):
            with patch("src.youtubesorter.auth.get_youtube_service") as mock_auth:
                with patch("src.youtubesorter.quota.check_quota", return_value=(0, 10000)):
                    with patch("src.youtubesorter.common.undo_operation", return_value=False):
                        mock_auth.return_value = MagicMock()
                        result = cli.main()
                        self.assertEqual(result, 1)

    def test_main_quota_exceeded(self):
        """Test handling of exceeded quota."""
        args = ["move", "source123", "target456"]

        with patch("sys.argv", ["youtubesorter"] + args):
            with patch("src.youtubesorter.auth.get_youtube_service") as mock_auth:
                with patch("src.youtubesorter.quota.check_quota", return_value=(10000, 10000)):
                    mock_auth.return_value = MagicMock()
                    result = cli.main()
                    self.assertEqual(result, 1)
                    self.mock_logger.error.assert_called_with(
                        "Quota limit reached: %d/%d", 10000, 10000
                    )

    def test_main_invalid_command(self):
        """Test handling of invalid command."""
        args = ["invalid_command"]

        with patch("sys.argv", ["youtubesorter"] + args):
            with patch("src.youtubesorter.auth.get_youtube_service") as mock_auth:
                with patch("src.youtubesorter.quota.check_quota", return_value=(0, 10000)):
                    mock_auth.return_value = MagicMock()
                    result = cli.main()
                    self.assertEqual(result, 1)

    def test_list_destinations_operation_type_mismatch(self):
        """Test list-destinations with operation type mismatch."""
        with patch("src.youtubesorter.utils.find_latest_state", return_value="state.json"):
            mock_manager = MagicMock()
            mock_manager.operation_type = "move"

            with patch("src.youtubesorter.cli.RecoveryManager", return_value=mock_manager):
                with self.assertRaises(ValueError):
                    cli.list_recovery_destinations("playlist123", "filter")


if __name__ == "__main__":
    main()
