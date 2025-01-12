"""YouTube API base class."""

import logging
from typing import Dict, List, Optional, Set

from .errors import PlaylistNotFoundError, YouTubeError


logger = logging.getLogger(__name__)


class YouTubeBase:
    """Base class for YouTube API operations."""

    def __init__(self, youtube):
        """Initialize API wrapper.

        Args:
            youtube: YouTube API client
        """
        self.youtube = youtube

    def get_playlist_info(self, playlist_id: str) -> Dict[str, str]:
        """Get playlist information.

        Args:
            playlist_id: ID of playlist to get info for

        Returns:
            Dictionary with playlist id, title and description

        Raises:
            PlaylistNotFoundError: If playlist is not found
            YouTubeError: If API request fails
        """
        try:
            request = self.youtube.playlists().list(
                part="snippet",
                id=playlist_id,
                maxResults=1,  # We only need one result
            )
            response = request.execute()

            if not response.get("items"):
                raise PlaylistNotFoundError(f"Playlist {playlist_id} not found")

            playlist = response["items"][0]
            return {
                "id": playlist_id,
                "title": playlist["snippet"]["title"],
                "description": playlist["snippet"].get("description", ""),
            }

        except PlaylistNotFoundError:
            raise
        except Exception as e:
            if "playlistNotFound" in str(e):
                raise PlaylistNotFoundError(f"Playlist {playlist_id} not found")
            raise YouTubeError("Failed to get playlist info")

    def get_playlist_videos(self, playlist_id: str) -> List[Dict[str, str]]:
        """Get all videos in a playlist.

        Args:
            playlist_id: ID of playlist to get videos from

        Returns:
            List of video dictionaries with video_id, title and description

        Raises:
            PlaylistNotFoundError: If playlist is not found
            YouTubeError: If API request fails
        """
        videos = []
        page_token = None

        while True:
            try:
                request = self.youtube.playlistItems().list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=page_token,
                )
                response = request.execute()

                # Extract video info from items
                for item in response.get("items", []):
                    snippet = item["snippet"]
                    videos.append({
                        "video_id": snippet["resourceId"]["videoId"],
                        "title": snippet["title"],
                        "description": snippet.get("description", ""),
                    })

                # Get next page token
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            except Exception as e:
                if "playlistNotFound" in str(e):
                    raise PlaylistNotFoundError(f"Playlist {playlist_id} not found")
                raise YouTubeError("Failed to get playlist videos")

        return videos

    def batch_move_videos_to_playlist(
        self,
        playlist_id: str,
        video_ids: List[str],
        source_playlist_id: Optional[str] = None,
        remove_from_source: bool = True,
    ) -> List[str]:
        """Move multiple videos between playlists.

        Args:
            playlist_id: ID of target playlist
            video_ids: List of video IDs to move
            source_playlist_id: Optional ID of source playlist (for validation)
            remove_from_source: Whether to remove videos from source playlist

        Returns:
            List of successfully moved video IDs

        Raises:
            PlaylistNotFoundError: If either playlist is not found
            YouTubeError: If API request fails
        """
        # First add videos to target playlist
        added = self.batch_add_videos_to_playlist(
            playlist_id=playlist_id,
            video_ids=video_ids
        )

        # If successful and remove_from_source is True, remove from source
        if added and remove_from_source and source_playlist_id:
            removed = self.batch_remove_videos_from_playlist(
                playlist_id=source_playlist_id,
                video_ids=video_ids
            )
            # Only return videos that were both added and removed
            return [vid for vid in added if vid in removed]

        return added

    def batch_add_videos_to_playlist(
        self,
        playlist_id: str,
        video_ids: List[str],
    ) -> List[str]:
        """Add multiple videos to a playlist.

        Args:
            playlist_id: ID of playlist to add to
            video_ids: List of video IDs to add

        Returns:
            List of successfully added video IDs

        Raises:
            PlaylistNotFoundError: If playlist is not found
            YouTubeError: If API request fails
        """
        successful = []

        for video_id in video_ids:
            try:
                request = self.youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": playlist_id,
                            "resourceId": {"kind": "youtube#video", "videoId": video_id},
                        }
                    },
                )
                request.execute()
                successful.append(video_id)
            except Exception as e:
                if "playlistNotFound" in str(e):
                    raise PlaylistNotFoundError(f"Playlist {playlist_id} not found")
                logger.error("Failed to add video %s", video_id)

        return successful

    def batch_remove_videos_from_playlist(
        self,
        playlist_id: str,
        video_ids: List[str],
    ) -> List[str]:
        """Remove multiple videos from a playlist.

        Args:
            playlist_id: ID of playlist to remove from
            video_ids: List of video IDs to remove

        Returns:
            List of successfully removed video IDs

        Raises:
            PlaylistNotFoundError: If playlist is not found
            YouTubeError: If API request fails
        """
        try:
            # Get playlist items to find item IDs
            item_map = {}  # Map video IDs to item IDs
            page_token = None

            while True:
                request = self.youtube.playlistItems().list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=page_token,
                )
                try:
                    response = request.execute()
                except Exception as e:
                    if "playlistNotFound" in str(e):
                        raise PlaylistNotFoundError(f"Playlist {playlist_id} not found")
                    raise YouTubeError("Failed to list playlist items")

                # Map video IDs to item IDs
                for item in response.get("items", []):
                    video_id = item["snippet"]["resourceId"]["videoId"]
                    if video_id in video_ids:
                        item_map[video_id] = item["id"]

                # Get next page token
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            # Remove videos using item IDs
            successful = []
            for video_id in video_ids:
                if video_id in item_map:
                    try:
                        request = self.youtube.playlistItems().delete(id=item_map[video_id])
                        request.execute()
                        successful.append(video_id)
                    except Exception as e:
                        logger.error("Failed to remove video %s", video_id)

            return successful

        except PlaylistNotFoundError:
            raise
        except Exception as e:
            raise YouTubeError("Failed to remove playlist items")
