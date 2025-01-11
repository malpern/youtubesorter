"""YouTube API wrapper."""

import logging
from typing import Dict, List

from .errors import PlaylistNotFoundError, YouTubeError
from .auth import get_youtube_service


logger = logging.getLogger(__name__)


def get_playlist_videos(playlist_id: str, use_cache: bool = True) -> List[Dict[str, str]]:
    """Get all videos in a playlist.

    Args:
        playlist_id: ID of playlist to get videos from
        use_cache: Whether to use cached results

    Returns:
        List of video dictionaries with video_id, title and description

    Raises:
        PlaylistNotFoundError: If playlist is not found
        YouTubeError: If API request fails
    """
    youtube = get_youtube_service()
    if not youtube:
        raise YouTubeError("Failed to get YouTube service")

    api = YouTubeAPI(youtube)
    return api.get_playlist_videos(playlist_id, use_cache)


def batch_move_videos_to_playlist(
    source_playlist: str,
    target_playlist: str,
    video_ids: List[str],
    remove_from_source: bool = True,
) -> List[str]:
    """Move multiple videos between playlists.

    Args:
        source_playlist: ID of source playlist
        target_playlist: ID of target playlist
        video_ids: List of video IDs to move
        remove_from_source: Whether to remove videos from source playlist

    Returns:
        List of successfully moved video IDs

    Raises:
        PlaylistNotFoundError: If either playlist is not found
        YouTubeError: If API request fails
    """
    youtube = get_youtube_service()
    if not youtube:
        raise YouTubeError("Failed to get YouTube service")

    api = YouTubeAPI(youtube)
    return api.batch_move_videos_to_playlist(
        source_playlist,
        target_playlist,
        video_ids,
        remove_from_source,
    )


def get_playlist_info(playlist_id: str) -> Dict[str, str]:
    """Get playlist information.

    Args:
        playlist_id: ID of playlist to get info for

    Returns:
        Dictionary with playlist title and description

    Raises:
        PlaylistNotFoundError: If playlist is not found
        YouTubeError: If API request fails
    """
    youtube = get_youtube_service()
    if not youtube:
        raise YouTubeError("Failed to get YouTube service")

    api = YouTubeAPI(youtube)
    return api.get_playlist_info(playlist_id)


class YouTubeAPI:
    """Wrapper for YouTube API operations."""

    def __init__(self, youtube):
        """Initialize API wrapper.

        Args:
            youtube: YouTube API client
        """
        self.youtube = youtube

    def get_playlist_videos(self, playlist_id: str, use_cache: bool = True) -> List[Dict[str, str]]:
        """Get all videos in a playlist.

        Args:
            playlist_id: ID of playlist to get videos from
            use_cache: Whether to use cached results

        Returns:
            List of video dictionaries with video_id, title and description

        Raises:
            PlaylistNotFoundError: If playlist is not found
            YouTubeError: If API request fails
        """
        try:
            videos = []
            page_token = None

            while True:
                # Get playlist items
                request = self.youtube.playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=page_token,
                )

                try:
                    response = request.execute()
                except Exception as e:
                    if "playlistNotFound" in str(e):
                        raise PlaylistNotFoundError(f"Playlist {playlist_id} not found") from e
                    raise YouTubeError(f"Failed to get playlist videos: {str(e)}") from e

                # Extract video info
                for item in response.get("items", []):
                    video = {
                        "video_id": item["contentDetails"]["videoId"],
                        "title": item["snippet"]["title"],
                        "description": item["snippet"]["description"],
                    }
                    videos.append(video)

                # Get next page token
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            return videos

        except PlaylistNotFoundError:
            raise
        except Exception as e:
            raise YouTubeError(f"Failed to get playlist videos: {str(e)}") from e

    def batch_move_videos_to_playlist(
        self,
        source_playlist: str,
        target_playlist: str,
        video_ids: List[str],
        remove_from_source: bool = True,
    ) -> List[str]:
        """Move multiple videos between playlists.

        Args:
            source_playlist: ID of source playlist
            target_playlist: ID of target playlist
            video_ids: List of video IDs to move
            remove_from_source: Whether to remove videos from source playlist

        Returns:
            List of successfully moved video IDs

        Raises:
            PlaylistNotFoundError: If either playlist is not found
            YouTubeError: If API request fails
        """
        # First add videos to target playlist
        added = self.batch_add_videos_to_playlist(target_playlist, video_ids)

        # If successful and remove_from_source is True, remove from source
        if added and remove_from_source:
            removed = self.batch_remove_videos_from_playlist(source_playlist, video_ids)
            # Only return videos that were both added and removed
            return [vid for vid in added if vid in removed]

        return added

    def batch_add_videos_to_playlist(self, playlist_id: str, video_ids: List[str]) -> List[str]:
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
                    raise PlaylistNotFoundError(f"Playlist {playlist_id} not found") from e
                logger.error(f"Failed to add video {video_id}: {str(e)}")

        return successful

    def batch_remove_videos_from_playlist(
        self, playlist_id: str, video_ids: List[str]
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
                    part="id,contentDetails",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=page_token,
                )
                try:
                    response = request.execute()
                except Exception as e:
                    if "playlistNotFound" in str(e):
                        raise PlaylistNotFoundError(f"Playlist {playlist_id} not found") from e
                    raise YouTubeError(f"Failed to list playlist items: {str(e)}") from e

                # Map video IDs to item IDs
                for item in response.get("items", []):
                    video_id = item["contentDetails"]["videoId"]
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
                        logger.error(f"Failed to remove video {video_id}: {str(e)}")

            return successful

        except PlaylistNotFoundError:
            raise
        except Exception as e:
            raise YouTubeError(f"Failed to remove playlist items: {str(e)}") from e

    def get_playlist_info(self, playlist_id: str) -> Dict[str, str]:
        """Get playlist information.

        Args:
            playlist_id: ID of playlist to get info for

        Returns:
            Dictionary with playlist title and description

        Raises:
            PlaylistNotFoundError: If playlist is not found
            YouTubeError: If API request fails
        """
        try:
            request = self.youtube.playlists().list(
                part="snippet",
                id=playlist_id,
            )
            response = request.execute()

            if not response.get("items"):
                raise PlaylistNotFoundError(f"Playlist {playlist_id} not found")

            playlist = response["items"][0]
            return {
                "title": playlist["snippet"]["title"],
                "description": playlist["snippet"]["description"],
            }

        except Exception as e:
            if "playlistNotFound" in str(e) or not response.get("items"):
                raise PlaylistNotFoundError(f"Playlist {playlist_id} not found")
            raise YouTubeError(f"Failed to get playlist info: {str(e)}")
