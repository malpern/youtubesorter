"""Test cases for consolidate command."""

from unittest import TestCase
from unittest.mock import patch, MagicMock
import json
import os
import tempfile

from src.youtubesorter import consolidate


class TestProcessPlaylist(TestCase):
    """Test cases for process_playlist function."""

    def setUp(self):
        """Set up test fixtures."""
        self.youtube = MagicMock()
        self.api = MagicMock()
        self.api.get_playlist_videos.return_value = [
            {"video_id": "video1", "title": "Test Video 1"},
            {"video_id": "video2", "title": "Test Video 2"},
        ]
        self.api.batch_move_videos_to_playlist.return_value = ["video1", "video2"]
        self.api.batch_add_videos_to_playlist.return_value = ["video1", "video2"]

        patcher = patch("src.youtubesorter.consolidate.YouTubeAPI")
        self.mock_api_class = patcher.start()
        self.mock_api_class.return_value = self.api
        self.addCleanup(patcher.stop)

    def test_process_playlist_move_success(self):
        """Test successful video move operation."""
        processed, failed, skipped = consolidate.process_playlist(
            self.youtube, "source1", "target1", copy=False, verbose=True
        )

        self.assertEqual(processed, ["video1", "video2"])
        self.assertEqual(failed, [])
        self.assertEqual(skipped, [])
        self.api.get_playlist_videos.assert_called_once_with("source1")
        self.api.batch_move_videos_to_playlist.assert_called_once_with(
            "source1", "target1", ["video1", "video2"]
        )

    def test_process_playlist_copy_success(self):
        """Test successful video copy operation."""
        processed, failed, skipped = consolidate.process_playlist(
            self.youtube, "source1", "target1", copy=True, verbose=True
        )

        self.assertEqual(processed, ["video1", "video2"])
        self.assertEqual(failed, [])
        self.assertEqual(skipped, [])
        self.api.get_playlist_videos.assert_called_once_with("source1")
        self.api.batch_add_videos_to_playlist.assert_called_once_with(
            "target1", ["video1", "video2"]
        )

    def test_process_playlist_empty(self):
        """Test processing empty playlist."""
        self.api.get_playlist_videos.return_value = []

        processed, failed, skipped = consolidate.process_playlist(
            self.youtube, "source1", "target1"
        )

        self.assertEqual(processed, [])
        self.assertEqual(failed, [])
        self.assertEqual(skipped, [])
        self.api.get_playlist_videos.assert_called_once_with("source1")
        self.api.batch_move_videos_to_playlist.assert_not_called()

    def test_process_playlist_with_limit(self):
        """Test processing playlist with video limit."""
        processed, failed, skipped = consolidate.process_playlist(
            self.youtube, "source1", "target1", limit=1
        )

        self.assertEqual(processed, ["video1", "video2"])
        self.assertEqual(failed, [])
        self.assertEqual(skipped, [])
        self.api.get_playlist_videos.assert_called_once_with("source1")
        self.api.batch_move_videos_to_playlist.assert_called_once_with(
            "source1", "target1", ["video1"]
        )

    def test_process_playlist_with_processed_videos(self):
        """Test processing playlist with already processed videos."""
        processed_videos = {"video1"}

        processed, failed, skipped = consolidate.process_playlist(
            self.youtube, "source1", "target1", processed_videos=processed_videos
        )

        self.assertEqual(processed, ["video1", "video2"])
        self.assertEqual(failed, [])
        self.assertEqual(skipped, [])
        self.api.batch_move_videos_to_playlist.assert_called_once_with(
            "source1", "target1", ["video2"]
        )

    def test_process_playlist_partial_failure(self):
        """Test processing playlist with partial failure."""
        self.api.batch_move_videos_to_playlist.return_value = ["video1"]

        processed, failed, skipped = consolidate.process_playlist(
            self.youtube, "source1", "target1"
        )

        self.assertEqual(processed, ["video1"])
        self.assertEqual(failed, ["video2"])
        self.assertEqual(skipped, [])

    def test_process_playlist_api_error(self):
        """Test handling API error during processing."""
        self.api.get_playlist_videos.side_effect = Exception("API Error")

        with patch("src.youtubesorter.consolidate.logger") as mock_logger:
            processed, failed, skipped = consolidate.process_playlist(
                self.youtube, "source1", "target1"
            )

            self.assertEqual(processed, [])
            self.assertEqual(failed, [])
            self.assertEqual(skipped, [])
            self.api.get_playlist_videos.assert_called_once_with("source1")
            self.api.batch_move_videos_to_playlist.assert_not_called()
            mock_logger.error.assert_called_once_with(
                "Error processing playlist %s: %s", "source1", "API Error"
            )


class TestConsolidateUndo(TestCase):
    """Test cases for consolidate undo functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.test_dir, ".youtubesorter_undo_state.json")
        self.test_operation = MagicMock(
            timestamp="2023-01-01T00:00:00",
            operation_type="consolidate",
            source_playlists=["source1", "source2"],
            target_playlists=["target1"],
            was_move=True,
            videos=["video1", "video2"],
            target_mapping={"video1": "target1", "video2": "target1"},
        )

        # Write test state
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": self.test_operation.timestamp,
                    "operation_type": self.test_operation.operation_type,
                    "source_playlists": self.test_operation.source_playlists,
                    "target_playlists": self.test_operation.target_playlists,
                    "was_move": self.test_operation.was_move,
                    "videos": self.test_operation.videos,
                    "target_mapping": self.test_operation.target_mapping,
                },
                f,
            )

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.remove(self.state_file)
            os.rmdir(self.test_dir)
        except OSError:
            pass

    @patch("src.youtubesorter.common.undo_operation")
    def test_undo_move_operation(self, mock_undo):
        """Test undoing a move operation."""
        youtube = MagicMock()
        consolidate.undo_last_operation(youtube, verbose=True)

        mock_undo.assert_called_once_with(youtube, verbose=True)

    @patch("src.youtubesorter.common.undo_operation")
    def test_undo_copy_operation(self, mock_undo):
        """Test undoing a copy operation."""
        # Update test state to be a copy operation
        self.test_operation.was_move = False
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": self.test_operation.timestamp,
                    "operation_type": self.test_operation.operation_type,
                    "source_playlists": self.test_operation.source_playlists,
                    "target_playlists": self.test_operation.target_playlists,
                    "was_move": self.test_operation.was_move,
                    "videos": self.test_operation.videos,
                    "target_mapping": self.test_operation.target_mapping,
                },
                f,
            )

        youtube = MagicMock()
        consolidate.undo_last_operation(youtube, verbose=True)

        mock_undo.assert_called_once_with(youtube, verbose=True)

    @patch("src.youtubesorter.common.undo_operation")
    def test_undo_api_error(self, mock_undo):
        """Test error handling during undo."""
        mock_undo.side_effect = Exception("API Error")

        with patch("src.youtubesorter.errors.log_error") as mock_log:
            youtube = MagicMock()
            consolidate.undo_last_operation(youtube)

            mock_undo.assert_called_once_with(youtube, verbose=False)
            mock_log.assert_called_once()

    @patch("src.youtubesorter.common.undo_operation")
    def test_undo_cancelled(self, mock_undo):
        """Test cancelling undo operation."""
        youtube = MagicMock()
        consolidate.undo_last_operation(youtube)

        mock_undo.assert_called_once_with(youtube, verbose=False)


class TestConsolidateArgParsing(TestCase):
    """Test cases for consolidate command argument parsing."""

    def test_consolidate_command(self):
        """Test parsing consolidate command arguments."""
        parser = consolidate.create_parser()
        args = parser.parse_args(
            ["consolidate", "source1,source2", "-t", "target1", "--copy", "-v"]
        )

        self.assertEqual(args.command, "consolidate")
        self.assertEqual(args.source_playlists, "source1,source2")
        self.assertEqual(args.target_playlist, "target1")
        self.assertTrue(args.copy)
        self.assertTrue(args.verbose)

    def test_undo_command(self):
        """Test parsing undo command arguments."""
        parser = consolidate.create_parser()
        args = parser.parse_args(["undo"])

        self.assertEqual(args.command, "undo")
        self.assertFalse(args.verbose)

    def test_undo_verbose(self):
        """Test parsing undo command with verbose flag."""
        parser = consolidate.create_parser()
        args = parser.parse_args(["undo", "-v"])

        self.assertEqual(args.command, "undo")
        self.assertTrue(args.verbose)


class TestConsolidatePlaylists(TestCase):
    """Test cases for consolidate_playlists function."""

    def setUp(self):
        """Set up test fixtures."""
        self.youtube = MagicMock()
        self.api = MagicMock()
        self.api.get_playlist_videos.return_value = [
            {"video_id": "video1", "title": "Test Video 1"},
            {"video_id": "video2", "title": "Test Video 2"},
        ]
        self.api.batch_move_videos_to_playlist.return_value = ["video1", "video2"]
        self.api.batch_add_videos_to_playlist.return_value = ["video1", "video2"]

        with patch("src.youtubesorter.consolidate.YouTubeAPI") as mock_api:
            mock_api.return_value = self.api
            self.mock_api = mock_api

    def test_consolidate_playlists_success(self):
        """Test successful consolidation of playlists."""
        with patch("src.youtubesorter.consolidate.process_playlist") as mock_process:
            # Set up successful process_playlist results
            mock_process.return_value = (["video1", "video2"], [], [])

            with patch("src.youtubesorter.consolidate.RecoveryManager") as mock_recovery:
                mock_manager = MagicMock()
                mock_recovery.return_value = mock_manager

                consolidate.consolidate_playlists(
                    self.youtube, ["source1", "source2"], "target1", copy=False, verbose=True
                )

                # Verify process_playlist was called for each source playlist
                self.assertEqual(mock_process.call_count, 2)
                for call_args in mock_process.call_args_list:
                    args, kwargs = call_args
                    self.assertEqual(args[0], self.youtube)
                    self.assertIn(args[1], ["source1", "source2"])
                    self.assertEqual(args[2], "target1")
                    self.assertFalse(kwargs.get("copy", False))

                # Verify recovery manager was initialized and used
                mock_recovery.assert_called_once_with(
                    playlist_id="source1", operation_type="consolidate"
                )
                self.assertEqual(mock_manager.assign_video.call_count, 4)  # 2 videos * 2 playlists

    def test_consolidate_playlists_empty_source(self):
        """Test consolidation with empty source playlists."""
        with patch("src.youtubesorter.consolidate.process_playlist") as mock_process:
            # Set up empty process_playlist results
            mock_process.return_value = ([], [], [])

            with patch("src.youtubesorter.consolidate.RecoveryManager") as mock_recovery:
                mock_manager = MagicMock()
                mock_recovery.return_value = mock_manager

                consolidate.consolidate_playlists(self.youtube, ["source1", "source2"], "target1")

                # Verify process_playlist was called for each source
                self.assertEqual(mock_process.call_count, 2)

                # Verify recovery manager was initialized but not used
                mock_recovery.assert_called_once_with(
                    playlist_id="source1", operation_type="consolidate"
                )
                mock_manager.assign_video.assert_not_called()

    def test_consolidate_playlists_resume(self):
        """Test resuming consolidation from previous state."""
        with patch("src.youtubesorter.consolidate.process_playlist") as mock_process:
            # Set up successful process_playlist results
            mock_process.return_value = (["video2"], [], [])

            with patch("src.youtubesorter.consolidate.RecoveryManager") as mock_recovery:
                mock_manager = MagicMock()
                mock_manager.processed_videos = ["video1"]
                mock_manager.failed_videos = ["video3"]
                mock_recovery.return_value = mock_manager

                consolidate.consolidate_playlists(
                    self.youtube, ["source1", "source2"], "target1", resume=True
                )

                # Verify process_playlist was called with correct processed_videos
                self.assertEqual(mock_process.call_count, 2)
                for call_args in mock_process.call_args_list:
                    args, kwargs = call_args
                    self.assertEqual(kwargs.get("processed_videos"), {"video1"})

    def test_consolidate_playlists_retry_failed(self):
        """Test retrying failed videos during consolidation."""
        with patch("src.youtubesorter.consolidate.process_playlist") as mock_process:
            # Set up successful process_playlist results
            mock_process.return_value = (["video1", "video2"], [], [])

            with patch("src.youtubesorter.consolidate.RecoveryManager") as mock_recovery:
                mock_manager = MagicMock()
                mock_manager.processed_videos = ["video1"]
                mock_manager.failed_videos = ["video2"]
                mock_recovery.return_value = mock_manager

                consolidate.consolidate_playlists(
                    self.youtube, ["source1", "source2"], "target1", retry_failed=True
                )

                # Verify process_playlist was called with empty failed_videos (retry all)
                self.assertEqual(mock_process.call_count, 2)
                for call_args in mock_process.call_args_list:
                    args, kwargs = call_args
                    self.assertEqual(kwargs.get("failed_videos"), set())

    def test_consolidate_playlists_with_limit(self):
        """Test consolidation with video limit."""
        with patch("src.youtubesorter.consolidate.process_playlist") as mock_process:
            # Set up successful process_playlist results
            mock_process.return_value = (["video1"], [], [])

            with patch("src.youtubesorter.consolidate.RecoveryManager") as mock_recovery:
                mock_manager = MagicMock()
                mock_recovery.return_value = mock_manager

                consolidate.consolidate_playlists(
                    self.youtube, ["source1", "source2"], "target1", limit=1
                )

                # Verify process_playlist was called only once since we reached the limit
                mock_process.assert_called_once()
                args, kwargs = mock_process.call_args
                self.assertEqual(args[0], self.youtube)
                self.assertEqual(args[1], "source1")
                self.assertEqual(args[2], "target1")
                self.assertEqual(kwargs.get("limit"), 1)

                # Verify recovery manager was initialized and used
                mock_recovery.assert_called_once_with(
                    playlist_id="source1", operation_type="consolidate"
                )
                mock_manager.assign_video.assert_called_once_with("video1", "target1")

    def test_consolidate_playlists_copy(self):
        """Test consolidation with copy mode."""
        with patch("src.youtubesorter.consolidate.process_playlist") as mock_process:
            # Set up successful process_playlist results
            mock_process.return_value = (["video1", "video2"], [], [])

            with patch("src.youtubesorter.consolidate.RecoveryManager") as mock_recovery:
                mock_manager = MagicMock()
                mock_recovery.return_value = mock_manager

                consolidate.consolidate_playlists(
                    self.youtube, ["source1", "source2"], "target1", copy=True
                )

                # Verify process_playlist was called with copy=True
                self.assertEqual(mock_process.call_count, 2)
                for call_args in mock_process.call_args_list:
                    args, kwargs = call_args
                    self.assertTrue(kwargs.get("copy", False))
