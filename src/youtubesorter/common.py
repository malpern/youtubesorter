"""Common utilities for YouTube playlist operations."""

import argparse
import json
import logging
import os
from glob import glob
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

from . import api
from . import classifier
from .config import STATE_DIR
from .logging_config import get_logger

logger = get_logger(__name__)

# Default state file path
STATE_FILE = os.path.join(STATE_DIR, "youtubesorter_state.json")


def classify_video_titles(videos: List[Dict[str, Any]], filter_prompt: str) -> List[bool]:
    """Classify videos based on titles.

    Args:
        videos: List of video dictionaries with titles
        filter_prompt: Filter prompt for video matching

    Returns:
        List of booleans indicating whether each video matches
    """
    return classifier.classify_video_titles(videos, filter_prompt)


def find_latest_state(playlist_id: str) -> Optional[str]:
    """Find the latest state file for a playlist.

    Args:
        playlist_id: Playlist ID to find state for

    Returns:
        Path to latest state file if found, None otherwise
    """
    pattern = (
        os.path.join(STATE_DIR, f"youtubesorter_{playlist_id}*.json")
        if playlist_id
        else os.path.join(STATE_DIR, "youtubesorter_*.json")
    )
    files = glob(pattern)
    if not files:
        return None

    try:
        return max(files, key=os.path.getctime)
    except OSError:
        logger.error("Failed to access state files")
        return None


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to parser.

    Args:
        parser: Argument parser to add arguments to
    """
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "-d", "--dry-run", action="store_true", help="Simulate operations without making changes"
    )
    parser.add_argument("-r", "--resume", help="Resume from a specific destination playlist")


def add_undo_command(subparsers: argparse._SubParsersAction) -> None:
    """Add undo command to subparsers.

    Args:
        subparsers: Subparser group to add command to
    """
    undo_parser = subparsers.add_parser("undo", help="Undo the last operation")
    undo_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")


def log_operation_summary(
    operation_type: str,
    target_playlist: str,
    processed: List[str],
    failed: List[str],
    skipped: List[str],
    verbose: bool = False,
) -> None:
    """Log summary of operation results.

    Args:
        operation_type: Type of operation performed
        target_playlist: Target playlist ID
        processed: List of successfully processed video IDs
        failed: List of failed video IDs
        skipped: List of skipped video IDs
        verbose: Whether to include detailed video lists
    """
    logger.info(
        f"\nOperation Summary for {operation_type}:\n"
        f"Target Playlist: {target_playlist}\n"
        f"Total Processed: {len(processed)}\n"
        f"Successfully Moved: {len(processed)}\n"
        f"Failed: {len(failed)}\n"
        f"Skipped: {len(skipped)}"
    )

    if verbose:
        if processed:
            logger.info("\nSuccessfully moved videos:")
            for video_id in processed:
                logger.info(f"- {video_id}")

        if failed:
            logger.info("\nFailed videos:")
            for video_id in failed:
                logger.info(f"- {video_id}")

        if skipped:
            logger.info("\nSkipped videos:")
            for video_id in skipped:
                logger.info(f"- {video_id}")


def process_videos(
    youtube: api.YouTubeAPI,
    source_playlist: str,
    filter_prompt: str,
    target_playlist: str,
    copy: bool = False,
    verbose: bool = False,
    dry_run: bool = False,
) -> Tuple[List[str], List[str], List[str]]:
    """Process videos from source playlist according to filter criteria.

    Args:
        youtube: YouTube API client
        source_playlist: Source playlist ID
        filter_prompt: Filter prompt for video classification
        target_playlist: Target playlist ID
        copy: Whether to copy instead of move videos
        verbose: Whether to enable verbose output
        dry_run: Whether to simulate operations

    Returns:
        Tuple of (processed, failed, skipped) video IDs
    """
    video_ids = []  # Initialize video_ids before try block
    try:
        # Get source videos
        videos = youtube.get_playlist_videos(source_playlist)
        if not videos:
            logger.info("No videos found in source playlist")
            return [], [], []

        # Filter videos if prompt provided
        if filter_prompt:
            matches = classify_video_titles(videos, filter_prompt)
            videos = [v for v, m in zip(videos, matches) if m]

        if not videos:
            logger.info("No videos matched filter criteria")
            return [], [], []

        # Get video IDs
        video_ids = [v["video_id"] for v in videos]

        # Process videos
        if dry_run:
            logger.info("Dry run - no changes will be made")
            return video_ids, [], []

        # Move or copy videos
        if copy:
            processed = youtube.batch_add_videos_to_playlist(target_playlist, video_ids)
            failed = [v for v in video_ids if v not in processed]
            return processed, failed, []
        else:
            processed = youtube.batch_move_videos_to_playlist(
                playlist_id=target_playlist,
                video_ids=video_ids,
                source_playlist_id=source_playlist,
                remove_from_source=True
            )
            failed = [v for v in video_ids if v not in processed]
            return processed, failed, []

    except Exception as e:
        logger.error(f"Error processing playlist {source_playlist}: {str(e)}")
        return [], video_ids, []


def save_operation_state(
    playlist_id: str,
    processed_videos: List[str],
    failed_videos: List[str],
    skipped_videos: List[str],
    state_file: Optional[str] = None,
) -> None:
    """Save operation state to file.

    Args:
        playlist_id: ID of playlist being processed
        processed_videos: List of processed video IDs
        failed_videos: List of failed video IDs
        skipped_videos: List of skipped video IDs
        state_file: Optional path to state file
    """
    try:
        if not state_file:
            state_file = os.path.join(STATE_DIR, f"{playlist_id}_state.json")

        state = {
            "playlist_id": playlist_id,
            "processed_videos": processed_videos,
            "failed_videos": failed_videos,
            "skipped_videos": skipped_videos,
        }

        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    except Exception as e:
        logger.error("Failed to save operation state: %s", str(e))


def save_undo_operation(
    target_playlist: str,
    processed: List[str],
    failed: List[str],
    skipped: List[str],
    state_file: Optional[str] = None,
) -> None:
    """Save undo operation state.

    Args:
        target_playlist: Target playlist ID
        processed: List of processed video IDs
        failed: List of failed video IDs
        skipped: List of skipped video IDs
        state_file: Path to state file. If None, uses default in state directory.
    """
    try:
        if state_file is None:
            os.makedirs(STATE_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            state_file = os.path.join(STATE_DIR, f"youtubesorter_undo_{target_playlist}_{timestamp}.json")

        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "target_playlist": target_playlist,
                    "processed_videos": processed,
                    "failed_videos": failed,
                    "skipped_videos": skipped,
                    "operation_type": "undo",
                },
                f,
                indent=2,
            )
    except IOError:
        logger.error("Failed to save undo operation state")


def load_operation_state(state_file: str) -> Optional[Dict[str, Any]]:
    """Load operation state.

    Args:
        state_file: Path to state file

    Returns:
        Operation state dictionary or None if file doesn't exist
    """
    try:
        if not os.path.exists(state_file):
            return None
            
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load operation state: %s", str(e))
        return None


def undo_operation(youtube, verbose=False):
    """Undo the last operation."""
    state_file = find_latest_state(None)
    if not state_file:
        logger.info("No previous operation found")
        return

    try:
        state = load_operation_state(state_file)
        target_playlist = state.get("target_playlist")
        processed_videos = state.get("processed_videos", [])
        operation_type = state.get("operation_type", "move")

        if not processed_videos:
            logger.info("No videos to undo")
            return

        logger.info("Undoing last operation")
        if verbose:
            logger.info("Videos to move back: %s", processed_videos)

        if operation_type == "move":
            # For move operations, move videos back to source playlist
            source_playlist = state.get("source_playlist")
            if not source_playlist:
                logger.error("Source playlist not found in state file")
                return

            moved_videos = youtube.batch_move_videos_to_playlist(
                target_playlist, source_playlist, processed_videos
            )
            if verbose:
                logger.info("Successfully moved: %d videos", len(moved_videos))

        elif operation_type == "copy":
            # For copy operations, just remove videos from target playlist
            removed_videos = youtube.batch_remove_videos_from_playlist(
                target_playlist, processed_videos
            )
            if verbose:
                logger.info("Successfully removed: %d videos", len(removed_videos))

        # Clear the state file after successful undo
        os.remove(state_file)

    except Exception as e:
        logger.error("Failed to undo operation: %s", str(e))


def clear_operation_state(state_file: Optional[str] = None) -> None:
    """Clear operation state.

    Args:
        state_file: Path to state file. If None, uses default in state directory.
    """
    try:
        if state_file is None:
            # Remove all state files
            pattern = os.path.join(STATE_DIR, "youtubesorter_*.json")
            for f in glob(pattern):
                try:
                    os.remove(f)
                except OSError:
                    logger.error("Failed to remove state file: %s", f)
        else:
            # Remove specific state file
            try:
                os.remove(state_file)
            except OSError:
                logger.error("Failed to remove state file: %s", state_file)
    except Exception as e:
        logger.error("Failed to clear operation state: %s", str(e))
