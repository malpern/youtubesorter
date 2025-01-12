"""Tests for consolidate functionality."""

import os
import tempfile
from typing import Generator
import pytest
from unittest.mock import MagicMock, patch, call

from src.youtubesorter import consolidate
from src.youtubesorter.errors import PlaylistNotFoundError, YouTubeError


@pytest.fixture
def mock_youtube() -> MagicMock:
    """Create mock YouTube API with common responses.
    
    Returns:
        MagicMock: Configured mock YouTube API
    """
    mock = MagicMock()
    
    # Configure default video list response
    mock.get_playlist_videos.return_value = [
        {
            "video_id": "video1",
            "title": "Video 1",
            "description": "Description 1"
        },
        {
            "video_id": "video2",
            "title": "Video 2",
            "description": "Description 2"
        }
    ]
    
    # Configure default move/add responses
    mock.batch_move_videos_to_playlist.return_value = ["video1", "video2"]
    mock.batch_add_videos_to_playlist.return_value = ["video1", "video2"]
    
    # Configure playlist info response
    mock.get_playlist_info.return_value = {
        "title": "Test Playlist",
        "description": "Test Description"
    }
    
    return mock


@pytest.fixture
def temp_state_dir() -> Generator[str, None, None]:
    """Create temporary directory for state files.
    
    Yields:
        str: Path to temporary directory
    """
    test_dir = tempfile.mkdtemp()
    state_dir = os.path.join(test_dir, "data/state")
    os.makedirs(state_dir, exist_ok=True)
    
    yield test_dir
    
    # Cleanup
    try:
        for root, dirs, files in os.walk(test_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(test_dir)
    except OSError:
        pass


def test_process_playlist_move_success(mock_youtube: MagicMock):
    """Test successful video move operation."""
    processed, failed, skipped = consolidate.process_playlist(
        mock_youtube, "source1", "target1", copy=False, verbose=True
    )
    
    assert processed == ["video1", "video2"]
    assert failed == []
    assert skipped == []
    
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        playlist_id="target1",
        video_ids=["video1", "video2"],
        source_playlist_id="source1",
        remove_from_source=True
    )


def test_process_playlist_copy_success(mock_youtube: MagicMock):
    """Test successful video copy operation."""
    processed, failed, skipped = consolidate.process_playlist(
        mock_youtube, "source1", "target1", copy=True, verbose=True
    )
    
    assert processed == ["video1", "video2"]
    assert failed == []
    assert skipped == []
    
    mock_youtube.batch_add_videos_to_playlist.assert_called_once_with(
        playlist_id="target1",
        video_ids=["video1", "video2"]
    )


def test_process_playlist_with_limit(mock_youtube: MagicMock):
    """Test processing playlist with video limit."""
    # Mock to only process first video
    mock_youtube.batch_move_videos_to_playlist.return_value = ["video1"]
    
    processed, failed, skipped = consolidate.process_playlist(
        mock_youtube, "source1", "target1", limit=1
    )
    
    assert processed == ["video1"]
    assert failed == []
    assert skipped == []
    
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        playlist_id="target1",
        video_ids=["video1"],
        source_playlist_id="source1",
        remove_from_source=True
    )


def test_process_playlist_with_processed_videos(mock_youtube: MagicMock):
    """Test processing playlist with already processed videos."""
    processed_videos = {"video1"}
    mock_youtube.batch_move_videos_to_playlist.return_value = ["video2"]
    
    processed, failed, skipped = consolidate.process_playlist(
        mock_youtube, "source1", "target1", processed_videos=processed_videos
    )
    
    assert processed == ["video2"]
    assert failed == []
    assert skipped == ["video1"]
    
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        playlist_id="target1",
        video_ids=["video2"],
        source_playlist_id="source1",
        remove_from_source=True
    )


def test_process_playlist_partial_failure(mock_youtube: MagicMock):
    """Test processing playlist with partial failure."""
    # Mock to only process first video
    mock_youtube.batch_move_videos_to_playlist.return_value = ["video1"]
    
    processed, failed, skipped = consolidate.process_playlist(
        mock_youtube, "source1", "target1"
    )
    
    assert processed == ["video1"]
    assert failed == ["video2"]
    assert skipped == []
    
    mock_youtube.batch_move_videos_to_playlist.assert_called_once_with(
        playlist_id="target1",
        video_ids=["video1", "video2"],
        source_playlist_id="source1",
        remove_from_source=True
    )


def test_process_playlist_api_error(mock_youtube: MagicMock):
    """Test handling API error during processing."""
    mock_youtube.get_playlist_videos.side_effect = YouTubeError("Failed to get playlist videos")
    
    with pytest.raises(YouTubeError) as exc_info:
        consolidate.process_playlist(mock_youtube, "source1", "target1")
    
    assert str(exc_info.value) == "Failed to get playlist videos"
    mock_youtube.get_playlist_videos.assert_called_once_with("source1")
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


def test_process_playlist_playlist_not_found(mock_youtube: MagicMock):
    """Test handling playlist not found error."""
    mock_youtube.get_playlist_videos.side_effect = PlaylistNotFoundError("Playlist not found")
    
    with pytest.raises(PlaylistNotFoundError) as exc_info:
        consolidate.process_playlist(mock_youtube, "source1", "target1")
    
    assert str(exc_info.value) == "Playlist not found"
    mock_youtube.get_playlist_videos.assert_called_once_with("source1")
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


def test_process_playlist_empty(mock_youtube: MagicMock):
    """Test processing empty playlist."""
    mock_youtube.get_playlist_videos.return_value = []
    
    processed, failed, skipped = consolidate.process_playlist(
        mock_youtube, "source1", "target1"
    )
    
    assert processed == []
    assert failed == []
    assert skipped == []
    
    mock_youtube.get_playlist_videos.assert_called_once_with("source1")
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


def test_consolidate_playlists_copy(mock_youtube: MagicMock):
    """Test consolidating playlists in copy mode."""
    with patch("src.youtubesorter.consolidate.process_playlist") as mock_process:
        processed_videos = set()

        def process_side_effect(*args, **kwargs):
            nonlocal processed_videos
            result = (["video1", "video2"], [], [])
            processed_videos.update(result[0])
            return result

        mock_process.side_effect = process_side_effect

        processed, failed, skipped = consolidate.consolidate_playlists(
            mock_youtube, ["source1", "source2"], "target1", copy=True
        )

        assert processed == ["video1", "video2", "video1", "video2"]
        assert failed == []
        assert skipped == []

        # Verify process_playlist was called for each source
        assert mock_process.call_count == 2
        mock_process.assert_has_calls([
            call(
                mock_youtube,
                "source1",
                "target1",
                copy=True,
                verbose=False,
                limit=None,
                processed_videos=set(),
                failed_videos=set()
            ),
            call(
                mock_youtube,
                "source2",
                "target1",
                copy=True,
                verbose=False,
                limit=None,
                processed_videos={"video1", "video2"},
                failed_videos=set()
            )
        ])


def test_consolidate_playlists_resume(mock_youtube: MagicMock):
    """Test resuming consolidation from previous state."""
    with patch("src.youtubesorter.consolidate.process_playlist") as mock_process:
        def process_side_effect(*args, **kwargs):
            return (["video2"], [], [])

        mock_process.side_effect = process_side_effect

        processed, failed, skipped = consolidate.consolidate_playlists(
            mock_youtube, ["source1", "source2"], "target1",
            resume=True
        )

        assert processed == ["video2", "video2"]
        assert failed == []
        assert skipped == []

        # Verify process_playlist was called for each source
        assert mock_process.call_count == 2
        mock_process.assert_has_calls([
            call(
                mock_youtube,
                "source1",
                "target1",
                copy=False,
                verbose=False,
                limit=None,
                processed_videos=set(),
                failed_videos=set()
            ),
            call(
                mock_youtube,
                "source2",
                "target1",
                copy=False,
                verbose=False,
                limit=None,
                processed_videos={"video2"},
                failed_videos=set()
            )
        ])


def test_consolidate_playlists_retry_failed(mock_youtube: MagicMock):
    """Test retrying failed videos during consolidation."""
    with patch("src.youtubesorter.consolidate.process_playlist") as mock_process:
        def process_side_effect(*args, **kwargs):
            return (["video2"], [], [])

        mock_process.side_effect = process_side_effect

        processed, failed, skipped = consolidate.consolidate_playlists(
            mock_youtube, ["source1", "source2"], "target1",
            retry_failed=True
        )

        assert processed == ["video2", "video2"]
        assert failed == []
        assert skipped == []

        # Verify process_playlist was called for each source
        assert mock_process.call_count == 2
        mock_process.assert_has_calls([
            call(
                mock_youtube,
                "source1",
                "target1",
                copy=False,
                verbose=False,
                limit=None,
                processed_videos=set(),
                failed_videos=set()
            ),
            call(
                mock_youtube,
                "source2",
                "target1",
                copy=False,
                verbose=False,
                limit=None,
                processed_videos={"video2"},
                failed_videos=set()
            )
        ])


def test_consolidate_playlists_with_limit(mock_youtube: MagicMock):
    """Test consolidating playlists with video limit."""
    with patch("src.youtubesorter.consolidate.process_playlist") as mock_process:
        def process_side_effect(*args, **kwargs):
            return (["video1"], [], [])

        mock_process.side_effect = process_side_effect

        processed, failed, skipped = consolidate.consolidate_playlists(
            mock_youtube, ["source1", "source2"], "target1", limit=1
        )

        assert processed == ["video1", "video1"]
        assert failed == []
        assert skipped == []

        # Verify process_playlist was called for each source with limit
        assert mock_process.call_count == 2
        mock_process.assert_has_calls([
            call(
                mock_youtube,
                "source1",
                "target1",
                copy=False,
                verbose=False,
                limit=1,
                processed_videos=set(),
                failed_videos=set()
            ),
            call(
                mock_youtube,
                "source2",
                "target1",
                copy=False,
                verbose=False,
                limit=1,
                processed_videos={"video1"},
                failed_videos=set()
            )
        ])


def test_consolidate_playlists_target_not_found(mock_youtube: MagicMock):
    """Test error handling when target playlist is not found."""
    mock_youtube.get_playlist_info.side_effect = PlaylistNotFoundError("Target playlist not found")
    
    with pytest.raises(YouTubeError) as exc_info:
        consolidate.consolidate_playlists(
            mock_youtube, ["source1"], "target1"
        )
    
    assert str(exc_info.value) == "Target playlist not found: target1"
    mock_youtube.get_playlist_info.assert_called_once_with("target1")
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


def test_consolidate_playlists_source_not_found(mock_youtube: MagicMock):
    """Test handling source playlist not found error."""
    mock_youtube.get_playlist_videos.side_effect = PlaylistNotFoundError("Source playlist not found")
    
    processed, failed, skipped = consolidate.consolidate_playlists(
        mock_youtube, ["source1", "source2"], "target1"
    )
    
    assert processed == []
    assert failed == []
    assert skipped == []
    
    mock_youtube.get_playlist_info.assert_called_once_with("target1")
    mock_youtube.get_playlist_videos.assert_has_calls([
        call("source1"),
        call("source2")
    ])
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()


def test_consolidate_playlists_api_error(mock_youtube: MagicMock):
    """Test handling API errors during consolidation."""
    mock_youtube.get_playlist_videos.side_effect = YouTubeError("API Error")
    
    processed, failed, skipped = consolidate.consolidate_playlists(
        mock_youtube, ["source1", "source2"], "target1"
    )
    
    assert processed == []
    assert failed == []
    assert skipped == []
    
    mock_youtube.get_playlist_info.assert_called_once_with("target1")
    mock_youtube.get_playlist_videos.assert_has_calls([
        call("source1"),
        call("source2")
    ])
    mock_youtube.batch_move_videos_to_playlist.assert_not_called()
