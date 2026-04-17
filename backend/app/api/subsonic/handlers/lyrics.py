import logging
from typing import Annotated
from uuid import UUID

from app.api.subsonic.auth import subsonic_auth
from app.db.database import get_db
from app.models.track import Track
from app.models.user import User
from app.schemas.subsonic.base import subsonic_error, subsonic_response
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/getLyrics.view")
@router.post("/getLyrics.view")
async def get_lyrics(
    artist: Annotated[str | None, Query()] = None,
    title: Annotated[str | None, Query()] = None,
    id: Annotated[str | None, Query(description="Song ID")] = None,
    f: Annotated[str, Query()] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get lyrics for a song.
    """
    track = None
    if id:
        try:
            track = await db.get(Track, UUID(id))
        except Exception as e:
            logger.warning(f"Failed to get track by ID: {e}")

    # If no track found by ID, could search by artist/title?
    # For now, just return empty or error.

    # Check if we have lyrics in metadata (future proofing)
    lyrics = None
    if track and track.metadata_content:
        lyrics = track.metadata_content.get("lyrics")

    if not lyrics:
        # Fallback to empty/not found
        # Subsonic expects a 'lyrics' object
        # If not found, some servers return empty content or error.
        # Let's return empty structure.
        fallback_artist = track.artist if track else ""
        artist_value = artist if artist else fallback_artist
        fallback_title = track.title if track else ""
        title_value = title if title else fallback_title
        return subsonic_response(
            {
                "lyrics": {
                    "artist": artist_value,
                    "title": title_value,
                    "content": "Lyrics not available.",
                }
            },
            f=f,
        )

    if track:
        return subsonic_response({"lyrics": {"artist": track.artist, "title": track.title, "content": lyrics}}, f=f)

    return subsonic_error(70, "lyrics not found", f=f)
