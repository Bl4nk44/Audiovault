"""
Playlist handlers for Subsonic API.

Handles playlist CRUD operations:
- getPlaylists.view
- getPlaylist.view
- createPlaylist.view
- updatePlaylist.view
- deletePlaylist.view
"""

from datetime import UTC, datetime
from uuid import UUID

from app.api.subsonic.auth import subsonic_auth
from app.api.subsonic.utils import (
    build_song_response,
    format_duration,
    format_subsonic_date,
)
from app.db.database import get_db
from app.models.download import Download
from app.models.playlist import Playlist, PlaylistTrack
from app.models.track import Track
from app.models.user import User
from app.schemas.subsonic.base import subsonic_error, subsonic_response
from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

# Error message constants
ERR_INVALID_PLAYLIST_ID = "Invalid playlist ID"
ERR_PLAYLIST_NOT_FOUND = "Playlist not found"
ERR_ACCESS_DENIED = "Access denied"


@router.get("/getPlaylists.view")
@router.post("/getPlaylists.view")
async def get_playlists(
    username: str = Query(None, description="Get playlists for specific user"),
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all playlists.

    Returns playlists owned by current user plus public playlists.

    Args:
        username: Optional username to filter (admin only)

    Returns:
        List of playlists
    """
    # Get playlists (own + public)
    result = await db.execute(
        select(Playlist).where((Playlist.owner_id == current_user.id) | (Playlist.public)).order_by(Playlist.name)
    )
    playlists = result.scalars().all()

    playlist_list = []
    for pl in playlists:
        # Count songs and total duration
        track_result = await db.execute(
            select(func.count(PlaylistTrack.track_id), func.sum(Track.duration_ms))
            .select_from(PlaylistTrack)
            .join(Track, Track.id == PlaylistTrack.track_id)
            .where(PlaylistTrack.playlist_id == pl.id)
        )
        row = track_result.first()
        song_count = row[0] or 0
        total_duration = row[1] or 0

        # Get owner username
        owner_result = await db.execute(select(User.username).where(User.id == pl.owner_id))
        owner_name = owner_result.scalar() or "unknown"

        playlist_list.append(
            {
                "id": str(pl.id),
                "name": pl.name,
                "comment": pl.comment or "",
                "owner": owner_name,
                "public": pl.public,
                "songCount": song_count,
                "duration": format_duration(total_duration),
                "created": format_subsonic_date(pl.created_at),
                "changed": format_subsonic_date(pl.updated_at),
                "coverArt": f"pl-{pl.id}",  # Use new pl- supported prefix
            }
        )

    return subsonic_response({"playlists": {"playlist": playlist_list}}, f=f)


@router.get("/getPlaylist.view")
@router.post("/getPlaylist.view")
async def get_playlist(
    id: str = Query(..., description="Playlist ID"),
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get playlist details including all tracks.

    Args:
        id: Playlist ID

    Returns:
        Playlist with track list
    """
    try:
        playlist_id = UUID(id)
    except ValueError:
        return subsonic_error(10, ERR_INVALID_PLAYLIST_ID)

    # Get playlist
    result = await db.execute(select(Playlist).where(Playlist.id == playlist_id))
    playlist = result.scalar_one_or_none()

    if not playlist:
        return subsonic_error(70, ERR_PLAYLIST_NOT_FOUND)

    # Check access
    if playlist.owner_id != current_user.id and not playlist.public:
        return subsonic_error(50, ERR_ACCESS_DENIED, f=f)

    # Get tracks with downloads
    stmt = (
        select(PlaylistTrack, Track, Download)
        .join(Track, Track.id == PlaylistTrack.track_id)
        .outerjoin(
            Download,
            (Download.track_id == Track.id) & (Download.user_id == current_user.id) & (Download.status == "completed"),
        )
        .where(PlaylistTrack.playlist_id == playlist_id)
        .order_by(PlaylistTrack.order)
    )
    result = await db.execute(stmt)
    entries = result.all()
    
    # DEBUG LOGGING
    import logging
    logger = logging.getLogger("app.api.subsonic.handlers.playlist")
    logger.info(f"getPlaylist: ID={playlist_id}, entries_found={len(entries)}")
    if len(entries) == 0:
        # Check if any tracks exist at all for this playlist (raw check)
        raw_count = await db.execute(select(func.count(PlaylistTrack.track_id)).where(PlaylistTrack.playlist_id == playlist_id))
        logger.info(f"getPlaylist: Raw PlaylistTrack count={raw_count.scalar()}")


    song_list = []
    total_duration = 0

    for _playlist_track, track, download in entries:
        song = build_song_response(track, download)
        song_list.append(song)
        total_duration += track.duration_ms or 0

    # Get owner username
    owner_result = await db.execute(select(User.username).where(User.id == playlist.owner_id))
    owner_name = owner_result.scalar() or "unknown"

    return subsonic_response(
        {
            "playlist": {
                "id": str(playlist.id),
                "name": playlist.name,
                "comment": playlist.comment or "",
                "owner": owner_name,
                "public": playlist.public,
                "songCount": len(song_list),
                "duration": format_duration(total_duration),
                "created": format_subsonic_date(playlist.created_at),
                "changed": format_subsonic_date(playlist.updated_at),
                "entry": song_list,
            }
        },
        f=f,
    )


@router.get("/createPlaylist.view")
@router.post("/createPlaylist.view")
async def create_playlist(
    playlistId: str = Query(None, description="Playlist ID (for update)"),
    name: str = Query(None, description="Playlist name"),
    songId: list[str] = Query(None, description="Song IDs to add"),
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Create or update playlist.

    If playlistId is provided, updates existing playlist.
    Otherwise creates new playlist.

    Args:
        playlistId: Existing playlist ID (for update)
        name: Playlist name
        songId: List of song IDs to add

    Returns:
        Created/updated playlist
    """
    if playlistId:
        # Update existing playlist
        try:
            playlist_id = UUID(playlistId)
        except ValueError:
            return subsonic_error(10, ERR_INVALID_PLAYLIST_ID, f=f)

        result = await db.execute(select(Playlist).where(Playlist.id == playlist_id))
        playlist = result.scalar_one_or_none()

        if not playlist:
            return subsonic_error(70, ERR_PLAYLIST_NOT_FOUND, f=f)

        if playlist.owner_id != current_user.id:
            return subsonic_error(50, ERR_ACCESS_DENIED, f=f)

        # Update name if provided
        if name:
            playlist.name = name

        # Replace songs if provided
        if songId:
            # Delete existing tracks
            await db.execute(delete(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id))

            # Add new tracks
            for i, song_id in enumerate(songId):
                try:
                    track_id = UUID(song_id)
                    playlist_track = PlaylistTrack(
                        playlist_id=playlist_id,
                        track_id=track_id,
                        order=i,
                    )
                    db.add(playlist_track)
                except ValueError:
                    continue

        playlist.updated_at = datetime.now(UTC)
        await db.commit()

    else:
        # Create new playlist
        if not name:
            return subsonic_error(10, "Playlist name is required", f=f)

        playlist = Playlist(
            name=name,
            owner_id=current_user.id,
            public=False,
        )
        db.add(playlist)
        await db.flush()

        # Add songs if provided
        if songId:
            for i, song_id in enumerate(songId):
                try:
                    track_id = UUID(song_id)
                    playlist_track = PlaylistTrack(
                        playlist_id=playlist.id,
                        track_id=track_id,
                        order=i,
                    )
                    db.add(playlist_track)
                except ValueError:
                    continue

        await db.commit()

    # Return created/updated playlist
    return await get_playlist(id=str(playlist.id), f=f, current_user=current_user, db=db)


@router.get("/updatePlaylist.view")
@router.post("/updatePlaylist.view")
async def update_playlist(
    playlistId: str = Query(..., description="Playlist ID"),
    name: str = Query(None, description="New name"),
    comment: str = Query(None, description="New comment"),
    public: bool = Query(None, description="Public flag"),
    songIdToAdd: list[str] = Query(None, description="Songs to add"),
    songIndexToRemove: list[int] = Query(None, description="Song indices to remove"),
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Update playlist metadata and contents.

    Args:
        playlistId: Playlist ID
        name: New playlist name
        comment: New comment
        public: Public visibility flag
        songIdToAdd: Song IDs to add
        songIndexToRemove: Indices of songs to remove (0-based)

    Returns:
        Empty success response
    """
    try:
        playlist_id = UUID(playlistId)
    except ValueError:
        return subsonic_error(10, ERR_INVALID_PLAYLIST_ID, f=f)

    # Get playlist
    result = await db.execute(select(Playlist).where(Playlist.id == playlist_id))
    playlist = result.scalar_one_or_none()

    if not playlist:
        return subsonic_error(70, ERR_PLAYLIST_NOT_FOUND)

    if playlist.owner_id != current_user.id:
        return subsonic_error(50, ERR_ACCESS_DENIED)

    # Update metadata
    if name is not None:
        playlist.name = name
    if comment is not None:
        playlist.comment = comment
    if public is not None:
        playlist.public = public

    # Remove songs by index
    if songIndexToRemove:
        # Get current tracks ordered
        result = await db.execute(
            select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id).order_by(PlaylistTrack.order)
        )
        tracks = list(result.scalars().all())

        # Remove by index (reverse order to preserve indices)
        for idx in sorted(songIndexToRemove, reverse=True):
            if 0 <= idx < len(tracks):
                await db.delete(tracks[idx])

        # Reorder remaining tracks
        result = await db.execute(
            select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id).order_by(PlaylistTrack.order)
        )
        remaining = list(result.scalars().all())
        for i, track in enumerate(remaining):
            track.order = i

    # Add songs
    if songIdToAdd:
        # Get current max order
        result = await db.execute(select(func.max(PlaylistTrack.order)).where(PlaylistTrack.playlist_id == playlist_id))
        max_order = result.scalar() or -1

        for song_id in songIdToAdd:
            try:
                track_id = UUID(song_id)
                max_order += 1
                playlist_track = PlaylistTrack(
                    playlist_id=playlist_id,
                    track_id=track_id,
                    order=max_order,
                )
                db.add(playlist_track)
            except ValueError:
                continue

    playlist.updated_at = datetime.now(UTC)
    await db.commit()

    return subsonic_response()


@router.get("/deletePlaylist.view")
@router.post("/deletePlaylist.view")
async def delete_playlist(
    id: str = Query(..., description="Playlist ID"),
    f: str = "xml",
    current_user: User = Depends(subsonic_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete playlist.

    Args:
        id: Playlist ID

    Returns:
        Empty success response
    """
    try:
        playlist_id = UUID(id)
    except ValueError:
        return subsonic_error(10, ERR_INVALID_PLAYLIST_ID)

    # Get playlist
    result = await db.execute(select(Playlist).where(Playlist.id == playlist_id))
    playlist = result.scalar_one_or_none()

    if not playlist:
        return subsonic_error(70, ERR_PLAYLIST_NOT_FOUND)

    if playlist.owner_id != current_user.id:
        return subsonic_error(50, ERR_ACCESS_DENIED)

    # Delete playlist (cascade will delete PlaylistTrack entries)
    await db.delete(playlist)
    await db.commit()

    return subsonic_response()
