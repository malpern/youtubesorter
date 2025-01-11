"""Utility to clear all videos from a YouTube playlist."""

import argparse
from typing import Optional

from googleapiclient.discovery import Resource

from . import auth
from . import api
from .logging import logger


def create_parser() -> argparse.ArgumentParser:
    """Create the command line argument parser."""
    parser = argparse.ArgumentParser(description="Remove all videos from a YouTube playlist.")

    parser.add_argument(
        "playlist_id",
        help=("ID of the playlist to clear " "(from the playlist URL after '?list=')"),
    )

    return parser


def clear_playlist(youtube: Resource, playlist_id: str) -> bool:
    """Remove all videos from a playlist.

    Args:
        youtube: Authenticated YouTube service object
        playlist_id: ID of the playlist to clear

    Returns:
        bool: True if operation was successful, False otherwise
    """
    try:
        # First, get all videos
        logger.info("Fetching videos from playlist...")
        videos = api.get_playlist_videos(youtube, playlist_id)

        if not videos:
            logger.info("No videos found in playlist.")
            return True

        # Show videos that will be removed
        logger.info("\nFound %d videos:", len(videos))
        for i, video in enumerate(videos, 1):
            logger.info("%d. %s", i, video["title"])

        # Ask for confirmation
        logger.warning("\n⚠️  WARNING: This will remove ALL videos from the playlist!")
        confirm = input('\nType "yes" to confirm: ')

        if confirm.lower() != "yes":
            logger.info("Operation cancelled.")
            return False

        # Remove videos in batches
        logger.info("\nRemoving videos...")
        video_ids = [v["video_id"] for v in videos]
        youtube_api = api.YouTubeAPI(youtube)
        removed = youtube_api.batch_remove_videos_from_playlist(playlist_id, video_ids)

        # Report results
        success_count = len(removed)
        failed_count = len(videos) - success_count
        logger.info("\n✅ Successfully removed: %d videos", success_count)
        if failed_count > 0:
            logger.warning("❌ Failed to remove: %d videos", failed_count)

        logger.info("\nPlaylist cleared successfully!")
        return True

    except Exception as e:
        logger.error("Error clearing playlist: %s", str(e))
        return False


def main() -> Optional[bool]:
    """Main entry point.

    Returns:
        Optional[bool]: True if successful, False if failed,
        None if setup failed
    """
    parser = create_parser()
    args = parser.parse_args()

    # Get YouTube service
    youtube = auth.get_youtube_service()
    if not youtube:
        return None

    return clear_playlist(youtube, args.playlist_id)


if __name__ == "__main__":
    main()
