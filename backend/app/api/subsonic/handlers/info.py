"""
Info handlers for Subsonic API.

Handles info/metadata endpoints:
- getArtistInfo.view / getArtistInfo2.view
- getSimilarSongs2.view
- getPodcasts.view
"""

from typing import Any
from uuid import UUID

from app.api.subsonic.auth import subsonic_auth
from app.api.subsonic.utils import build_song_response
from app.db.database import get_db
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from app.models.user import User
from app.schemas.subsonic.base import subsonic_error, subsonic_response
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/getArtistInfo.view")
@router.post("/getArtistInfo.view")
async def get_artist_info(
    id: str = Query(..., description="Artist ID"),
    count: int = Query(20, description="Max similar artists"),
    include_not_present: bool = Query(False, alias="includeNotPresent", description="Include non-present artists"),
    f: str = Query("xml", description="Response format"),
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get metadata for an artist (folder view format).

    Returns basic artist info. Similar artists not implemented.
    """
    try:
        artist_id = UUID(id)
    except ValueError:
        return subsonic_error(10, "Invalid artist ID", f=f)

    result = await db.execute(select(Artist).where(Artist.id == artist_id))
    artist = result.scalar_one_or_none()

    if not artist:
        return subsonic_error(70, "Artist not found", f=f)

    # Build artist info response
    artist_info: dict[str, Any] = {
        "biography": artist.bio or "",
        "musicBrainzId": None,
        "lastFmUrl": "",  # Not implemented
        "smallImageUrl": f"/api/subsonic/getCoverArt.view?id=ar-{artist.id}&size=64" if artist.images else None,
        "mediumImageUrl": f"/api/subsonic/getCoverArt.view?id=ar-{artist.id}&size=126" if artist.images else None,
        "largeImageUrl": f"/api/subsonic/getCoverArt.view?id=ar-{artist.id}&size=300" if artist.images else None,
        "similarArtist": [],  # Not implemented
    }

    # Remove None values for cleaner XML
    artist_info = {k: v for k, v in artist_info.items() if v is not None}

    return subsonic_response({"artistInfo": artist_info}, f=f)


@router.get("/getArtistInfo2.view")
@router.post("/getArtistInfo2.view")
async def get_artist_info2(
    id: str = Query(..., description="Artist ID"),
    count: int = Query(20, description="Max similar artists"),
    include_not_present: bool = Query(False, alias="includeNotPresent", description="Include non-present artists"),
    f: str = Query("xml", description="Response format"),
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get metadata for an artist (ID3 format).

    Same as getArtistInfo but with ID3 naming.
    """
    try:
        artist_id = UUID(id)
    except ValueError:
        return subsonic_error(10, "Invalid artist ID", f=f)

    result = await db.execute(select(Artist).where(Artist.id == artist_id))
    artist = result.scalar_one_or_none()

    if not artist:
        return subsonic_error(70, "Artist not found", f=f)

    # Build artist info response
    artist_info: dict[str, Any] = {
        "biography": artist.bio or "",
        "musicBrainzId": None,
        "lastFmUrl": "",  # Not implemented
        "smallImageUrl": f"/api/subsonic/getCoverArt.view?id=ar-{artist.id}&size=64" if artist.images else None,
        "mediumImageUrl": f"/api/subsonic/getCoverArt.view?id=ar-{artist.id}&size=126" if artist.images else None,
        "largeImageUrl": f"/api/subsonic/getCoverArt.view?id=ar-{artist.id}&size=300" if artist.images else None,
        "similarArtist": [],  # Not implemented
    }

    # Remove None values for cleaner XML
    artist_info = {k: v for k, v in artist_info.items() if v is not None}

    return subsonic_response({"artistInfo2": artist_info}, f=f)


@router.get("/getSimilarSongs2.view")
@router.post("/getSimilarSongs2.view")
async def get_similar_songs2(
    id: str = Query(..., description="Song or Artist ID"),
    count: int = Query(50, description="Number of songs"),
    f: str = Query("xml", description="Response format"),
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get similar songs (ID3 format).

    Returns songs from the same artist as the given song/artist.
    """
    try:
        item_id = UUID(id)
    except ValueError:
        return subsonic_error(10, "Invalid ID", f=f)

    # Try to find as track first
    result = await db.execute(select(Track).where(Track.id == item_id))
    track = result.scalar_one_or_none()

    artist_id = None
    if track:
        artist_id = track.artist_id
    else:
        # Try as artist ID
        result = await db.execute(select(Artist).where(Artist.id == item_id))
        artist = result.scalar_one_or_none()
        if artist:
            artist_id = artist.id

    if not artist_id:
        return subsonic_error(70, "Song or artist not found", f=f)

    # Get songs by the same artist (only downloaded ones)
    result = await db.execute(
        select(Track, Download)  # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
        .join(Download, Download.track_id == Track.id)
        .where(
            Track.artist_id == artist_id,
            Download.user_id == current_user.id,
        )
        .limit(count)
    )

    songs = []
    for t, d in result.all():
        songs.append(build_song_response(t, d))

    return subsonic_response({"similarSongs2": {"song": songs}}, f=f)


@router.get("/getPodcasts.view")
@router.post("/getPodcasts.view")
async def get_podcasts(
    include_episodes: bool = Query(True, alias="includeEpisodes", description="Include episodes"),
    id: str = Query(None, description="Podcast ID"),
    f: str = Query("xml", description="Response format"),
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all podcasts.

    Returns empty list as podcasts are not implemented.
    """
    return subsonic_response({"podcasts": {"channel": []}}, f=f)


@router.get("/getNewestPodcasts.view")
@router.post("/getNewestPodcasts.view")
async def get_newest_podcasts(
    count: int = Query(20, description="Count"),
    f: str = Query("xml", description="Response format"),
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get newest podcast episodes.

    Returns empty list as podcasts are not implemented.
    """
    return subsonic_response({"newestPodcasts": {"episode": []}}, f=f)


@router.get("/getBookmarks.view")
@router.post("/getBookmarks.view")
async def get_bookmarks(
    f: str = Query("xml", description="Response format"),
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all bookmarks.

    Returns empty list as bookmarks are not implemented.
    """
    return subsonic_response({"bookmarks": {"bookmark": []}}, f=f)


@router.get("/getInternetRadioStations.view")
@router.post("/getInternetRadioStations.view")
async def get_internet_radio_stations(
    f: str = Query("xml", description="Response format"),
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all internet radio stations.

    Returns empty list as radio is not implemented.
    """
    return subsonic_response({"internetRadioStations": {"internetRadioStation": []}}, f=f)
