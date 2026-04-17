"""
Lyrics API endpoint.
"""

from typing import Annotated, Optional
from uuid import UUID

from app.core.dependencies import get_current_active_user
from app.db.database import get_db
from app.models.track import Track
from app.models.user import User
from app.services.lyrics_service import lyrics_service
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

USE_CACHE_DESCRIPTION = "Whether to use cached results instead of fetching from external APIs"

router = APIRouter()


class LyricsResponse(BaseModel):
    """Response model for lyrics endpoint."""

    found: bool
    lyrics: Optional[str] = None
    synced_lyrics: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    url: Optional[str] = None
    album: Optional[str] = None
    cached: bool = False


class LyricsSearchRequest(BaseModel):
    """Request model for searching lyrics by artist/title."""

    artist: str
    title: str


@router.get("/track/{track_id}", response_model=LyricsResponse)
async def get_lyrics_by_track(
    track_id: UUID,
    use_cache: Annotated[bool, Query(description=USE_CACHE_DESCRIPTION)] = True,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get lyrics for a track by its ID.
    Fetches artist and title from database and searches Genius.
    """
    # Get track from database
    result = await db.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one_or_none()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    if not track.artist or not track.title:
        raise HTTPException(status_code=400, detail="Track missing artist or title information")

    # Fetch lyrics with track_id context for local metadata
    lyrics_data = await lyrics_service.get_lyrics(
        track.title, track.artist, use_cache=use_cache, track_id=str(track.id) if track.id else None
    )

    if not lyrics_data:
        return LyricsResponse(found=False)

    return LyricsResponse(
        found=lyrics_data.get("found", False),
        lyrics=lyrics_data.get("lyrics"),
        synced_lyrics=lyrics_data.get("synced_lyrics"),
        title=lyrics_data.get("title"),
        artist=lyrics_data.get("artist"),
        url=lyrics_data.get("url"),
        album=lyrics_data.get("album"),
        cached=lyrics_data.get("cached", False),
    )


@router.post("/search", response_model=LyricsResponse)
async def search_lyrics(
    request: LyricsSearchRequest,
    use_cache: Annotated[bool, Query(description=USE_CACHE_DESCRIPTION)] = True,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
):
    """
    Search for lyrics by artist and title.
    Does not require track to exist in database.
    """
    lyrics_data = await lyrics_service.get_lyrics(request.artist, request.title, use_cache=use_cache)

    if not lyrics_data:
        return LyricsResponse(found=False)

    return LyricsResponse(
        found=lyrics_data.get("found", False),
        lyrics=lyrics_data.get("lyrics"),
        synced_lyrics=lyrics_data.get("synced_lyrics"),
        title=lyrics_data.get("title"),
        artist=lyrics_data.get("artist"),
        url=lyrics_data.get("url"),
        album=lyrics_data.get("album"),
        cached=lyrics_data.get("cached", False),
    )


@router.get("/search", response_model=LyricsResponse)
async def search_lyrics_get(
    artist: Annotated[str, Query(description="Artist name")],
    title: Annotated[str, Query(description="Song title")],
    use_cache: Annotated[bool, Query(description=USE_CACHE_DESCRIPTION)] = True,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
):
    """
    Search for lyrics by artist and title (GET version for easy testing).
    """
    lyrics_data = await lyrics_service.get_lyrics(artist, title, use_cache=use_cache)

    if not lyrics_data:
        return LyricsResponse(found=False)

    return LyricsResponse(
        found=lyrics_data.get("found", False),
        lyrics=lyrics_data.get("lyrics"),
        synced_lyrics=lyrics_data.get("synced_lyrics"),
        title=lyrics_data.get("title"),
        artist=lyrics_data.get("artist"),
        url=lyrics_data.get("url"),
        album=lyrics_data.get("album"),
        cached=lyrics_data.get("cached", False),
    )
