"""Clean up recovery files, keeping latest for each source playlist."""

import os
import json
from collections import defaultdict
import time

from src.youtubesorter.config import RECOVERY_DIR, STATE_DIR, CACHE_DIR
from src.youtubesorter.logging_config import get_logger

logger = get_logger(__name__)


def cleanup_recovery_files(directory: str = RECOVERY_DIR) -> None:
    """Clean up recovery files, keeping latest for each source playlist.

    Args:
        directory: Directory containing recovery files
    """
    if not os.path.exists(directory):
        logger.info("Recovery directory not found: %s", directory)
        return

    # Group files by source playlist ID
    playlist_files = defaultdict(list)

    # Find all recovery files
    for filename in os.listdir(directory):
        if filename.startswith("recovery_") and filename.endswith(".json"):
            try:
                # Read the file to get source playlist ID
                with open(os.path.join(directory, filename), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    source_id = data["playlist_id"]
                    playlist_files[source_id].append(filename)
            except (json.JSONDecodeError, KeyError, IOError) as e:
                logger.warning("Skipping invalid file %s: %s", filename, str(e))
                continue

    # For each playlist, keep only the latest file
    files_to_delete = []
    for source_id, filenames in playlist_files.items():
        # Sort files by timestamp (which is part of the filename)
        sorted_files = sorted(filenames, key=lambda x: x.split("_")[-1].split(".")[0])
        # Keep the latest, mark others for deletion
        files_to_delete.extend(sorted_files[:-1])

    # Delete old files
    for filename in files_to_delete:
        try:
            os.remove(os.path.join(directory, filename))
            logger.info("Deleted old recovery file: %s", filename)
        except OSError as e:
            logger.error("Error deleting file %s: %s", filename, str(e))


def cleanup_state_files(directory: str = STATE_DIR) -> None:
    """Clean up state files, keeping latest for each operation type.

    Args:
        directory: Directory containing state files
    """
    if not os.path.exists(directory):
        logger.info("State directory not found: %s", directory)
        return

    # Group files by operation type
    operation_files = defaultdict(list)

    # Find all state files
    for filename in os.listdir(directory):
        if filename.startswith("youtubesorter_") and filename.endswith(".json"):
            try:
                operation_type = filename.split("_")[1]  # Get operation type from filename
                operation_files[operation_type].append(filename)
            except IndexError:
                logger.warning("Skipping invalid filename: %s", filename)
                continue

    # For each operation type, keep only the latest file
    files_to_delete = []
    for operation_type, filenames in operation_files.items():
        # Sort files by timestamp
        sorted_files = sorted(filenames, key=lambda x: x.split("_")[-1].split(".")[0])
        # Keep the latest, mark others for deletion
        files_to_delete.extend(sorted_files[:-1])

    # Delete old files
    for filename in files_to_delete:
        try:
            os.remove(os.path.join(directory, filename))
            logger.info("Deleted old state file: %s", filename)
        except OSError as e:
            logger.error("Error deleting file %s: %s", filename, str(e))


def cleanup_cache_files(directory: str = CACHE_DIR) -> None:
    """Clean up cache files older than 7 days.

    Args:
        directory: Directory containing cache files
    """
    if not os.path.exists(directory):
        logger.info("Cache directory not found: %s", directory)
        return

    # Find all cache files
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            filepath = os.path.join(directory, filename)
            try:
                # Check file age
                age = os.path.getmtime(filepath)
                if (time.time() - age) > (7 * 24 * 60 * 60):  # 7 days
                    os.remove(filepath)
                    logger.info("Deleted old cache file: %s", filename)
            except OSError as e:
                logger.error("Error processing file %s: %s", filename, str(e))


if __name__ == "__main__":
    cleanup_recovery_files()
    cleanup_state_files()
    cleanup_cache_files()
