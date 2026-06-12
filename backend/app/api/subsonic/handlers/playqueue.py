"""
Play queue and bookmark handlers for Subsonic API.

Handles cross-device playback state:
- getPlayQueue.view / savePlayQueue.view
- getBookmarks.view / createBookmark.view / deleteBookmark.view
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.subsonic.auth import subsonic_auth
from app.api.subsonic.utils import build_song_response, format_subsonic_date
from app.db.database import get_db
from app.models.subsonic import SubsonicBookmark, SubsonicPlayQueue
from app.models.track import Track
from app.models.user import User
from app.schemas.subsonic.base import subsonic_error, subsonic_response

router = APIRouter()

_RESPONSE_FORMAT = "Response format"


def _parse_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None


async def _songs_for_ids(db: AsyncSession, ids: list[UUID]) -> dict[UUID, dict]:
    """Fetch Subsonic song entries for the given track ids, keyed by id."""
    if not ids:
        return {}
    result = await db.execute(select(Track).where(Track.id.in_(ids)))
    return {track.id: build_song_response(track) for track in result.scalars()}


@router.get("/savePlayQueue.view")
@router.post("/savePlayQueue.view")
async def save_play_queue(
    id: Annotated[list[str], Query(description="Track ids in queue order")] = [],  # noqa: B006
    current: Annotated[str | None, Query(description="Currently playing track id")] = None,
    position: Annotated[int, Query(description="Position within current track (ms)")] = 0,
    c: Annotated[str | None, Query(description="Client name")] = None,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """Save the user's play queue, replacing any previously saved queue."""
    track_ids = [tid for tid in id if _parse_uuid(tid) is not None]
    current_uuid = _parse_uuid(current) if current else None

    existing = await db.scalar(select(SubsonicPlayQueue).where(SubsonicPlayQueue.user_id == current_user.id))
    if existing is None:
        existing = SubsonicPlayQueue(user_id=current_user.id)
        db.add(existing)

    existing.track_ids = track_ids
    existing.current_track_id = current_uuid
    existing.position_ms = position
    existing.changed_by = c
    await db.commit()

    return subsonic_response(f=f)


@router.get("/getPlayQueue.view")
@router.post("/getPlayQueue.view")
async def get_play_queue(
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """Return the user's saved play queue, or an empty envelope if none exists."""
    pq = await db.scalar(select(SubsonicPlayQueue).where(SubsonicPlayQueue.user_id == current_user.id))
    if pq is None or not pq.track_ids:
        return subsonic_response(f=f)

    ordered_ids = [uuid for tid in pq.track_ids if (uuid := _parse_uuid(tid)) is not None]
    songs_by_id = await _songs_for_ids(db, ordered_ids)
    entries = [songs_by_id[uuid] for uuid in ordered_ids if uuid in songs_by_id]

    play_queue: dict = {
        "username": current_user.username,
        "position": pq.position_ms,
        "changed": format_subsonic_date(pq.changed_at),
        "changedBy": pq.changed_by or "",
        "entry": entries,
    }
    if pq.current_track_id is not None:
        play_queue["current"] = str(pq.current_track_id)

    return subsonic_response({"playQueue": play_queue}, f=f)


@router.get("/getBookmarks.view")
@router.post("/getBookmarks.view")
async def get_bookmarks(
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """Return all bookmarks for the current user."""
    result = await db.execute(
        select(SubsonicBookmark)
        .where(SubsonicBookmark.user_id == current_user.id)
        .order_by(SubsonicBookmark.changed_at.desc())
    )
    bookmarks = result.scalars().all()

    songs_by_id = await _songs_for_ids(db, [bm.track_id for bm in bookmarks])
    bookmark_list = []
    for bm in bookmarks:
        entry = songs_by_id.get(bm.track_id)
        if entry is None:
            continue
        bookmark_list.append(
            {
                "position": bm.position_ms,
                "username": current_user.username,
                "comment": bm.comment or "",
                "created": format_subsonic_date(bm.created_at),
                "changed": format_subsonic_date(bm.changed_at),
                "entry": entry,
            }
        )

    return subsonic_response({"bookmarks": {"bookmark": bookmark_list}}, f=f)


@router.get("/createBookmark.view")
@router.post("/createBookmark.view")
async def create_bookmark(
    id: Annotated[str, Query(description="Track id to bookmark")],
    position: Annotated[int, Query(description="Bookmark position (ms)")] = 0,
    comment: Annotated[str | None, Query(description="Bookmark comment")] = None,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """Create or update a bookmark for a track. Re-bookmarking updates position/comment."""
    track_uuid = _parse_uuid(id)
    if track_uuid is None:
        return subsonic_error(10, "Invalid track id", f=f)

    track = await db.get(Track, track_uuid)
    if track is None:
        return subsonic_error(70, "Track not found", f=f)

    existing = await db.scalar(
        select(SubsonicBookmark).where(
            SubsonicBookmark.user_id == current_user.id,
            SubsonicBookmark.track_id == track_uuid,
        )
    )
    if existing is None:
        existing = SubsonicBookmark(user_id=current_user.id, track_id=track_uuid)
        db.add(existing)
    existing.position_ms = position
    existing.comment = comment
    await db.commit()

    return subsonic_response(f=f)


@router.get("/deleteBookmark.view")
@router.post("/deleteBookmark.view")
async def delete_bookmark(
    id: Annotated[str, Query(description="Track id to remove bookmark for")],
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """Delete a track's bookmark for the current user."""
    track_uuid = _parse_uuid(id)
    if track_uuid is None:
        return subsonic_error(10, "Invalid track id", f=f)

    await db.execute(
        delete(SubsonicBookmark).where(
            SubsonicBookmark.user_id == current_user.id,
            SubsonicBookmark.track_id == track_uuid,
        )
    )
    await db.commit()

    return subsonic_response(f=f)
