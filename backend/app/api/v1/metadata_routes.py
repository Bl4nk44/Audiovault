import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.metadata import TrackMetadata

router = APIRouter()
logger = logging.getLogger(__name__)


class ResolvedTrack(BaseModel):
    id: str
    title: str
    artist: str
    album: str | None = None


# Maps a metadata source to the Track column holding that platform's native ID.
_SOURCE_ID_FIELDS = {
    "spotify": "spotify_id",
    "deezer": "deezer_id",
    "youtube": "youtube_id",
}


async def _find_existing_track(db: AsyncSession, source: str, source_id: str):
    """Return the Track matching the platform ID, or None."""
    id_field = _SOURCE_ID_FIELDS.get(source)
    if not source_id or not id_field:
        return None

    from sqlalchemy.future import select

    from app.models.track import Track

    result = await db.execute(select(Track).where(getattr(Track, id_field) == source_id))
    return result.scalar_one_or_none()


def _build_track_kwargs(metadata: TrackMetadata, source: str, source_id: str) -> dict:
    """Assemble the kwargs for creating a new Track from import metadata."""
    meta: dict = {
        "image_url": metadata.image_url,
        "album": metadata.album,
        "source_url": metadata.source_url,
    }
    if source == "spotify":
        meta["album_art"] = metadata.image_url
        meta["isrc"] = metadata.isrc

    kwargs: dict = {
        "title": metadata.title,
        "artist": metadata.artist,
        "duration_ms": metadata.duration_ms,
        "metadata_source": source or "imported",
        "metadata_content": meta,
    }

    id_field = _SOURCE_ID_FIELDS.get(source)
    if id_field and source_id:
        kwargs[id_field] = source_id
        if source == "deezer" and metadata.isrc:
            kwargs["isrc"] = metadata.isrc

    return kwargs


@router.post("/resolve", response_model=ResolvedTrack)
async def resolve_track_metadata(
    metadata: TrackMetadata,
    current_user: Annotated[User, Depends(get_current_active_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Find or create a Track DB entry from metadata.
    Used by the playlist import flow to obtain a local UUID before queuing a download.
    """
    from app.models.track import Track

    source = metadata.source or ""
    source_id = metadata.source_id or ""

    track_obj = await _find_existing_track(db, source, source_id)

    if track_obj is None:
        track_obj = Track(**_build_track_kwargs(metadata, source, source_id))
        db.add(track_obj)
        await db.flush()
        await db.commit()
        await db.refresh(track_obj)

    return ResolvedTrack(
        id=str(track_obj.id),
        title=track_obj.title,
        artist=track_obj.artist or "",
        album=(track_obj.metadata_content or {}).get("album") if track_obj.metadata_content else None,
    )
