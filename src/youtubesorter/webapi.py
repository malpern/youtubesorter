"""Web API for YouTube Playlist Organizer."""

import logging
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import auth
from .api import YouTubeAPI
from .core import YouTubeBase
from .errors import PlaylistNotFoundError, YouTubeError

logger = logging.getLogger(__name__)

app = FastAPI()


class ConsolidateRequest(BaseModel):
    """Request model for consolidating playlists."""

    source_playlists: List[str]
    target_playlist: str
    copy: bool = False
    dry_run: bool = False
    verbose: bool = False
    resume: bool = False
    resume_destination: Optional[str] = None
    retry_failed: bool = False
    limit: Optional[int] = None


class DistributeRequest(BaseModel):
    """Request model for distributing videos."""

    source_playlist: str
    target_playlists: List[str]
    filter_prompts: List[str]
    dry_run: bool = False
    verbose: bool = False
    resume: bool = False
    resume_destination: Optional[str] = None
    retry_failed: bool = False
    limit: Optional[int] = None


class DeduplicateRequest(BaseModel):
    """Request model for deduplicating a playlist."""

    playlist_id: str
    verbose: bool = False


class ApiResponse(BaseModel):
    """Response model for API endpoints."""

    success: bool
    processed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    details: Optional[str] = None


def get_youtube_client() -> YouTubeBase:
    """Get an authenticated YouTube client.

    Returns:
        YouTubeBase: Authenticated YouTube client

    Raises:
        HTTPException: If authentication fails
    """
    try:
        youtube = auth.get_youtube_service()
        return YouTubeAPI(youtube)
    except Exception as e:
        logger.error("Failed to authenticate: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to authenticate")


@app.post("/consolidate", response_model=ApiResponse)
async def consolidate_playlists_endpoint(request: ConsolidateRequest) -> ApiResponse:
    """Consolidate multiple playlists into one.

    Args:
        request: Consolidate request parameters

    Returns:
        ApiResponse: Response with success status and counts
    """
    try:
        youtube = get_youtube_client()

        # Verify source playlists exist
        for playlist_id in request.source_playlists:
            try:
                youtube.get_playlist_info(playlist_id)
            except PlaylistNotFoundError:
                raise HTTPException(
                    status_code=404,
                    detail=f"Source playlist {playlist_id} not found"
                )

        # Verify target playlist exists
        try:
            youtube.get_playlist_info(request.target_playlist)
        except PlaylistNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Target playlist {request.target_playlist} not found"
            )

        # Consolidate playlists
        from . import consolidate
        try:
            processed, failed, skipped = consolidate.consolidate_playlists(
                youtube,
                request.source_playlists,
                request.target_playlist,
                copy=request.copy,
                verbose=request.verbose,
                limit=request.limit,
                resume=request.resume,
                retry_failed=request.retry_failed,
            )
            return ApiResponse(success=True, processed=processed, failed=failed, skipped=skipped)
        except Exception as e:
            logger.error("Failed to consolidate playlists: %s", str(e))
            raise HTTPException(status_code=500, detail="API Error")

    except HTTPException:
        raise


@app.post("/distribute", response_model=ApiResponse)
async def distribute_videos_endpoint(request: DistributeRequest) -> ApiResponse:
    """Distribute videos from a playlist based on filter prompts.

    Args:
        request: Distribute request parameters

    Returns:
        ApiResponse: Response with success status and counts
    """
    try:
        youtube = get_youtube_client()

        # Verify source playlist exists
        try:
            youtube.get_playlist_info(request.source_playlist)
        except PlaylistNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Source playlist {request.source_playlist} not found"
            )

        # Verify target playlists exist
        for playlist_id in request.target_playlists:
            try:
                youtube.get_playlist_info(playlist_id)
            except PlaylistNotFoundError:
                raise HTTPException(
                    status_code=404,
                    detail=f"Target playlist {playlist_id} not found"
                )

        # Distribute videos
        from . import distribute
        success = distribute.distribute_videos(
            youtube=youtube,
            source_playlist=request.source_playlist,
            target_playlists=request.target_playlists,
            filter_prompts=request.filter_prompts,
            dry_run=request.dry_run,
            verbose=request.verbose,
            resume=request.resume,
            resume_destination=request.resume_destination,
            retry_failed=request.retry_failed,
            limit=request.limit,
        )

        return ApiResponse(success=success)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to distribute videos: %s", str(e))
        raise HTTPException(status_code=500, detail="API Error")


@app.post("/deduplicate", response_model=ApiResponse)
async def deduplicate_playlist_endpoint(request: DeduplicateRequest) -> ApiResponse:
    """Remove duplicate videos from a playlist.

    Args:
        request: Deduplicate request parameters

    Returns:
        ApiResponse: Response with success status and counts
    """
    try:
        youtube = get_youtube_client()

        # Verify playlist exists
        try:
            youtube.get_playlist_info(request.playlist_id)
        except PlaylistNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Playlist {request.playlist_id} not found"
            )

        # Deduplicate playlist
        from . import deduplicate
        removed = deduplicate.deduplicate_playlist(
            youtube=youtube,
            playlist_id=request.playlist_id,
        )

        return ApiResponse(success=bool(removed))

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to deduplicate playlist: %s", str(e))
        raise HTTPException(status_code=500, detail="API Error") 