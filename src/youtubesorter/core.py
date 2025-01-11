"""Core functionality and shared utilities."""

from typing import Any, Dict, List

from .logging_config import get_logger
from .errors import PlaylistNotFoundError


# Get logger for this module
logger = get_logger(__name__)


class YouTubeBase:
    """Base class for YouTube operations."""

    def __init__(self, youtube: Any):
        """Initialize with YouTube API client.

        Args:
            youtube: Authenticated YouTube API client
        """
        self.youtube = youtube
        self._logger = logger

    def get_playlist_info(self, playlist_id: str) -> Dict:
        """Get basic playlist information.

        Args:
            playlist_id: YouTube playlist ID

        Returns:
            Dict with playlist info

        Raises:
            PlaylistNotFoundError: If playlist does not exist
        """
        try:
            request = self.youtube.playlists().list(
                part="snippet",
                id=playlist_id,
                maxResults=1,
            )
            response = request.execute()

            if not response.get("items"):
                raise PlaylistNotFoundError(f"Playlist {playlist_id} not found")

            playlist = response["items"][0]
            return {
                "id": playlist["id"],
                "title": playlist["snippet"]["title"],
                "description": playlist["snippet"].get("description", ""),
            }

        except Exception as e:
            self._logger.error("Error getting playlist info: %s", str(e))
            raise

    def get_playlist_videos(self, playlist_id: str) -> List[Dict]:
        """Get all videos in a playlist.

        Args:
            playlist_id: YouTube playlist ID

        Returns:
            List of video information dictionaries
        """
        videos = []
        next_page_token = None

        try:
            while True:
                request = self.youtube.playlistItems().list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token,
                )
                response = request.execute()

                for item in response.get("items", []):
                    video_id = item["snippet"]["resourceId"]["videoId"]
                    title = item["snippet"]["title"]
                    description = item["snippet"].get("description", "")

                    videos.append(
                        {
                            "video_id": video_id,
                            "title": title,
                            "description": description,
                        }
                    )

                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break

            return videos

        except Exception as e:
            self._logger.error("Error getting playlist videos: %s", str(e))
            return []
