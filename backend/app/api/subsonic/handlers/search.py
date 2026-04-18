"""
Search handlers for Subsonic API.

Handles search endpoints:
- search2.view (API 1.4+)
- search3.view (API 1.8+)
"""

from typing import Annotated

from app.api.subsonic.auth import subsonic_auth
from app.api.subsonic.utils import (
    build_song_response,
    format_duration,
    format_subsonic_date,
)
from app.db.database import get_db
from app.models.album import Album
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from app.models.user import User
from app.schemas.subsonic.base import subsonic_response
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

_RESPONSE_FORMAT = "Response format"


async def _search_artists(
    db: AsyncSession, current_user: User, search_term: str, count: int, offset: int, id3: bool = False
) -> list:
    result = await db.execute(
        select(Artist)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
        .join(Track, Track.artist_id == Artist.id)
        .join(Download, Download.track_id == Track.id)
        .where(
            Download.user_id == current_user.id,
            Download.status == "completed",
            func.lower(Artist.name).like(search_term),
        )
        .group_by(Artist.id)
        .order_by(Artist.name)
        .offset(offset)
        .limit(count)
    )
    out = []
    for artist_obj in result.scalars():
        ac = await db.scalar(select(func.count(Album.id.distinct())).where(Album.artist_id == artist_obj.id)) or 0
        entry = {
            "id": str(artist_obj.id),
            "name": artist_obj.name,
            "coverArt": f"ar-{artist_obj.id}" if artist_obj.images else None,
        }
        entry["albumCount" if id3 else "album_count"] = ac
        out.append(entry)
    return out


async def _search2_albums(
    db: AsyncSession, current_user: User, search_term: str, count: int, offset: int
) -> list:
    result = await db.execute(
        select(Album)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
        .join(Track, Track.album_id == Album.id)
        .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
        .where(func.lower(Album.title).like(search_term))
        .group_by(Album.id)
        .order_by(Album.title)
        .offset(offset)
        .limit(count)
    )
    out = []
    for album_obj in result.scalars():
        artist_name = "Unknown Artist"
        if album_obj.artist_id:
            name = await db.scalar(select(Artist.name).where(Artist.id == album_obj.artist_id))
            if name:
                artist_name = name
        sc = await db.scalar(
            select(func.count(Track.id))
            .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
            .where(Track.album_id == album_obj.id)
        ) or 0
        out.append({
            "id": str(album_obj.id),
            "parent": str(album_obj.artist_id) if album_obj.artist_id else "1",
            "title": album_obj.title,
            "artist": artist_name,
            "isDir": True,
            "coverArt": f"al-{album_obj.id}",
            "songCount": sc,
            "year": (
                int(album_obj.release_date[:4])
                if album_obj.release_date and len(album_obj.release_date) >= 4
                else None
            ),
        })
    return out


async def _search3_albums(
    db: AsyncSession, current_user: User, search_term: str, count: int, offset: int
) -> list:
    result = await db.execute(
        select(Album)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
        .join(Track, Track.album_id == Album.id)
        .join(Download, Download.track_id == Track.id)
        .where(Download.user_id == current_user.id, func.lower(Album.title).like(search_term))
        .group_by(Album.id)
        .order_by(Album.title)
        .offset(offset)
        .limit(count)
    )
    out = []
    for album_obj in result.scalars():
        artist_name = "Unknown Artist"
        if album_obj.artist_id:
            name = await db.scalar(select(Artist.name).where(Artist.id == album_obj.artist_id))
            if name:
                artist_name = name
        sc = await db.scalar(
            select(func.count(Track.id))
            .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
            .where(Track.album_id == album_obj.id)
        ) or 0
        total_ms = await db.scalar(
            select(func.sum(Track.duration_ms))
            .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
            .where(Track.album_id == album_obj.id)
        ) or 0
        out.append({
            "id": str(album_obj.id),
            "name": album_obj.title,
            "artist": artist_name,
            "artistId": str(album_obj.artist_id) if album_obj.artist_id else None,
            "coverArt": f"al-{album_obj.id}",
            "songCount": sc,
            "duration": format_duration(total_ms),
            "created": format_subsonic_date(album_obj.created_at),
            "year": (
                int(album_obj.release_date[:4])
                if album_obj.release_date and len(album_obj.release_date) >= 4
                else None
            ),
        })
    return out


async def _search_songs(
    db: AsyncSession, current_user: User, search_term: str, count: int, offset: int, id3: bool = False
) -> list:
    if id3:
        result = await db.execute(
            # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
            select(Track, Download)
            .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
            .where(
                or_(
                    func.lower(Track.title).like(search_term),
                    func.lower(Track.artist).like(search_term),
                    func.lower(Track.album).like(search_term),
                )
            )
            .offset(offset)
            .limit(count)
        )
    else:
        result = await db.execute(
            select(Track, Download)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
            .join(Download, Download.track_id == Track.id)
            .where(
                Download.user_id == current_user.id,
                Download.status == "completed",
                or_(
                    func.lower(Track.title).like(search_term),
                    func.lower(Track.artist).like(search_term),
                    func.lower(Track.album).like(search_term),
                ),
            )
            .offset(offset)
            .limit(count)
        )
    out = []
    for track, download in result.all():
        song = build_song_response(track, download)
        if not id3:
            song["parent"] = str(track.album_id) if track.album_id else "1"
        out.append(song)
    return out


@router.get("/search.view")
@router.post("/search.view")
async def search_legacy(
    artist: Annotated[str | None, Query(description="Artist to search")] = None,
    album: Annotated[str | None, Query(description="Album to search")] = None,
    title: Annotated[str | None, Query(description="Song title to search")] = None,
    any: Annotated[str | None, Query(description="Search any field")] = None,
    count: Annotated[int, Query(description="Max results")] = 20,
    offset: Annotated[int, Query(description="Result offset")] = 0,
    newer_than: Annotated[int | None, Query(alias="newerThan", description="Only return newer than timestamp")] = None,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Legacy search (API 1.0).

    Searches for songs matching criteria.
    Deprecated in favor of search2/search3.
    """
    # Build search query
    query_text = any or title or album or artist or ""

    if not query_text:
        return subsonic_response({"searchResult": {"match": []}})

    # Search tracks
    search_term = f"%{query_text.lower()}%"

    result = await db.execute(
        select(Track, Download)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
        .join(Download, Download.track_id == Track.id)
        .where(
            Download.user_id == current_user.id,
            Download.status == "completed",
            or_(
                func.lower(Track.title).like(search_term),
                func.lower(Track.artist).like(search_term),
                func.lower(Track.album).like(search_term),
            ),
        )
        .offset(offset)
        .limit(count)
    )
    track_downloads = result.all()

    matches = []
    for track, download in track_downloads:
        matches.append(build_song_response(track, download))

    return subsonic_response({"searchResult": {"match": matches}}, f=f)


@router.get("/search2.view")
@router.post("/search2.view")
async def search2(
    query: Annotated[str, Query(description="Search query")],
    artist_count: Annotated[int, Query(alias="artistCount", description="Max artists to return")] = 20,
    artist_offset: Annotated[int, Query(alias="artistOffset", description="Artist offset")] = 0,
    album_count: Annotated[int, Query(alias="albumCount", description="Max albums to return")] = 20,
    album_offset: Annotated[int, Query(alias="albumOffset", description="Album offset")] = 0,
    song_count: Annotated[int, Query(alias="songCount", description="Max songs to return")] = 20,
    song_offset: Annotated[int, Query(alias="songOffset", description="Song offset")] = 0,
    music_folder_id: Annotated[str | None, Query(alias="musicFolderId", description="Music folder ID")] = None,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Enhanced search (API 1.4+).

    Searches artists, albums, and songs in parallel.
    Returns results in folder/directory view format.

    Args:
        query: Search query (case-insensitive, partial match)
        artistCount: Maximum number of artists to return
        albumCount: Maximum number of albums to return
        songCount: Maximum number of songs to return

    Returns:
        Search results with artists, albums, and songs
    """
    search_term = f"%{query.lower()}%"
    artists_result = (
        await _search_artists(db, current_user, search_term, artist_count, artist_offset) if artist_count > 0 else []
    )
    albums_result = (
        await _search2_albums(db, current_user, search_term, album_count, album_offset) if album_count > 0 else []
    )
    songs_result = (
        await _search_songs(db, current_user, search_term, song_count, song_offset) if song_count > 0 else []
    )
    return subsonic_response(
        {"searchResult2": {"artist": artists_result, "album": albums_result, "song": songs_result}}, f=f
    )


@router.get("/search3.view")
@router.post("/search3.view")
async def search3(
    query: Annotated[str, Query(description="Search query")],
    artist_count: Annotated[int, Query(alias="artistCount", description="Max artists to return")] = 20,
    artist_offset: Annotated[int, Query(alias="artistOffset", description="Artist offset")] = 0,
    album_count: Annotated[int, Query(alias="albumCount", description="Max albums to return")] = 20,
    album_offset: Annotated[int, Query(alias="albumOffset", description="Album offset")] = 0,
    song_count: Annotated[int, Query(alias="songCount", description="Max songs to return")] = 20,
    song_offset: Annotated[int, Query(alias="songOffset", description="Song offset")] = 0,
    music_folder_id: Annotated[str | None, Query(alias="musicFolderId", description="Music folder ID")] = None,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Latest search (API 1.8+).

    Same as search2 but returns ID3 tag format.

    Args:
        query: Search query
        artistCount: Maximum number of artists
        albumCount: Maximum number of albums
        songCount: Maximum number of songs

    Returns:
        Search results in ID3 format
    """
    search_term = f"%{query.lower()}%"
    artists_result = (
        await _search_artists(db, current_user, search_term, artist_count, artist_offset, id3=True)
        if artist_count > 0
        else []
    )
    albums_result = (
        await _search3_albums(db, current_user, search_term, album_count, album_offset) if album_count > 0 else []
    )
    songs_result = (
        await _search_songs(db, current_user, search_term, song_count, song_offset, id3=True)
        if song_count > 0
        else []
    )
    return subsonic_response(
        {"searchResult3": {"artist": artists_result, "album": albums_result, "song": songs_result}}, f=f
    )
