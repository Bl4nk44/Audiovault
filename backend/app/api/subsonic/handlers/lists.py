"""
List handlers for Subsonic API.

Handles list-based endpoints:
- getAlbumList.view
- getAlbumList2.view
- getGenres.view
- getTopSongs.view
- getSimilarSongs.view
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.subsonic.auth import subsonic_auth
from app.api.subsonic.utils import (
    build_song_response,
    format_subsonic_date,
)
from app.db.database import get_db
from app.models.album import Album
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from app.models.user import User
from app.schemas.subsonic.base import subsonic_error, subsonic_response

router = APIRouter()

_RESPONSE_FORMAT = "Response format"


def _genre_expr(db: AsyncSession):
    """Dialect-aware extraction of the genre value from Track.metadata_content."""
    is_postgres = db.bind.dialect.name == "postgresql" if hasattr(db.bind, "dialect") else True
    if is_postgres:
        return func.json_extract_path_text(Track.metadata_content, "genre")
    return func.json_extract(Track.metadata_content, "$.genre")


def _album_year_expr():
    """Numeric year parsed from the leading YYYY of Album.release_date (NULL-safe)."""
    return func.cast(func.substr(Album.release_date, 1, 4), Integer)


def _apply_album_list_ordering(query, list_type: str):
    if list_type == "random":
        return query.order_by(func.random())
    if list_type in ("newest", "recent", "starred", "frequent"):
        return query.order_by(Album.created_at.desc())
    if list_type == "byYear":
        return query.order_by(_album_year_expr())
    if list_type in ("alphabetical", "byName", "alphabeticalByName", "alphabeticalByArtist", "byGenre"):
        return query.order_by(Album.title)
    return query.order_by(Album.id)


def _album_year(album: Album) -> int | None:
    return int(album.release_date[:4]) if album.release_date and len(album.release_date) >= 4 else None


async def _build_album_list_item(db: AsyncSession, album: Album, current_user: User, id3: bool = False) -> dict:
    artist_name = "Unknown Artist"
    if album.artist_id:
        artist_obj = await db.get(Artist, album.artist_id)
        if artist_obj:
            artist_name = artist_obj.name
    sc = (
        await db.scalar(
            select(func.count(Track.id))
            .join(Download, Download.track_id == Track.id)
            .where(Track.album_id == album.id, Download.user_id == current_user.id, Download.status == "completed")
        )
        or 0
    )
    artist_id = str(album.artist_id) if album.artist_id else None
    if id3:
        # getAlbumList2 — ID3 shape
        return {
            "id": str(album.id),
            "name": album.title,
            "artist": artist_name,
            "artistId": artist_id,
            "coverArt": f"al-{album.id}",
            "songCount": sc,
            "year": _album_year(album),
            "created": format_subsonic_date(album.created_at),
        }
    # getAlbumList — folder/directory shape
    return {
        "id": str(album.id),
        "parent": artist_id,
        "title": album.title,
        "artist": artist_name,
        "artistId": artist_id,
        "isDir": True,
        "coverArt": f"al-{album.id}",
        "songCount": sc,
        "year": _album_year(album),
        "created": format_subsonic_date(album.created_at),
    }


@router.get("/getGenres.view")
@router.post("/getGenres.view")
async def get_genres(
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get genres.

    Returns all genres found in ID3 tags.
    """
    # Updated to be dialect-aware (Postgres vs SQLite for tests)

    # Check dialect to use correct JSON extraction
    is_postgres = db.bind.dialect.name == "postgresql" if hasattr(db.bind, "dialect") else True

    if is_postgres:
        genre_query = func.json_extract_path_text(Track.metadata_content, "genre")
    else:
        # SQLite way for tests
        genre_query = func.json_extract(Track.metadata_content, "$.genre")

    result = await db.execute(
        select(genre_query)
        .join(Download, Download.track_id == Track.id)
        .where(
            Download.user_id == current_user.id,
            Download.status == "completed",
        )
        .distinct()
    )

    genres_found = [r for r in result.scalars().all() if r]

    # Sort and count (could be optimized with group_by in SQL if needed)
    genre_list = []

    for genre_name in sorted(genres_found):
        # Count songs and albums (approximate)
        # Doing simple count query for each genre
        if is_postgres:
            count_filter = func.json_extract_path_text(Track.metadata_content, "genre") == genre_name
        else:
            count_filter = func.json_extract(Track.metadata_content, "$.genre") == genre_name

        song_count = await db.scalar(
            select(func.count(Track.id))
            .join(Download, Download.track_id == Track.id)
            .where(Download.user_id == current_user.id, Download.status == "completed", count_filter)
        )

        genre_list.append(
            {
                "value": genre_name,
                "songCount": song_count,
                "albumCount": 1,  # Dummy value for now as calculating distinct albums per genre is complex
            }
        )

    return subsonic_response({"genres": {"genre": genre_list}}, f=f)


@router.get("/getAlbumList.view")
@router.post("/getAlbumList.view")
@router.get("/getAlbumList2.view")
@router.post("/getAlbumList2.view")
async def get_album_list(
    request: Request,
    type: Annotated[
        str,
        Query(description="List type: random, newest, frequent, recent, starred, alphabetical, byName, byYear"),
    ],
    size: Annotated[int, Query(description="Return size")] = 10,
    offset: Annotated[int, Query(description="Offset")] = 0,
    from_year: Annotated[int | None, Query(alias="fromYear", description="Filter from year")] = None,
    to_year: Annotated[int | None, Query(alias="toYear", description="Filter to year")] = None,
    genre: Annotated[str | None, Query(description="Filter by genre")] = None,
    music_folder_id: Annotated[str | None, Query(alias="musicFolderId", description="Music folder ID")] = None,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get list of albums.

    getAlbumList (folder/directory shape, wrapper ``albumList``) and getAlbumList2
    (ID3 shape, wrapper ``albumList2``) share this handler; the response shape is
    chosen by the request path. Supports the sort/filter ``type`` values clients
    actually send, plus byYear (fromYear/toYear) and byGenre (genre) filtering.
    """
    id3 = request.url.path.endswith("getAlbumList2.view")
    size = min(size, 500)

    query = (
        select(Album)
        .join(Track, Track.album_id == Album.id)
        .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
        .group_by(Album.id)
    )

    if type == "byYear":
        year_expr = _album_year_expr()
        if from_year is not None:
            query = query.where(year_expr >= from_year)
        if to_year is not None:
            query = query.where(year_expr <= to_year)
    if type == "byGenre" and genre:
        query = query.where(_genre_expr(db) == genre)

    query = _apply_album_list_ordering(query, type).offset(offset).limit(size)
    result = await db.execute(query)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
    album_list = [await _build_album_list_item(db, album, current_user, id3=id3) for album in result.scalars().all()]

    wrapper = "albumList2" if id3 else "albumList"
    return subsonic_response({wrapper: {"album": album_list}}, f=f)


@router.get("/getRandomSongs.view")
@router.post("/getRandomSongs.view")
async def get_random_songs(
    size: Annotated[int, Query(description="Count")] = 10,
    genre: Annotated[str | None, Query(description="Genre")] = None,
    from_year: Annotated[int | None, Query(alias="fromYear", description="From year")] = None,
    to_year: Annotated[int | None, Query(alias="toYear", description="To year")] = None,
    music_folder_id: Annotated[str | None, Query(alias="musicFolderId", description="Folder ID")] = None,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get random songs.
    """
    size = min(size, 500)

    query = (
        select(Track, Download)
        .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
        .order_by(func.random())
        .limit(size)
    )

    # Apply filters if needed (genre, year, etc - simplified for now)

    result = await db.execute(query)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
    songs = []
    for track, download in result.all():
        songs.append(build_song_response(track, download))

    return subsonic_response({"randomSongs": {"song": songs}}, f=f)


@router.get("/getTopSongs.view")
@router.post("/getTopSongs.view")
async def get_top_songs(
    artist: Annotated[str | None, Query(description="Artist name")] = None,
    count: Annotated[int, Query(description="Count")] = 50,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get top songs (not really tracking play counts per song globally yet).
    Returns random songs for now or alphabetical.
    """
    # Return random as placeholder for "top"
    query = (
        select(Track, Download)
        .join(Download, Download.track_id == Track.id)
        .where(Download.user_id == current_user.id)
        .limit(count)
    )

    if artist:
        query = query.where(Track.artist == artist)

    result = await db.execute(query)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
    songs = []
    for track, download in result.all():
        songs.append(build_song_response(track, download))

    return subsonic_response({"topSongs": {"song": songs}}, f=f)


@router.get("/getSimilarSongs.view")
@router.post("/getSimilarSongs.view")
async def get_similar_songs(
    id: Annotated[str, Query(description="Song ID")],
    count: Annotated[int, Query(description="Count")] = 50,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get similar songs. Returns random songs from same genre or artist.
    """
    try:
        track_id = UUID(id)
    except ValueError:
        return subsonic_error(10, "Invalid ID", f=f)

    track = await db.get(Track, track_id)
    if not track:
        return subsonic_error(70, "Song not found", f=f)

    # Find songs by same artist
    query = (
        select(Track, Download)
        .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
        .where(
            Download.status == "completed",  # Keep this filter if we only want completed downloads
            Track.artist_id == track.artist_id,
            Track.id != track.id,
        )
        .limit(count)
    )

    result = await db.execute(query)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
    songs = []
    for t, d in result.all():
        songs.append(build_song_response(t, d))

    return subsonic_response({"similarSongs": {"song": songs}}, f=f)
