"""Utility functions for YouTube playlist operations."""

import glob
import os
import re
from typing import Optional
from .logging_config import get_logger

logger = get_logger(__name__)


def parse_playlist_url(playlist_str: str) -> str:
    """Extract playlist ID from a YouTube playlist URL or return the raw ID.

    Args:
        playlist_str: A YouTube playlist URL or ID

    Returns:
        The playlist ID

    Raises:
        ValueError if the input is not a valid playlist URL or ID
    """
    # Try to extract playlist ID from URL
    url_match = re.search(r"[?&]list=([^&]+)", playlist_str)
    if url_match:
        return url_match.group(1)

    # If not a URL, validate as a raw playlist ID
    if re.match(r"^[A-Za-z0-9_-]+$", playlist_str):
        return playlist_str

    raise ValueError(
        f"Invalid playlist format: {playlist_str}. " "Must be a YouTube playlist URL or ID"
    )


def find_latest_state(playlist_id: Optional[str] = None) -> Optional[str]:
    """Find the latest recovery state file.

    Args:
        playlist_id: Optional playlist ID to filter by

    Returns:
        Path to latest state file if found, None otherwise
    """
    pattern = ".youtubesorter_*_recovery.json"
    if playlist_id:
        pattern = f".youtubesorter_{playlist_id}_recovery.json"

    try:
        files = glob.glob(pattern)
        if not files:
            return None

        # Sort by modification time, newest first
        return max(files, key=os.path.getmtime)
    except Exception as e:
        logger.error("Error finding latest state file: %s", str(e))
        return None
