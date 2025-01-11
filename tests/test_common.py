"""Tests for the common module."""

import argparse
import json
import unittest
from unittest.mock import MagicMock, patch, mock_open

import pytest

from src.youtubesorter import common
from src.youtubesorter.api import YouTubeAPI


@pytest.fixture
def youtube_client():
    """Create a mock YouTube client."""
    return MagicMock()


@pytest.fixture
def youtube_api():
    """Create a mock YouTube API."""
    api = MagicMock()
    api.get_playlist_videos = MagicMock()
    api.batch_move_videos_to_playlist = MagicMock()
    api.batch_add_videos_to_playlist = MagicMock()
    return api


def test_classify_video_titles():
    """Test video title classification."""
    videos = [
        {"title": "Python Tutorial"},
        {"title": "JavaScript Basics"},
        {"title": "Python Advanced"},
    ]
    filter_prompt = "python"

    with patch("src.youtubesorter.classifier.classify_video_titles") as mock_classify:
        mock_classify.return_value = [True, False, True]
        results = common.classify_video_titles(videos, filter_prompt)
        assert results == [True, False, True]
        mock_classify.assert_called_once_with(videos, filter_prompt)


def test_find_latest_state():
    """Test finding latest state file."""
    with patch("src.youtubesorter.common.glob") as mock_glob:
        # Test with no state files
        mock_glob.return_value = []
        assert common.find_latest_state("playlist1") is None

        # Test with multiple state files
        mock_glob.return_value = [
            ".youtubesorter_playlist1_1.json",
            ".youtubesorter_playlist1_2.json",
        ]
        with patch("os.path.getctime") as mock_getctime:
            mock_getctime.side_effect = lambda x: 2 if x.endswith("2.json") else 1
            assert common.find_latest_state("playlist1") == ".youtubesorter_playlist1_2.json"


def test_add_common_arguments():
    """Test adding common arguments to parser."""
    parser = argparse.ArgumentParser()
    common.add_common_arguments(parser)

    args = parser.parse_args([])
    assert not args.verbose
    assert not args.dry_run
    assert args.resume is None

    args = parser.parse_args(["-v", "-d", "-r", "playlist1"])
    assert args.verbose
    assert args.dry_run
    assert args.resume == "playlist1"


def test_add_undo_command():
    """Test adding undo command to parser."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    common.add_undo_command(subparsers)

    args = parser.parse_args(["undo"])
    assert args.command == "undo"
    assert not args.verbose

    args = parser.parse_args(["undo", "-v"])
    assert args.command == "undo"
    assert args.verbose


def test_log_operation_summary(caplog):
    """Test logging operation summary."""
    caplog.set_level("INFO")
    common.log_operation_summary(
        "move",
        "playlist1",
        ["vid1", "vid2"],
        ["vid3"],
        ["vid4"],
        verbose=True,
    )

    assert "Operation Summary for move" in caplog.text
    assert "Target Playlist: playlist1" in caplog.text
    assert "Total Processed: 2" in caplog.text
    assert "Successfully Moved: 2" in caplog.text
    assert "Failed: 1" in caplog.text
    assert "Skipped: 1" in caplog.text
    assert "vid1" in caplog.text
    assert "vid2" in caplog.text
    assert "vid3" in caplog.text
    assert "vid4" in caplog.text


def test_process_videos_no_source_videos(youtube_api):
    """Test processing videos when source playlist is empty."""
    youtube_api.get_playlist_videos.return_value = []
    result = common.process_videos(youtube_api, "source", "target", "filter")
    assert result == ([], [], [])
    youtube_api.get_playlist_videos.assert_called_once_with("source")
    youtube_api.batch_move_videos_to_playlist.assert_not_called()


def test_process_videos_no_matches(youtube_api):
    """Test processing videos when no videos match filter."""
    youtube_api.get_playlist_videos.return_value = [{"video_id": "vid1", "title": "Video 1"}]
    with patch("src.youtubesorter.common.classify_video_titles") as mock_classify:
        mock_classify.return_value = [False]
        result = common.process_videos(youtube_api, "source", "target", "filter")
        assert result == ([], [], [])
        youtube_api.get_playlist_videos.assert_called_once_with("source")
        youtube_api.batch_move_videos_to_playlist.assert_not_called()


def test_process_videos_dry_run(youtube_api):
    """Test processing videos in dry run mode."""
    youtube_api.get_playlist_videos.return_value = [{"video_id": "vid1", "title": "Video 1"}]
    with patch("src.youtubesorter.common.classify_video_titles") as mock_classify:
        mock_classify.return_value = [True]
        result = common.process_videos(youtube_api, "source", "target", "filter", dry_run=True)
        assert result == (["vid1"], [], [])
        youtube_api.get_playlist_videos.assert_called_once_with("source")
        youtube_api.batch_move_videos_to_playlist.assert_not_called()


def test_process_videos_move_success(youtube_api):
    """Test successful video move."""
    youtube_api.get_playlist_videos.return_value = [{"video_id": "vid1", "title": "Video 1"}]
    youtube_api.batch_move_videos_to_playlist.return_value = ["vid1"]
    with patch("src.youtubesorter.common.classify_video_titles") as mock_classify:
        mock_classify.return_value = [True]
        result = common.process_videos(youtube_api, "source", "filter", "target")
        assert result == (["vid1"], [], [])
        youtube_api.get_playlist_videos.assert_called_once_with("source")
        youtube_api.batch_move_videos_to_playlist.assert_called_once_with(
            "source", "target", ["vid1"]
        )


def test_process_videos_move_partial_failure(youtube_api):
    """Test partial failure when moving videos."""
    youtube_api.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Video 1"},
        {"video_id": "vid2", "title": "Video 2"},
    ]
    youtube_api.batch_move_videos_to_playlist.return_value = ["vid1"]
    with patch("src.youtubesorter.common.classify_video_titles") as mock_classify:
        mock_classify.return_value = [True, True]
        result = common.process_videos(youtube_api, "source", "filter", "target")
        assert result == (["vid1"], ["vid2"], [])
        youtube_api.get_playlist_videos.assert_called_once_with("source")
        youtube_api.batch_move_videos_to_playlist.assert_called_once_with(
            "source", "target", ["vid1", "vid2"]
        )


def test_process_videos_copy_success(youtube_api):
    """Test successful video copy."""
    youtube_api.get_playlist_videos.return_value = [{"video_id": "vid1", "title": "Video 1"}]
    youtube_api.batch_add_videos_to_playlist.return_value = ["vid1"]
    with patch("src.youtubesorter.common.classify_video_titles") as mock_classify:
        mock_classify.return_value = [True]
        result = common.process_videos(youtube_api, "source", "filter", "target", copy=True)
        assert result == (["vid1"], [], [])
        youtube_api.get_playlist_videos.assert_called_once_with("source")
        youtube_api.batch_add_videos_to_playlist.assert_called_once_with("target", ["vid1"])


def test_process_videos_error(youtube_api):
    """Test error handling during video processing."""
    youtube_api.get_playlist_videos.side_effect = Exception("API Error")
    result = common.process_videos(youtube_api, "source", "filter", "target")
    assert result == ([], [], [])
    youtube_api.get_playlist_videos.assert_called_once_with("source")
    youtube_api.batch_move_videos_to_playlist.assert_not_called()


def test_save_undo_operation():
    """Test saving undo operation state."""
    expected_data = {
        "target_playlist": "target",
        "processed_videos": ["vid1", "vid2"],
        "failed_videos": ["vid3"],
        "skipped_videos": ["vid4"],
        "operation_type": "undo",
    }
    mock_file = mock_open()
    with patch("builtins.open", mock_file):
        common.save_undo_operation(
            "target",
            ["vid1", "vid2"],
            ["vid3"],
            ["vid4"],
            "state.json",
        )

    # Combine all write calls into a single string
    handle = mock_file()
    written_data = "".join(call[0][0] for call in handle.write.call_args_list)
    assert isinstance(written_data, str)
    assert json.loads(written_data) == expected_data


def test_save_operation_state():
    """Test saving operation state."""
    expected_data = {
        "target_playlist": "target",
        "processed_videos": ["vid1", "vid2"],
        "failed_videos": ["vid3"],
        "skipped_videos": ["vid4"],
        "operation_type": "move",
    }
    mock_file = mock_open()
    with patch("builtins.open", mock_file):
        common.save_operation_state(
            "target",
            ["vid1", "vid2"],
            ["vid3"],
            ["vid4"],
            "state.json",
        )

    # Combine all write calls into a single string
    handle = mock_file()
    written_data = "".join(call[0][0] for call in handle.write.call_args_list)
    assert isinstance(written_data, str)
    assert json.loads(written_data) == expected_data


def test_load_operation_state():
    """Test loading operation state."""
    state_data = {
        "target_playlist": "target",
        "processed_videos": ["vid1", "vid2"],
        "failed_videos": ["vid3"],
        "skipped_videos": ["vid4"],
    }
    mock_file = mock_open(read_data=json.dumps(state_data))
    with patch("builtins.open", mock_file):
        state = common.load_operation_state("state.json")
        assert state == state_data


def test_save_operation_state_error():
    """Test error handling when saving operation state."""
    with patch("builtins.open", side_effect=IOError("Permission denied")):
        # Should not raise an exception
        common.save_operation_state(
            "target",
            ["vid1", "vid2"],
            ["vid3"],
            ["vid4"],
            "state.json",
        )


def test_save_undo_operation_error():
    """Test error handling when saving undo operation state."""
    with patch("builtins.open", side_effect=IOError("Permission denied")):
        # Should not raise an exception
        common.save_undo_operation(
            "target",
            ["vid1", "vid2"],
            ["vid3"],
            ["vid4"],
            "state.json",
        )


def test_load_operation_state_error():
    """Test error handling when loading operation state."""
    with patch("builtins.open", side_effect=IOError("File not found")):
        with pytest.raises(IOError):
            common.load_operation_state("state.json")


def test_undo_operation_success(youtube_api, caplog):
    """Test successful undo operation."""
    caplog.set_level("INFO")

    # Mock the state file
    state_data = {
        "target_playlist": "target",
        "source_playlist": "source",
        "processed_videos": ["vid1", "vid2"],
        "failed_videos": ["vid3"],
        "skipped_videos": ["vid4"],
        "operation_type": "move",
    }
    mock_file = mock_open(read_data=json.dumps(state_data))

    with patch("builtins.open", mock_file):
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("src.youtubesorter.common.find_latest_state") as mock_find:
                mock_find.return_value = "state.json"
                with patch("os.remove") as mock_remove:
                    # Execute undo operation
                    common.undo_operation(youtube_api, verbose=True)

                    # Verify API calls
                    youtube_api.batch_move_videos_to_playlist.assert_called_once_with(
                        "target", "source", ["vid1", "vid2"]
                    )

                    # Verify state file was removed
                    mock_remove.assert_called_once_with("state.json")

                    # Verify logging
                    assert "Undoing last operation" in caplog.text
                    assert "Successfully moved: 0 videos" in caplog.text


def test_undo_operation_no_state(youtube_api, caplog):
    """Test undo operation when no state file exists."""
    caplog.set_level("INFO")

    with patch("src.youtubesorter.common.find_latest_state") as mock_find:
        mock_find.return_value = None

        # Execute undo operation
        common.undo_operation(youtube_api)

        # Verify no API calls were made
        youtube_api.batch_move_videos_to_playlist.assert_not_called()

        # Verify logging
        assert "No previous operation found" in caplog.text


def test_undo_operation_copy(youtube_api, caplog):
    """Test undo operation for copy operation."""
    caplog.set_level("INFO")

    # Mock the state file
    state_data = {
        "target_playlist": "target",
        "processed_videos": ["vid1", "vid2"],
        "operation_type": "copy",
    }
    mock_file = mock_open(read_data=json.dumps(state_data))

    with patch("builtins.open", mock_file):
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("src.youtubesorter.common.find_latest_state") as mock_find:
                mock_find.return_value = "state.json"
                with patch("os.remove") as mock_remove:
                    # Execute undo operation
                    common.undo_operation(youtube_api, verbose=True)

                    # Verify API calls
                    youtube_api.batch_remove_videos_from_playlist.assert_called_once_with(
                        "target", ["vid1", "vid2"]
                    )

                    # Verify state file was removed
                    mock_remove.assert_called_once_with("state.json")

                    # Verify logging
                    assert "Undoing last operation" in caplog.text
                    assert "Successfully removed: 0 videos" in caplog.text


def test_undo_operation_api_error(youtube_api, caplog):
    """Test undo operation when API call fails."""
    caplog.set_level("INFO")

    # Mock the state file
    state_data = {
        "target_playlist": "target",
        "source_playlist": "source",
        "processed_videos": ["vid1", "vid2"],
        "operation_type": "move",
    }
    mock_file = mock_open(read_data=json.dumps(state_data))

    # Mock API error
    youtube_api.batch_move_videos_to_playlist.side_effect = Exception("API Error")

    with patch("builtins.open", mock_file):
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("src.youtubesorter.common.find_latest_state") as mock_find:
                mock_find.return_value = "state.json"

                # Execute undo operation
                common.undo_operation(youtube_api)

                # Verify API call was attempted
                youtube_api.batch_move_videos_to_playlist.assert_called_once_with(
                    "target", "source", ["vid1", "vid2"]
                )

                # Verify error was logged
                assert "Failed to undo operation: API Error" in caplog.text


def test_find_latest_state_with_empty_playlist_id():
    """Test finding latest state file with empty playlist ID."""
    with patch("src.youtubesorter.common.glob") as mock_glob:
        mock_glob.return_value = [
            ".youtubesorter_1.json",
            ".youtubesorter_2.json",
        ]
        with patch("os.path.getctime") as mock_getctime:
            mock_getctime.side_effect = lambda x: 2 if x.endswith("2.json") else 1
            assert common.find_latest_state(None) == ".youtubesorter_2.json"


def test_find_latest_state_with_getctime_error():
    """Test finding latest state file when getctime raises an error."""
    with patch("src.youtubesorter.common.glob") as mock_glob:
        mock_glob.return_value = [
            ".youtubesorter_1.json",
            ".youtubesorter_2.json",
        ]
        with patch("os.path.getctime", side_effect=OSError("Access denied")):
            assert common.find_latest_state("playlist1") is None


def test_process_videos_with_empty_filter():
    """Test processing videos with empty filter prompt."""
    youtube_api = MagicMock()
    youtube_api.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Video 1"},
        {"video_id": "vid2", "title": "Video 2"},
    ]
    youtube_api.batch_move_videos_to_playlist.return_value = ["vid1", "vid2"]

    result = common.process_videos(youtube_api, "source", "", "target")
    assert result == (["vid1", "vid2"], [], [])
    youtube_api.get_playlist_videos.assert_called_once_with("source")
    youtube_api.batch_move_videos_to_playlist.assert_called_once_with(
        "source", "target", ["vid1", "vid2"]
    )


def test_process_videos_copy_failure():
    """Test handling copy operation failure."""
    youtube_api = MagicMock()
    youtube_api.get_playlist_videos.return_value = [
        {"video_id": "vid1", "title": "Video 1"},
        {"video_id": "vid2", "title": "Video 2"},
    ]
    youtube_api.batch_add_videos_to_playlist.return_value = ["vid1"]  # vid2 fails

    result = common.process_videos(youtube_api, "source", "", "target", copy=True)
    assert result == (["vid1"], ["vid2"], [])
    youtube_api.get_playlist_videos.assert_called_once_with("source")
    youtube_api.batch_add_videos_to_playlist.assert_called_once_with("target", ["vid1", "vid2"])


def test_log_operation_summary_no_videos(caplog):
    """Test logging operation summary with no videos."""
    caplog.set_level("INFO")
    common.log_operation_summary(
        "move",
        "playlist1",
        [],
        [],
        [],
        verbose=True,
    )

    assert "Operation Summary for move" in caplog.text
    assert "Target Playlist: playlist1" in caplog.text
    assert "Total Processed: 0" in caplog.text
    assert "Successfully Moved: 0" in caplog.text
    assert "Failed: 0" in caplog.text
    assert "Skipped: 0" in caplog.text


def test_log_operation_summary_not_verbose(caplog):
    """Test logging operation summary without verbose mode."""
    caplog.set_level("INFO")
    common.log_operation_summary(
        "move",
        "playlist1",
        ["vid1", "vid2"],
        ["vid3"],
        ["vid4"],
        verbose=False,
    )

    assert "Operation Summary for move" in caplog.text
    assert "Target Playlist: playlist1" in caplog.text
    assert "Total Processed: 2" in caplog.text
    assert "Successfully Moved: 2" in caplog.text
    assert "Failed: 1" in caplog.text
    assert "Skipped: 1" in caplog.text
    assert "vid1" not in caplog.text
    assert "vid2" not in caplog.text
    assert "vid3" not in caplog.text
    assert "vid4" not in caplog.text


if __name__ == "__main__":
    unittest.main()
