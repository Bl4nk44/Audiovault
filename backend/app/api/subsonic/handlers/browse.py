"""
Browse handlers for Subsonic API.

Handles library browsing endpoints:
- getMusicFolders.view
- getIndexes.view
- getArtists.view
- getArtist.view
- getAlbum.view
- getSong.view
- getMusicDirectory.view
"""

from typing import Annotated
from uuid import UUID

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
from app.schemas.subsonic.base import subsonic_error, subsonic_response
from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/getMusicFolders.view")
@router.post("/getMusicFolders.view")
async def get_music_folders(
    f: str = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get list of music folders.

    In Audiovault, we have a single virtual folder containing all music.

    Returns:
        List of music folders (single "Music Library" folder)
    """
    return subsonic_response({"musicFolders": {"musicFolder": [{"id": "1", "name": "Music Library"}]}}, f=f)


@router.get("/getIndexes.view")
@router.post("/getIndexes.view")
async def get_indexes(
    music_folder_id: Annotated[str, Query(alias="musicFolderId", description="Music folder ID")] = "1",
    if_modified_since: Annotated[int, Query(alias="ifModifiedSince", description="Return if modified after this timestamp")] = 0,
    f: str = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get indexed list of all artists.

    Groups artists alphabetically (A-Z, #).

    Args:
        musicFolderId: Folder ID (ignored, we have one folder)
        ifModifiedSince: Timestamp for incremental updates

    Returns:
        Alphabetical index of artists
    """
    # Get all artists with at least one track with completed download for this user
    artists_res = await db.execute(
        select(Artist)
        .join(Track, Track.artist_id == Artist.id)
        .join(Download, Download.track_id == Track.id)
        .where(
            Download.user_id == current_user.id,
            Download.status == "completed",
        )
        .group_by(Artist.id)
        .order_by(Artist.name)
    )
    artists = artists_res.scalars().all()

    # Group by first letter
    indexes: dict[str, list] = {}

    for artist in artists:
        if not artist.name:
            continue

        first_char = artist.name[0].upper()

        # Group non-letter characters under #
        if not first_char.isalpha():
            first_char = "#"

        if first_char not in indexes:
            indexes[first_char] = []

        # Count albums for this artist
        album_result = await db.execute(select(func.count(distinct(Album.id))).where(Album.artist_id == artist.id))
        album_count = album_result.scalar() or 0

        indexes[first_char].append(
            {
                "id": str(artist.id),
                "name": artist.name,
                "albumCount": album_count,
                "coverArt": f"ar-{artist.id}",
            }
        )

    # Build index list
    index_list = []
    for letter in sorted(indexes.keys()):
        index_list.append(
            {
                "name": letter,
                "artist": indexes[letter],
            }
        )

    return subsonic_response(
        {
            "indexes": {
                "lastModified": 0,
                "ignoredArticles": "The El La Los Las Le Les",
                "index": index_list,
            }
        },
        f=f,
    )


@router.get("/getArtists.view")
@router.post("/getArtists.view")
async def get_artists(
    music_folder_id: Annotated[str | None, Query(alias="musicFolderId", description="Music folder ID")] = None,
    f: str = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get all artists (similar to getIndexes but for ID3 view).

    Returns:
        Alphabetical index of artists (ID3 format)
    """
    # Reuse getIndexes logic
    artists_id3_res = await db.execute(
        select(Artist)
        .join(Track, Track.artist_id == Artist.id)
        .join(Download, Download.track_id == Track.id)
        .where(
            Download.user_id == current_user.id,
            Download.status == "completed",
        )
        .group_by(Artist.id)
        .order_by(Artist.name)
    )
    artists = artists_id3_res.scalars().all()

    # Group by first letter
    indexes: dict[str, list] = {}

    for artist in artists:
        if not artist.name:
            continue

        first_char = artist.name[0].upper()
        if not first_char.isalpha():
            first_char = "#"

        if first_char not in indexes:
            indexes[first_char] = []

        album_result = await db.execute(select(func.count(distinct(Album.id))).where(Album.artist_id == artist.id))
        album_count = album_result.scalar() or 0

        indexes[first_char].append(
            {
                "id": str(artist.id),
                "name": artist.name,
                "albumCount": album_count,
                "coverArt": f"ar-{artist.id}",
            }
        )

    index_list = []
    for letter in sorted(indexes.keys()):
        index_list.append(
            {
                "name": letter,
                "artist": indexes[letter],
            }
        )

    return subsonic_response(
        {
            "artists": {
                "ignoredArticles": "The El La Los Las Le Les",
                "index": index_list,
            }
        },
        f=f,
    )


@router.get("/getArtist.view")
@router.post("/getArtist.view")
async def get_artist(
    id: str = Query(..., description="Artist ID"),
    f: str = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get artist details including albums.

    Args:
        id: Artist ID (UUID)

    Returns:
        Artist info with list of albums
    """
    try:
        artist_id = UUID(id)
    except ValueError:
        return subsonic_error(10, "Invalid artist ID", f=f)

    # Get artist
    artist_result = await db.execute(select(Artist).where(Artist.id == artist_id))
    artist = artist_result.scalar_one_or_none()

    if not artist:
        return subsonic_error(70, "Artist not found", f=f)

    # Get albums for this artist that user has downloaded tracks from
    albums_result = await db.execute(
        select(Album)
        .join(Track, Track.album_id == Album.id)
        .join(Download, Download.track_id == Track.id)
        .where(
            Album.artist_id == artist_id,
            Download.user_id == current_user.id,
            Download.status == "completed",
        )
        .group_by(Album.id)
        .order_by(Album.release_date.desc().nullslast(), Album.title)
    )
    albums = albums_result.scalars().all()

    # Build album list
    album_list = []
    for album in albums:
        # Count songs in album
        song_result = await db.execute(
            select(func.count(Track.id))
            .join(Download, Download.track_id == Track.id)
            .where(
                Track.album_id == album.id,
                Download.user_id == current_user.id,
                Download.status == "completed",
            )
        )
        song_count = song_result.scalar() or 0

        # Sum duration
        duration_result = await db.execute(
            select(func.sum(Track.duration_ms))
            .join(Download, Download.track_id == Track.id)
            .where(
                Track.album_id == album.id,
                Download.user_id == current_user.id,
                Download.status == "completed",
            )
        )
        total_duration = duration_result.scalar() or 0

        album_list.append(
            {
                "id": str(album.id),
                "name": album.title,
                "artist": artist.name,
                "artistId": str(artist.id),
                "coverArt": f"al-{album.id}",
                "songCount": song_count,
                "duration": format_duration(total_duration),
                "created": format_subsonic_date(album.created_at),
                "year": int(album.release_date[:4]) if album.release_date and len(album.release_date) >= 4 else None,
            }
        )

    artist_images = artist.images or {}

    return subsonic_response(
        {
            "artist": {
                "id": str(artist.id),
                "name": artist.name,
                "coverArt": f"ar-{artist.id}" if artist_images else None,
                "albumCount": len(album_list),
                "album": album_list,
            }
        },
        f=f,
    )


@router.get("/getAlbum.view")
@router.post("/getAlbum.view")
async def get_album(
    id: str = Query(..., description="Album ID"),
    f: str = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get album details including songs.

    Args:
        id: Album ID (UUID)

    Returns:
        Album info with list of songs
    """
    try:
        album_id = UUID(id)
    except ValueError:
        return subsonic_error(10, "Invalid album ID", f=f)

    # Get album with artist
    result = await db.execute(select(Album).where(Album.id == album_id))
    album = result.scalar_one_or_none()

    if not album:
        return subsonic_error(70, "Album not found", f=f)

    # Get artist name
    artist_name = "Unknown Artist"
    if album.artist_id:
        artist_result = await db.execute(select(Artist).where(Artist.id == album.artist_id))
        artist = artist_result.scalar_one_or_none()
        if artist:
            artist_name = artist.name

    # Get tracks with downloads for this user (only completed downloads)
    tracks_res = await db.execute(
        select(Track, Download)
        .join(Download, Download.track_id == Track.id)
        .where(
            Track.album_id == album_id,
            Download.user_id == current_user.id,
            Download.status == "completed",
        )
        .order_by(Track.title)
    )
    track_downloads = tracks_res.all()

    # Build song list
    song_list = []
    total_duration = 0

    for i, (track, download) in enumerate(track_downloads):
        song = build_song_response(track, download)
        song["parent"] = str(album.id)
        song["albumId"] = str(album.id)
        song["artistId"] = str(album.artist_id) if album.artist_id else None

        # Ensure track number exists (fallback to index + 1)
        if "track" not in song:
            song["track"] = i + 1

        song_list.append(song)
        total_duration += track.duration_ms or 0

    return subsonic_response(
        {
            "album": {
                "id": str(album.id),
                "name": album.title,
                "artist": artist_name,
                "artistId": str(album.artist_id) if album.artist_id else None,
                "coverArt": f"al-{album.id}",
                "songCount": len(song_list),
                "duration": format_duration(total_duration),
                "created": format_subsonic_date(album.created_at),
                "year": int(album.release_date[:4]) if album.release_date and len(album.release_date) >= 4 else None,
                "song": song_list,
            }
        },
        f=f,
    )


@router.get("/getSong.view")
@router.post("/getSong.view")
async def get_song(
    id: str = Query(..., description="Song ID"),
    f: str = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get song metadata.

    Args:
        id: Song/Track ID (UUID)

    Returns:
        Song metadata
    """
    try:
        track_id = UUID(id)
    except ValueError:
        return subsonic_error(10, "Invalid song ID", f=f)

    # Get track with download (only if downloaded)
    song_res = await db.execute(
        select(Track, Download)
        .join(Download, Download.track_id == Track.id)
        .where(
            Track.id == track_id,
            Download.user_id == current_user.id,
            Download.status == "completed",
        )
    )
    song_row = song_res.first()

    if not song_row:
        return subsonic_error(70, "Song not found", f=f)

    track, download = song_row
    song = build_song_response(track, download)

    return subsonic_response({"song": song}, f=f)


@router.get("/getMusicDirectory.view")
@router.post("/getMusicDirectory.view")
async def get_music_directory(
    id: str = Query(..., description="Directory ID"),
    f: str = "xml",
    current_user: Annotated[User, Depends(subsonic_auth)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    """
    Get contents of a music directory.

    Directory can be:
    - "1" = root (list artists)
    - Artist ID = list albums
    - Album ID = list songs

    Args:
        id: Directory ID

    Returns:
        Directory contents
    """
    # Root folder - list artists
    if id == "1":
        root_artists_res = await db.execute(
            select(Artist)
            .join(Track, Track.artist_id == Artist.id)
            .outerjoin(Download, (Download.track_id == Track.id) & (Download.user_id == current_user.id))
            .where(
                # No condition needed if we just want all artists?
                # Wait, original was removing artists with no downloads?
                # Yes. This change effectively makes all artists visible.
            )
            .group_by(Artist.id)
            .order_by(Artist.name)
        )
        artists = root_artists_res.scalars().all()

        children = []
        for artist in artists:
            children.append(
                {
                    "id": str(artist.id),
                    "title": artist.name,
                    "artist": artist.name,
                    "isDir": True,
                    "coverArt": f"ar-{artist.id}" if artist.images else None,
                }
            )

        return subsonic_response(
            {
                "directory": {
                    "id": "1",
                    "name": "Music Library",
                    "child": children,
                }
            },
            f=f,
        )

    # Try as artist ID
    try:
        item_id = UUID(id)
    except ValueError:
        return subsonic_error(70, "Directory not found", f=f)

    # Check if it's an artist
    item_artist_result = await db.execute(select(Artist).where(Artist.id == item_id))
    artist_item = item_artist_result.scalar_one_or_none()

    if artist_item:
        # List albums for this artist (only with downloaded tracks)
        result = await db.execute(
            select(Album)
            .join(Track, Track.album_id == Album.id)
            .join(Download, Download.track_id == Track.id)
            .where(
                Album.artist_id == artist_item.id,
                Download.user_id == current_user.id,
                Download.status == "completed",
            )
            .group_by(Album.id)
            .order_by(Album.release_date.desc().nullslast())
        )
        albums = result.scalars().all()

        children = []
        for album in albums:
            # Count songs (only downloaded)
            song_result = await db.execute(
                select(func.count(Track.id))
                .join(Download, Download.track_id == Track.id)
                .where(
                    Track.album_id == album.id,
                    Download.user_id == current_user.id,
                    Download.status == "completed",
                )
            )
            song_count = song_result.scalar() or 0

            children.append(
                {
                    "id": str(album.id),
                    "parent": str(artist_item.id),
                    "title": album.title,
                    "artist": artist_item.name,
                    "isDir": True,
                    "coverArt": f"al-{album.id}",
                    "songCount": song_count,
                    "year": int(album.release_date[:4])
                    if album.release_date and len(album.release_date) >= 4
                    else None,
                }
            )

        return subsonic_response(
            {
                "directory": {
                    "id": str(artist_item.id),
                    "parent": "1",
                    "name": artist_item.name,
                    "child": children,
                }
            },
            f=f,
        )

    # Check if it's an album
    item_album_result = await db.execute(select(Album).where(Album.id == item_id))
    album_item = item_album_result.scalar_one_or_none()

    if album_item:
        # Get artist name
        artist_name = "Unknown Artist"
        parent_id = "1"
        if album_item.artist_id:
            artist_result = await db.execute(select(Artist).where(Artist.id == album_item.artist_id))
            artist_obj = artist_result.scalar_one_or_none()
            if artist_obj:
                artist_name = artist_obj.name
                parent_id = str(artist_obj.id)

        # List tracks (only downloaded)
        result = await db.execute(
            select(Track, Download)
            .join(Download, Download.track_id == Track.id)
            .where(
                Track.album_id == album_item.id,
                Download.user_id == current_user.id,
                Download.status == "completed",
            )
            .order_by(Track.title)
        )
        track_downloads = result.all()

        children = []
        for track, download in track_downloads:
            song = build_song_response(track, download)
            song["parent"] = str(album_item.id)
            children.append(song)

        return subsonic_response(
            {
                "directory": {
                    "id": str(album_item.id),
                    "parent": parent_id,
                    "name": album_item.title,
                    "artist": artist_name,
                    "coverArt": f"al-{album_item.id}",
                    "child": children,
                }
            },
            f=f,
        )

    return subsonic_error(70, "Directory not found", f=f)
