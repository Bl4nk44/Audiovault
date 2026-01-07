"""
Search handlers for Subsonic API.

Handles search endpoints:
- search2.view (API 1.4+)
- search3.view (API 1.8+)
"""


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


@router.get("/search.view")
@router.post("/search.view")
async def search_legacy(
    artist: str = Query(None, description="Artist to search"),
    album: str = Query(None, description="Album to search"),
    title: str = Query(None, description="Song title to search"),
    any: str = Query(None, description="Search any field"),
    count: int = Query(20, description="Max results"),
    offset: int = Query(0, description="Result offset"),
    newerThan: int = Query(None, description="Only return newer than timestamp"),
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Legacy search (API 1.0).
    
    Searches for songs matching criteria.
    Deprecated in favor of search2/search3.
    """
    # Build search query
    query_text = any or title or album or artist or ""
    
    if not query_text:
        return subsonic_response({
            "searchResult": {
                "match": []
            }
        })
    
    # Search tracks
    search_term = f"%{query_text.lower()}%"
    
    result = await db.execute(
        select(Track, Download)
        .join(Download, Download.track_id == Track.id)
        .where(
            Download.user_id == current_user.id,
            Download.status == "completed",
            or_(
                func.lower(Track.title).like(search_term),
                func.lower(Track.artist).like(search_term),
                func.lower(Track.album).like(search_term),
            )
        )
        .offset(offset)
        .limit(count)
    )
    track_downloads = result.all()
    
    matches = []
    for track, download in track_downloads:
        matches.append(build_song_response(track, download))
    
    return subsonic_response({
        "searchResult": {
            "match": matches
        }
    })


@router.get("/search2.view")
@router.post("/search2.view")
async def search2(
    query: str = Query(..., description="Search query"),
    artistCount: int = Query(20, description="Max artists to return"),
    artistOffset: int = Query(0, description="Artist offset"),
    albumCount: int = Query(20, description="Max albums to return"),
    albumOffset: int = Query(0, description="Album offset"),
    songCount: int = Query(20, description="Max songs to return"),
    songOffset: int = Query(0, description="Song offset"),
    musicFolderId: str = Query(None, description="Music folder ID"),
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
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
    if artistCount > 0:
        result = await db.execute(
            select(Artist)
            .join(Track, Track.artist_id == Artist.id)
            .join(Download, Download.track_id == Track.id)
            .where(
                Download.user_id == current_user.id,
                Download.status == "completed",
                func.lower(Artist.name).like(search_term),
            )
            .group_by(Artist.id)
            .order_by(Artist.name)
            .offset(artistOffset)
            .limit(artistCount)
        )
        
        for artist in result.scalars():
            # Count albums
            album_result = await db.execute(
                select(func.count(Album.id.distinct()))
                .where(Album.artist_id == artist.id)
            )
            album_count = album_result.scalar() or 0
            
            artists_result.append({
                "id": str(artist.id),
                "name": artist.name,
                "albumCount": album_count,
                "coverArt": f"ar-{artist.id}" if artist.images else None,
            })
    
    # Search albums
    albums_result = []
    if albumCount > 0:
        result = await db.execute(
            select(Album)
            .join(Track, Track.album_id == Album.id)
            .join(Download, Download.track_id == Track.id)
            .where(
                Download.user_id == current_user.id,
                Download.status == "completed",
                func.lower(Album.title).like(search_term),
            )
            .group_by(Album.id)
            .order_by(Album.title)
            .offset(albumOffset)
            .limit(albumCount)
        )
        
        for album in result.scalars():
            # Get artist name
            artist_name = "Unknown Artist"
            if album.artist_id:
                artist_result = await db.execute(
                    select(Artist.name).where(Artist.id == album.artist_id)
                )
                name = artist_result.scalar()
                if name:
                    artist_name = name
            
            # Count songs
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
            
            albums_result.append({
                "id": str(album.id),
                "parent": str(album.artist_id) if album.artist_id else "1",
                "title": album.title,
                "artist": artist_name,
                "isDir": True,
                "coverArt": f"al-{album.id}",
                "songCount": song_count,
                "year": int(album.release_date[:4]) if album.release_date and len(album.release_date) >= 4 else None,
            })
    
    # Search songs
    songs_result = []
    if songCount > 0:
        result = await db.execute(
            select(Track, Download)
            .join(Download, Download.track_id == Track.id)
            .where(
                Download.user_id == current_user.id,
                Download.status == "completed",
                or_(
                    func.lower(Track.title).like(search_term),
                    func.lower(Track.artist).like(search_term),
                    func.lower(Track.album).like(search_term),
                )
            )
            .offset(songOffset)
            .limit(songCount)
        )
        
        for track, download in result.all():
            song = build_song_response(track, download)
            song["parent"] = str(track.album_id) if track.album_id else "1"
            songs_result.append(song)
    
    return subsonic_response({
        "searchResult2": {
            "artist": artists_result,
            "album": albums_result,
            "song": songs_result,
        }
    })


@router.get("/search3.view")
@router.post("/search3.view")
async def search3(
    query: str = Query(..., description="Search query"),
    artistCount: int = Query(20, description="Max artists to return"),
    artistOffset: int = Query(0, description="Artist offset"),
    albumCount: int = Query(20, description="Max albums to return"),
    albumOffset: int = Query(0, description="Album offset"),
    songCount: int = Query(20, description="Max songs to return"),
    songOffset: int = Query(0, description="Song offset"),
    musicFolderId: str = Query(None, description="Music folder ID"),
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
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
    if artistCount > 0:
        result = await db.execute(
            select(Artist)
            .join(Track, Track.artist_id == Artist.id)
            .join(Download, Download.track_id == Track.id)
            .where(
                Download.user_id == current_user.id,
                Download.status == "completed",
                func.lower(Artist.name).like(search_term),
            )
            .group_by(Artist.id)
            .order_by(Artist.name)
            .offset(artistOffset)
            .limit(artistCount)
        )
        
        for artist in result.scalars():
            album_result = await db.execute(
                select(func.count(Album.id.distinct()))
                .where(Album.artist_id == artist.id)
            )
            album_count = album_result.scalar() or 0
            
            artists_result.append({
                "id": str(artist.id),
                "name": artist.name,
                "albumCount": album_count,
                "coverArt": f"ar-{artist.id}" if artist.images else None,
            })
    
    # Search albums (ID3 format)
    albums_result = []
    if albumCount > 0:
        result = await db.execute(
            select(Album)
            .join(Track, Track.album_id == Album.id)
            .join(Download, Download.track_id == Track.id)
            .where(
                Download.user_id == current_user.id,
                Download.status == "completed",
                func.lower(Album.title).like(search_term),
            )
            .group_by(Album.id)
            .order_by(Album.title)
            .offset(albumOffset)
            .limit(albumCount)
        )
        
        for album in result.scalars():
            artist_name = "Unknown Artist"
            if album.artist_id:
                artist_result = await db.execute(
                    select(Artist.name).where(Artist.id == album.artist_id)
                )
                name = artist_result.scalar()
                if name:
                    artist_name = name
            
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
            
            albums_result.append({
                "id": str(album.id),
                "name": album.title,
                "artist": artist_name,
                "artistId": str(album.artist_id) if album.artist_id else None,
                "coverArt": f"al-{album.id}",
                "songCount": song_count,
                "duration": format_duration(total_duration),
                "created": format_subsonic_date(album.created_at),
                "year": int(album.release_date[:4]) if album.release_date and len(album.release_date) >= 4 else None,
            })
    
    # Search songs (same as search2)
    songs_result = []
    if songCount > 0:
        result = await db.execute(
            select(Track, Download)
            .join(Download, Download.track_id == Track.id)
            .where(
                Download.user_id == current_user.id,
                Download.status == "completed",
                or_(
                    func.lower(Track.title).like(search_term),
                    func.lower(Track.artist).like(search_term),
                    func.lower(Track.album).like(search_term),
                )
            )
            .offset(songOffset)
            .limit(songCount)
        )
        
        for track, download in result.all():
            songs_result.append(build_song_response(track, download))
    
    return subsonic_response({
        "searchResult3": {
            "artist": artists_result,
            "album": albums_result,
            "song": songs_result,
        }
    })
