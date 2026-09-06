"""
User action handlers for Subsonic API.

Handles user interactions:
- star.view / unstar.view
- setRating.view
- scrobble.view
- getStarred.view / getStarred2.view
- getNowPlaying.view
"""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, delete, select
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
from app.models.history import ListeningHistory
from app.models.starred import StarredAlbum, StarredArtist, StarredTrack
from app.models.subsonic import SubsonicNowPlaying, SubsonicRating
from app.models.track import Track
from app.models.user import User
from app.schemas.subsonic.base import subsonic_error, subsonic_response

router = APIRouter()

_RESPONSE_FORMAT = "Response format"
_MUSIC_FOLDER_ID_DESC = "Music folder ID"


async def _star_item(db: AsyncSession, model, user_id, field_name: str, id_str: str) -> None:
    try:
        item_uuid = UUID(id_str)
        existing = await db.execute(
            select(model).where(model.user_id == user_id, getattr(model, field_name) == item_uuid)
        )
        if not existing.scalar_one_or_none():
            db.add(model(**{"user_id": user_id, field_name: item_uuid}))
    except ValueError:
        pass


async def _unstar_item(db: AsyncSession, model, user_id, field_name: str, id_str: str) -> None:
    try:
        item_uuid = UUID(id_str)
        await db.execute(delete(model).where(model.user_id == user_id, getattr(model, field_name) == item_uuid))
    except ValueError:
        pass


@router.get("/star.view")
@router.post("/star.view")
async def star(
    id: Annotated[list[str] | None, Query(description="Song IDs to star")] = None,
    album_id: Annotated[list[str] | None, Query(alias="albumId", description="Album IDs to star")] = None,
    artist_id: Annotated[list[str] | None, Query(alias="artistId", description="Artist IDs to star")] = None,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Add items to starred/favorites.

    Can star songs, albums, and/or artists in a single request.
    Uses existing StarredTrack, StarredAlbum, StarredArtist models.

    Args:
        id: Song/track IDs
        albumId: Album IDs
        artistId: Artist IDs

    Returns:
        Empty success response
    """
    if id:
        for track_id_str in id:
            await _star_item(db, StarredTrack, current_user.id, "track_id", track_id_str)
    if album_id:
        for album_id_str in album_id:
            await _star_item(db, StarredAlbum, current_user.id, "album_id", album_id_str)
    if artist_id:
        for artist_id_str in artist_id:
            await _star_item(db, StarredArtist, current_user.id, "artist_id", artist_id_str)

    await db.commit()
    return subsonic_response(f=f)


@router.get("/unstar.view")
@router.post("/unstar.view")
async def unstar(
    id: Annotated[list[str] | None, Query(description="Song IDs to unstar")] = None,
    album_id: Annotated[list[str] | None, Query(alias="albumId", description="Album IDs to unstar")] = None,
    artist_id: Annotated[list[str] | None, Query(alias="artistId", description="Artist IDs to unstar")] = None,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Remove items from starred/favorites.

    Args:
        id: Song/track IDs
        albumId: Album IDs
        artistId: Artist IDs

    Returns:
        Empty success response
    """
    if id:
        for track_id_str in id:
            await _unstar_item(db, StarredTrack, current_user.id, "track_id", track_id_str)
    if album_id:
        for album_id_str in album_id:
            await _unstar_item(db, StarredAlbum, current_user.id, "album_id", album_id_str)
    if artist_id:
        for artist_id_str in artist_id:
            await _unstar_item(db, StarredArtist, current_user.id, "artist_id", artist_id_str)

    await db.commit()
    return subsonic_response(f=f)


@router.get("/getStarred.view")
@router.post("/getStarred.view")
async def get_starred(
    music_folder_id: Annotated[str | None, Query(alias="musicFolderId", description=_MUSIC_FOLDER_ID_DESC)] = None,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get all starred items (folder view format).

    Returns:
        Starred artists, albums, and songs
    """
    # Get starred artists
    result = await db.execute(
        select(StarredArtist, Artist)
        .join(Artist, Artist.id == StarredArtist.artist_id)
        .where(StarredArtist.user_id == current_user.id)
        .order_by(Artist.name)
    )
    starred_artists = []
    for starred, artist in result.all():
        starred_artists.append(
            {
                "id": str(artist.id),
                "name": artist.name,
                "starred": format_subsonic_date(starred.created_at),
            }
        )

    # Get starred albums
    result = await db.execute(
        select(StarredAlbum, Album)
        .join(Album, Album.id == StarredAlbum.album_id)
        .where(StarredAlbum.user_id == current_user.id)
        .order_by(Album.title)
    )
    starred_albums = []
    for starred, album in result.all():
        artist_name = "Unknown Artist"
        if album.artist_id:
            artist_result = await db.execute(select(Artist.name).where(Artist.id == album.artist_id))
            name = artist_result.scalar()
            if name:
                artist_name = name

        starred_albums.append(
            {
                "id": str(album.id),
                "parent": str(album.artist_id) if album.artist_id else "1",
                "title": album.title,
                "artist": artist_name,
                "isDir": True,
                "coverArt": f"al-{album.id}",
                "starred": format_subsonic_date(starred.created_at),
            }
        )

    # Get starred tracks
    result = await db.execute(
        select(StarredTrack, Track, Download)
        .join(Track, Track.id == StarredTrack.track_id)
        .outerjoin(
            Download,
            and_(
                Download.track_id == Track.id,
                Download.user_id == current_user.id,
            ),
        )
        .where(StarredTrack.user_id == current_user.id)
        .order_by(Track.title)
    )
    starred_songs = []
    for starred, track, download in result.all():
        song = build_song_response(track, download)
        song["starred"] = format_subsonic_date(starred.created_at)
        starred_songs.append(song)

    return subsonic_response(
        {
            "starred": {
                "artist": starred_artists,
                "album": starred_albums,
                "song": starred_songs,
            }
        },
        f=f,
    )


@router.get("/getStarred2.view")
@router.post("/getStarred2.view")
async def get_starred2(
    music_folder_id: Annotated[str | None, Query(alias="musicFolderId", description=_MUSIC_FOLDER_ID_DESC)] = None,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get all starred items (ID3 format).

    Same as getStarred but with ID3 album format.
    """
    # Get starred items using JSON format internally for manipulation
    result = await get_starred(music_folder_id, "json", current_user, db)

    # Rename to starred2
    if "subsonic-response" in result and "starred" in result["subsonic-response"]:
        result["subsonic-response"]["starred2"] = result["subsonic-response"].pop("starred")

    # Return in requested format
    if f == "json":
        return result
    else:
        # Convert to XML
        from app.schemas.subsonic.base import subsonic_response as build_response

        return build_response(result["subsonic-response"], f=f)


@router.get("/setRating.view")
@router.post("/setRating.view")
async def set_rating(
    id: Annotated[str, Query(description="Song ID")],
    rating: Annotated[int, Query(description="Rating (0-5)")],
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Set rating for a song.

    Args:
        id: Song/track ID
        rating: Rating value 0-5 (0 = unrated)

    Returns:
        Empty success response
    """
    if rating < 0 or rating > 5:
        return subsonic_error(10, "Rating must be between 0 and 5", f=f)

    try:
        track_id = UUID(id)
    except ValueError:
        return subsonic_error(10, "Invalid song ID")

    # Get or create rating
    result = await db.execute(
        select(SubsonicRating).where(
            SubsonicRating.user_id == current_user.id,
            SubsonicRating.track_id == track_id,
        )
    )
    existing = result.scalar_one_or_none()

    if rating == 0:
        # Remove rating
        if existing:
            await db.delete(existing)
    elif existing:
        # Update rating
        existing.rating = rating
        existing.rated_at = datetime.now(UTC)
    else:
        # Create rating
        new_rating = SubsonicRating(
            user_id=current_user.id,
            track_id=track_id,
            rating=rating,
        )
        db.add(new_rating)

    await db.commit()
    return subsonic_response(f=f)


async def _record_submission(db, scrobbler_service, current_user, track_id, track_obj, time_ms):
    played_at = datetime.fromtimestamp(time_ms / 1000, tz=UTC) if time_ms else datetime.now(UTC)
    db.add(ListeningHistory(user_id=current_user.id, track_id=track_id, played_at=played_at, duration_played=None))
    if track_obj:
        try:
            await scrobbler_service.scrobble_track(
                user=current_user,
                track=track_obj.title,
                artist=track_obj.artist or "Unknown",
                album=track_obj.album,
                timestamp=int(played_at.timestamp()),
            )
        except Exception:  # nosec B110  # noqa: S110
            pass
    return played_at


@router.get("/scrobble.view")
@router.post("/scrobble.view")
async def scrobble(
    id: Annotated[str, Query(description="Song ID")],
    time: Annotated[int | None, Query(description="Time played (Unix timestamp in ms)")] = None,
    submission: Annotated[bool, Query(description="True for scrobble, false for now playing")] = True,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Record play/scrobble.

    Uses existing ListeningHistory model.

    Args:
        id: Song/track ID
        time: Timestamp when played (milliseconds)
        submission: True = full scrobble, False = now playing only

    Returns:
        Empty success response
    """
    from app.services.scrobbler import AudiovaultScrobbler

    scrobbler_service = await AudiovaultScrobbler.for_user(current_user, db)

    try:
        track_id = UUID(id)
    except ValueError:
        return subsonic_error(10, "Invalid song ID", f=f)

    # Fetch track details for Last.fm
    track_result = await db.execute(select(Track).where(Track.id == track_id))
    track_obj = track_result.scalar_one_or_none()

    # Clients (e.g. Amperfy) may scrobble a track id that is no longer in the
    # library. Both ListeningHistory and SubsonicNowPlaying have a FK to tracks,
    # so writing them would raise a ForeignKeyViolation (HTTP 500). Per Subsonic,
    # scrobbling an unknown id is a best-effort no-op that still returns ok.
    if track_obj is None:
        return subsonic_response(f=f)

    if submission:
        await _record_submission(db, scrobbler_service, current_user, track_id, track_obj, time)

    result = await db.execute(select(SubsonicNowPlaying).where(SubsonicNowPlaying.user_id == current_user.id))
    now_playing = result.scalar_one_or_none()
    if now_playing:
        now_playing.track_id = track_id
        now_playing.updated_at = datetime.now(UTC)
    else:
        db.add(SubsonicNowPlaying(user_id=current_user.id, track_id=track_id))

    if not submission and track_obj and track_obj.artist:
        try:
            await scrobbler_service.update_now_playing(
                user=current_user, track=track_obj.title, artist=track_obj.artist or "Unknown", album=track_obj.album
            )
        except Exception:  # nosec B110  # noqa: S110
            pass

    await db.commit()
    return subsonic_response(f=f)


@router.get("/getNowPlaying.view")
@router.post("/getNowPlaying.view")
async def get_now_playing(
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get currently playing tracks across all users.

    Returns entries updated in the last 5 minutes.
    """
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(minutes=5)

    result = await db.execute(
        select(SubsonicNowPlaying, Track, User, Download)
        .join(Track, Track.id == SubsonicNowPlaying.track_id)
        .join(User, User.id == SubsonicNowPlaying.user_id)
        .outerjoin(
            Download,
            and_(
                Download.track_id == Track.id,
                Download.user_id == SubsonicNowPlaying.user_id,
            ),
        )
        .where(SubsonicNowPlaying.updated_at >= cutoff)
        .order_by(SubsonicNowPlaying.updated_at.desc())
    )

    entries = []
    now = datetime.now(UTC)
    for now_playing, track, user, download in result.all():
        song = build_song_response(track, download)
        song["username"] = user.username

        # Ensure now_playing.updated_at is aware for subtraction
        updated_at = now_playing.updated_at
        if updated_at and updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)

        song["minutesAgo"] = int((now - updated_at).total_seconds() / 60)
        song["playerId"] = now_playing.player_id or "0"
        entries.append(song)

    return subsonic_response({"nowPlaying": {"entry": entries}}, f=f)


@router.get("/getRandomSongs.view")
@router.post("/getRandomSongs.view")
async def get_random_songs(
    size: Annotated[int, Query(description="Number of songs")] = 10,
    genre: Annotated[str | None, Query(description="Filter by genre")] = None,
    from_year: Annotated[int | None, Query(alias="fromYear", description="Filter from year")] = None,
    to_year: Annotated[int | None, Query(alias="toYear", description="Filter to year")] = None,
    music_folder_id: Annotated[str | None, Query(alias="musicFolderId", description=_MUSIC_FOLDER_ID_DESC)] = None,
    f: Annotated[str, Query(description=_RESPONSE_FORMAT)] = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get random songs.

    Args:
        size: Number of songs to return (max 500)
        genre: Filter by genre
        fromYear: Filter from year
        toYear: Filter to year

    Returns:
        Random song list
    """
    from sqlalchemy import func as sqlfunc

    size = min(size, 500)

    query = (
        select(Track, Download)
        .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
        .where(
            # Download.user_id == current_user.id,
        )
    )

    from sqlalchemy import Integer

    is_postgres = db.bind.dialect.name == "postgresql" if hasattr(db.bind, "dialect") else True

    # Apply filters
    if from_year:
        if is_postgres:
            query = query.where(Track.metadata_content["year"].astext.cast(Integer) >= from_year)
        else:
            query = query.where(
                sqlfunc.cast(sqlfunc.json_extract(Track.metadata_content, "$.year"), Integer) >= from_year
            )
    if to_year:
        if is_postgres:
            query = query.where(Track.metadata_content["year"].astext.cast(Integer) <= to_year)
        else:
            query = query.where(
                sqlfunc.cast(sqlfunc.json_extract(Track.metadata_content, "$.year"), Integer) <= to_year
            )

    # Random order
    query = query.order_by(sqlfunc.random()).limit(size)

    result = await db.execute(query)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi

    songs = []
    for track, download in result.all():
        songs.append(build_song_response(track, download))

    return subsonic_response({"randomSongs": {"song": songs}}, f=f)
