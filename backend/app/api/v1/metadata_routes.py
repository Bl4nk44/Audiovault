import logging
from typing import Annotated

from app.core.dependencies import get_current_active_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.metadata import TrackMetadata
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = logging.getLogger(__name__)


class ResolvedTrack(BaseModel):
    id: str
    title: str
    artist: str
    album: str | None = None


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
    from sqlalchemy.future import select

    source = metadata.source or ""
    source_id = metadata.source_id or ""

    # Try to find existing track by platform ID
    track_obj: Track | None = None
    if source_id:
        id_field = {
            "spotify": "spotify_id",
            "deezer": "deezer_id",
            "youtube": "youtube_id",
        }.get(source)

        if id_field:
            result = await db.execute(select(Track).where(getattr(Track, id_field) == source_id))
            track_obj = result.scalar_one_or_none()

    if track_obj is None:
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
        if source == "spotify" and source_id:
            kwargs["spotify_id"] = source_id
        elif source == "deezer" and source_id:
            kwargs["deezer_id"] = source_id
            if metadata.isrc:
                kwargs["isrc"] = metadata.isrc
        elif source == "youtube" and source_id:
            kwargs["youtube_id"] = source_id

        track_obj = Track(**kwargs)
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
