import json
import logging
from datetime import datetime as dt, timezone
from typing import Optional
from uuid import UUID

from app.core.dependencies import get_current_active_user
from app.db.database import get_db
from app.models.playlist import Playlist, PlaylistTrack
from app.models.track import Track
from app.models.user import User
from app.schemas.download import DownloadCreate
from app.schemas.playlist import (
    PlaylistCreate,
    PlaylistResponse,
    PlaylistTrackAdd,
    PlaylistTrackAddResponse,
    PlaylistTrackResponse,
    PlaylistUpdate,
)
from app.services.playlist_version_service import playlist_version_service
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

router = APIRouter()
logger = logging.getLogger(__name__)

PLAYLIST_NOT_FOUND = "Playlist not found"


@router.post("/", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    playlist_in: PlaylistCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new playlist for the current user.
    """
    new_playlist = Playlist(
        name=playlist_in.name,
        comment=playlist_in.comment,
        public=playlist_in.public,
        owner_id=current_user.id,
    )
    db.add(new_playlist)
    await db.commit()
    await db.refresh(new_playlist)

    return PlaylistResponse(
        id=new_playlist.id,
        name=new_playlist.name,
        comment=new_playlist.comment,
        public=new_playlist.public,
        owner_id=new_playlist.owner_id,
        created_at=new_playlist.created_at,
        updated_at=new_playlist.updated_at,
        tracks_count=0,
        tracks=[],
    )


@router.get("/", response_model=list[PlaylistResponse])
async def get_playlists(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all playlists owned by the current user.
    """
    query = (
        select(Playlist)
        .where(Playlist.owner_id == current_user.id)
        .options(selectinload(Playlist.tracks).selectinload(PlaylistTrack.track))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    playlists = result.scalars().all()

    # Manual mapping to include track count efficiently if needed,
    # but for now we rely on the relationship loading.
    # To optimize count, we could use a separate query or column_property.
    # For now (MVP), we will just let Pydantic handle it (check PlaylistResponse logic).

    # Wait, PlaylistResponse expects tracks list.
    # We need to ensure tracks are loaded or handled correctly.
    # The models/playlist.py has tracks relationship loading PlaylistTrack objects.
    # PlaylistTrack has 'track' relationship.
    # We need to map PlaylistTrack -> PlaylistTrackResponse manually or via SQL.

    responses = []
    for pl in playlists:
        if pl is None:
            continue
        # Construct response with tracks
        pl_tracks_resp = []
        for pt in pl.tracks:
            if pt.track:
                pl_tracks_resp.append(
                    PlaylistTrackResponse(
                        track_id=pt.track.id,
                        order=pt.order,
                        title=pt.track.title,
                        artist=pt.track.artist,
                        album=pt.track.album,
                        duration_ms=pt.track.duration_ms,
                        image_url=pt.track.metadata_content.get("image_url") if pt.track.metadata_content else None,
                    )
                )

        responses.append(
            PlaylistResponse(
                id=pl.id,
                name=pl.name,
                comment=pl.comment,
                public=pl.public,
                owner_id=pl.owner_id,
                created_at=pl.created_at,
                updated_at=pl.updated_at,
                tracks_count=len(pl_tracks_resp),
                tracks=pl_tracks_resp,
            )
        )

    return responses


@router.get("/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get specific playlist details.
    """
    query = (
        select(Playlist)
        .where(Playlist.id == playlist_id)
        .where(Playlist.owner_id == current_user.id)
        .options(selectinload(Playlist.tracks).selectinload(PlaylistTrack.track))
    )
    result = await db.execute(query)
    playlist = result.scalar_one_or_none()
    if playlist is None:
        raise HTTPException(status_code=404, detail=PLAYLIST_NOT_FOUND)

    if playlist is None:
        raise HTTPException(status_code=404, detail=PLAYLIST_NOT_FOUND)

    pl_tracks_resp = []
    for pt in playlist.tracks:
        if pt.track:
            pl_tracks_resp.append(
                PlaylistTrackResponse(
                    track_id=pt.track.id,
                    order=pt.order,
                    title=pt.track.title,
                    artist=pt.track.artist,
                    album=pt.track.album,
                    duration_ms=pt.track.duration_ms,
                    image_url=pt.track.metadata_content.get("image_url") if pt.track.metadata_content else None,
                )
            )

    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        comment=playlist.comment,
        public=playlist.public,
        owner_id=playlist.owner_id,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
        tracks_count=len(pl_tracks_resp),
        tracks=pl_tracks_resp,
    )


@router.put("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: UUID,
    playlist_in: PlaylistUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update playlist metadata.
    """
    query = select(Playlist).where(Playlist.id == playlist_id, Playlist.owner_id == current_user.id)
    result = await db.execute(query)
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(status_code=404, detail=PLAYLIST_NOT_FOUND)

    update_data = playlist_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(playlist, field, value)

    await db.commit()
    await db.refresh(playlist)

    # Reload for response to match schema structure if needed, or reconstruct
    # Simpler to just return (lazy load will trigger if we access tracks, but better to query with load if needed)
    # For update metadata, tracks shouldn't change, so empty list or previous list is fine.
    # But to satisfy response model safely:
    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        comment=playlist.comment,
        public=playlist.public,
        owner_id=playlist.owner_id,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
        tracks_count=0,  # Simplified, normally would fetch
        tracks=[],  # Simplified
    )


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a playlist.
    """
    query = select(Playlist).where(Playlist.id == playlist_id, Playlist.owner_id == current_user.id)
    result = await db.execute(query)
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(status_code=404, detail=PLAYLIST_NOT_FOUND)

    if not playlist:
        raise HTTPException(status_code=404, detail=PLAYLIST_NOT_FOUND)
    
    # playlist is guaranteed not None here
    assert playlist is not None
    if playlist is None:
        raise HTTPException(status_code=404, detail=PLAYLIST_NOT_FOUND)

    await db.delete(playlist)
    await db.commit()


async def _resolve_track_ids(
    db: AsyncSession, track_ids: list[str], user_id: UUID, playlist_id: UUID, playlist_name: str
) -> list[UUID]:
    """Helper to resolve track IDs from various formats."""
    from app.services.download_manager import download_manager

    resolved_ids = []
    for track_id_str in track_ids:
        if track_id_str.startswith("external:"):
            parts = track_id_str.split(":", 2)
            if len(parts) >= 3:
                artist_name, track_name = parts[1], parts[2]

                # Try to find existing track
                find_query = (
                    select(Track)
                    .where(Track.title.ilike(f"%{track_name}%"), Track.artist.ilike(f"%{artist_name}%"))
                    .limit(1)
                )
                find_result = await db.execute(find_query)
                existing_track = find_result.scalar_one_or_none()

                if existing_track:
                    resolved_ids.append(existing_track.id)
                else:
                    # Create placeholder
                    new_track = Track(
                        title=track_name,
                        artist=artist_name,
                        duration_ms=0,
                        metadata_content={"source": "lastfm", "image_url": None},
                    )
                    db.add(new_track)
                    await db.flush()
                    resolved_ids.append(new_track.id)

                    # Trigger download
                    try:
                        await download_manager.add_download(
                            db=db,
                            user_id=user_id,
                            download_data=DownloadCreate(
                                track_id=new_track.id,
                                source="lastfm",
                                playlist_id=playlist_id,
                                playlist_name=playlist_name,
                            ),
                        )
                    except Exception as e:
                        from app.api.v1.playlists import logger

                        logger.error(f"Failed to trigger automatic download: {e}")
        else:
            try:
                resolved_ids.append(UUID(track_id_str))
            except ValueError:
                continue
    return resolved_ids


@router.post("/{playlist_id}/tracks", status_code=status.HTTP_201_CREATED)
async def add_tracks_to_playlist(
    playlist_id: UUID,
    tracks_in: PlaylistTrackAdd,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Add tracks to playlist."""
    # 1. Verify playlist ownership
    query = select(Playlist).where(Playlist.id == playlist_id, Playlist.owner_id == current_user.id)
    result = await db.execute(query)
    playlist = result.scalar_one_or_none()

    if playlist is None:
        raise HTTPException(status_code=404, detail=PLAYLIST_NOT_FOUND)

    # 2. Get current max order
    max_order_query = select(func.max(PlaylistTrack.order)).where(PlaylistTrack.playlist_id == playlist_id)
    max_order_res = await db.execute(max_order_query)
    current_max_order = max_order_res.scalar() or 0

    # 3. Resolve track IDs
    resolved_track_ids = await _resolve_track_ids(db, tracks_in.track_ids, current_user.id, playlist.id, playlist.name)

    # 4. Filter existing tracks
    if resolved_track_ids:
        valid_tracks_query = select(Track.id).where(Track.id.in_(resolved_track_ids))
        valid_tracks_res = await db.execute(valid_tracks_query)
        valid_track_ids = valid_tracks_res.scalars().all()
    else:
        valid_track_ids = []

    if not valid_track_ids:
        raise HTTPException(status_code=400, detail="No valid track IDs provided.")

    # 5. Add new tracks (with duplicate avoidance)
    added_count = 0
    duplicate_count = 0
    for track_id in valid_track_ids:
        exists_query = select(PlaylistTrack).where(
            PlaylistTrack.playlist_id == playlist_id, PlaylistTrack.track_id == track_id
        )
        exists_res = await db.execute(exists_query)
        if exists_res.scalar_one_or_none():
            duplicate_count += 1
            continue

        new_pt = PlaylistTrack(playlist_id=playlist_id, track_id=track_id, order=current_max_order + added_count + 1)
        db.add(new_pt)
        added_count += 1

    if added_count == 0 and duplicate_count == 0:
        raise HTTPException(status_code=400, detail="No tracks were added.")

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error.")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return PlaylistTrackAddResponse(
        added_count=added_count, duplicate_count=duplicate_count, total_processed=len(tracks_in.track_ids)
    )


@router.delete("/{playlist_id}/tracks", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tracks_from_playlist(
    playlist_id: UUID,
    tracks_in: PlaylistTrackAdd,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove tracks from playlist.
    NOTE: This implementation removes ALL occurrences of the specified track_ids from the playlist.
    """
    query = select(Playlist).where(Playlist.id == playlist_id, Playlist.owner_id == current_user.id)
    result = await db.execute(query)
    playlist = result.scalar_one_or_none()

    if playlist is None:
        raise HTTPException(status_code=404, detail=PLAYLIST_NOT_FOUND)

    target_ids = []
    for t_id in tracks_in.track_ids:
        try:
            target_ids.append(UUID(t_id))
        except ValueError:
            continue

    if not target_ids:
        return

    stmt = delete(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id, PlaylistTrack.track_id.in_(target_ids))
    await db.execute(stmt)
    await db.commit()


@router.get("/{playlist_id}/export")
async def export_playlist(
    playlist_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export playlist metadata and tracks as a downloadable JSON file.
    """
    query = (
        select(Playlist)
        .where(Playlist.id == playlist_id)
        .where(Playlist.owner_id == current_user.id)
        .options(selectinload(Playlist.tracks).selectinload(PlaylistTrack.track))
    )
    result = await db.execute(query)
    playlist = result.scalar_one_or_none()

    if playlist is None:
        raise HTTPException(status_code=404, detail=PLAYLIST_NOT_FOUND)

    # Build export data
    tracks_data = []
    for pt in playlist.tracks:
        if pt.track:
            tracks_data.append(
                {
                    "order": pt.order,
                    "title": pt.track.title,
                    "artist": pt.track.artist,
                    "album": pt.track.album,
                    "duration_ms": pt.track.duration_ms,
                    "year": pt.track.metadata_content.get("year") if pt.track.metadata_content else None,
                    "genre": pt.track.metadata_content.get("genre") if pt.track.metadata_content else None,
                }
            )

    export_data = {
        "playlist": {
            "id": str(playlist.id),
            "name": playlist.name,
            "comment": playlist.comment,
            "public": playlist.public,
            "created_at": playlist.created_at.isoformat() if playlist.created_at else None,
            "updated_at": playlist.updated_at.isoformat() if playlist.updated_at else None,
        },
        "tracks_count": len(tracks_data),
        "tracks": tracks_data,
        "exported_at": dt.now(tz=timezone.utc).isoformat(),
        "export_version": "1.0",
    }

    # Create safe filename
    safe_name = "".join(c for c in playlist.name if c.isalnum() or c in " -_").strip()
    filename = f"{safe_name}_playlist.json"

    json_content = json.dumps(export_data, indent=2, ensure_ascii=False)

    return Response(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# === Playlist Versioning Endpoints ===


class PlaylistVersionResponse(BaseModel):
    """Response model for playlist version."""

    id: UUID
    version_number: int
    name: str
    comment: Optional[str] = None
    tracks_count: int
    change_type: str
    change_details: dict
    created_at: dt | None = None

    class Config:
        from_attributes = True


@router.get("/{playlist_id}/versions", response_model=list[PlaylistVersionResponse])
async def get_playlist_versions(
    playlist_id: UUID,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get version history for a playlist.
    """
    # Check if playlist exists and user has access
    result = await db.execute(select(Playlist).where(Playlist.id == playlist_id))
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(status_code=404, detail=PLAYLIST_NOT_FOUND)

    if playlist.owner_id != current_user.id and not playlist.public:
        raise HTTPException(status_code=403, detail="Access denied")

    versions = await playlist_version_service.get_versions(db, playlist_id, limit)

    return [
        PlaylistVersionResponse(
            id=v.id,
            version_number=v.version_number,
            name=v.name,
            comment=v.comment,
            tracks_count=len(v.tracks_snapshot) if v.tracks_snapshot else 0,
            change_type=v.change_type,
            change_details=v.change_details or {},
            created_at=v.created_at,
        )
        for v in versions
    ]


@router.post("/{playlist_id}/rollback/{version_number}")
async def rollback_playlist(
    playlist_id: UUID,
    version_number: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Rollback a playlist to a previous version.
    """
    # Get playlist with tracks loaded
    result = await db.execute(select(Playlist).options(selectinload(Playlist.tracks)).where(Playlist.id == playlist_id))
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(status_code=404, detail=PLAYLIST_NOT_FOUND)

    if playlist.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can rollback playlist")

    # Get the version to rollback to
    version = await playlist_version_service.get_version(db, playlist_id, version_number)

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Perform rollback
    new_version = await playlist_version_service.rollback_to_version(
        db=db,
        playlist=playlist,
        version=version,
        user_id=current_user.id,
    )

    return {
        "message": f"Playlist rolled back to version {version_number}",
        "new_version_number": new_version.version_number,
    }
