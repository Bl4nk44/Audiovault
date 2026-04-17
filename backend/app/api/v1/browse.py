"""
Browse API routes — Unified multi-source search and metadata browsing.

Replaces the Spotify-only endpoints with provider-agnostic routes
powered by SearchOrchestrator.

Endpoints:
- GET /search — Multi-source search (tracks, artists, albums, playlists)
- GET /track/{source}/{id} — Track details from specific provider
- GET /artist/{source}/{id} — Artist details from specific provider
- GET /album/{source}/{id} — Album details from specific provider
- GET /playlist/{source}/{id} — Playlist details from specific provider
"""

import logging
from typing import Annotated

from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.search_orchestrator import search_orchestrator
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search")
async def browse_search(
    q: str,
    limit: int = 20,
    offset: int = 0,
    type: str = "track",
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
):
    """
    Search across multiple music providers (Deezer, MusicBrainz, Spotify if configured).

    Supports types: track, artist, album, playlist.
    Results are deduplicated by ISRC and title+artist.
    """
    try:
        if type == "artist":
            return await search_orchestrator.search_artists(q, limit=limit)
        elif type == "album":
            return await search_orchestrator.search_albums(q, limit=limit)
        elif type == "playlist":
            # For playlist search, delegate to Deezer/Spotify directly
            return await search_orchestrator.search_tracks(q, limit=limit)
        else:
            # Default: track search
            return await search_orchestrator.search_tracks(q, limit=limit)
    except Exception as e:
        logger.error(f"Browse search error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/track/{source}/{track_id}")
async def browse_track(
    source: str,
    track_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
):
    """Get track details from a specific provider (deezer, spotify, musicbrainz)."""
    result = await search_orchestrator.get_track_details(source, track_id)
    if not result:
        raise HTTPException(status_code=404, detail="Track not found")
    return result


@router.get("/artist/{source}/{artist_id}")
async def browse_artist(
    source: str,
    artist_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
):
    """Get artist details from a specific provider."""
    result = await search_orchestrator.get_artist_details(source, artist_id)
    if not result:
        raise HTTPException(status_code=404, detail="Artist not found")
    return result


@router.get("/album/{source}/{album_id}")
async def browse_album(
    source: str,
    album_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
):
    """Get album details from a specific provider."""
    result = await search_orchestrator.get_album_details(source, album_id)
    if not result:
        raise HTTPException(status_code=404, detail="Album not found")
    return result


@router.get("/playlist/{source}/{playlist_id}")
async def browse_playlist(
    source: str,
    playlist_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
):
    """Get playlist details from a specific provider."""
    result = await search_orchestrator.get_playlist_details(source, playlist_id)
    if not result:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return result
