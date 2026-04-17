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


@router.get("/search.view")
@router.post("/search.view")
async def search_legacy(
    artist: str = Query(None, description="Artist to search"),
    album: str = Query(None, description="Album to search"),
    title: str = Query(None, description="Song title to search"),
    any: str = Query(None, description="Search any field"),
    count: int = Query(20, description="Max results"),
    offset: int = Query(0, description="Result offset"),
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
    query: str = Query(..., description="Search query"),
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

    # Search artists
    artists_result = []
    if artist_count > 0:
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
            .offset(artist_offset)
            .limit(artist_count)
        )

        for artist_obj in result.scalars():
            # Count albums
            album_result = await db.execute(
                select(func.count(Album.id.distinct())).where(Album.artist_id == artist_obj.id)
            )
            album_count = album_result.scalar() or 0

            artists_result.append(
                {
                    "id": str(artist_obj.id),
                    "name": artist_obj.name,
                    "album_count": album_count,
                    "coverArt": f"ar-{artist_obj.id}" if artist_obj.images else None,
                }
            )

    # Search albums
    albums_result = []
    if album_count > 0:
        albums_result_db = await db.execute(
            select(Album)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
            .join(Track, Track.album_id == Album.id)
            .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
            .where(
                func.lower(Album.title).like(search_term),
            )
            .group_by(Album.id)
            .order_by(Album.title)
            .offset(album_offset)
            .limit(album_count)
        )

        for album_obj in albums_result_db.scalars():
            # Get artist name
            artist_name = "Unknown Artist"
            if album_obj.artist_id:
                artist_result = await db.execute(select(Artist.name).where(Artist.id == album_obj.artist_id))
                name = artist_result.scalar()
                if name:
                    artist_name = name

            # Count songs
            song_result = await db.execute(
                select(func.count(Track.id))
                .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
                .where(
                    Track.album_id == album_obj.id,
                )
            )
            song_count = song_result.scalar() or 0

            albums_result.append(
                {
                    "id": str(album_obj.id),
                    "parent": str(album_obj.artist_id) if album_obj.artist_id else "1",
                    "title": album_obj.title,
                    "artist": artist_name,
                    "isDir": True,
                    "coverArt": f"al-{album_obj.id}",
                    "songCount": song_count,
                    "year": int(album_obj.release_date[:4])
                    if album_obj.release_date and len(album_obj.release_date) >= 4
                    else None,
                }
            )

    # Search songs
    songs_result = []
    if song_count > 0:
        songs_result_db = await db.execute(
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
            .offset(song_offset)
            .limit(song_count)
        )

        for track, download in songs_result_db.all():
            song = build_song_response(track, download)
            song["parent"] = str(track.album_id) if track.album_id else "1"
            songs_result.append(song)

    return subsonic_response(
        {
            "searchResult2": {
                "artist": artists_result,
                "album": albums_result,
                "song": songs_result,
            }
        },
        f=f,
    )


@router.get("/search3.view")
@router.post("/search3.view")
async def search3(
    query: str = Query(..., description="Search query"),
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

    # Search artists (ID3 format)
    artists_result = []
    if artist_count > 0:
        artists_result_db = await db.execute(
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
            .offset(artist_offset)
            .limit(artist_count)
        )

        for artist_obj in artists_result_db.scalars():
            album_result = await db.execute(
                select(func.count(Album.id.distinct())).where(Album.artist_id == artist_obj.id)
            )
            album_count = album_result.scalar() or 0

            artists_result.append(
                {
                    "id": str(artist_obj.id),
                    "name": artist_obj.name,
                    "albumCount": album_count,
                    "coverArt": f"ar-{artist_obj.id}" if artist_obj.images else None,
                }
            )

    # Search albums (ID3 format)
    albums_result = []
    if album_count > 0:
        albums_result_db = await db.execute(
            select(Album)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
            .join(Track, Track.album_id == Album.id)
            .join(Download, Download.track_id == Track.id)
            .where(
                Download.user_id == current_user.id,
                func.lower(Album.title).like(search_term),
            )
            .group_by(Album.id)
            .order_by(Album.title)
            .offset(album_offset)
            .limit(album_count)
        )

        for album_obj in albums_result_db.scalars():
            artist_name = "Unknown Artist"
            if album_obj.artist_id:
                artist_result = await db.execute(select(Artist.name).where(Artist.id == album_obj.artist_id))
                name = artist_result.scalar()
                if name:
                    artist_name = name

            song_result = await db.execute(
                select(func.count(Track.id))
                .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
                .where(
                    Track.album_id == album_obj.id,
                )
            )
            song_count = song_result.scalar() or 0

            # Sum duration
            duration_result = await db.execute(
                select(func.sum(Track.duration_ms))
                .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
                .where(
                    Track.album_id == album_obj.id,
                )
            )
            total_duration = duration_result.scalar() or 0

            albums_result.append(
                {
                    "id": str(album_obj.id),
                    "name": album_obj.title,
                    "artist": artist_name,
                    "artistId": str(album_obj.artist_id) if album_obj.artist_id else None,
                    "coverArt": f"al-{album_obj.id}",
                    "songCount": song_count,
                    "duration": format_duration(total_duration),
                    "created": format_subsonic_date(album_obj.created_at),
                    "year": int(album_obj.release_date[:4])
                    if album_obj.release_date and len(album_obj.release_date) >= 4
                    else None,
                }
            )

    # Search songs (same as search2)
    songs_result = []
    if song_count > 0:
        # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
        songs_result_db = await db.execute(
            select(Track, Download)
            .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
            .where(
                # Download.user_id == current_user.id,
                or_(
                    func.lower(Track.title).like(search_term),
                    func.lower(Track.artist).like(search_term),
                    func.lower(Track.album).like(search_term),
                )
            )
            .offset(song_offset)
            .limit(song_count)
        )

        for track, download in songs_result_db.all():
            songs_result.append(build_song_response(track, download))

    return subsonic_response(
        {
            "searchResult3": {
                "artist": artists_result,
                "album": albums_result,
                "song": songs_result,
            }
        },
        f=f,
    )
