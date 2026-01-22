import os
from uuid import UUID

from app.core.dependencies import get_current_active_user
from app.db.database import get_db
from app.models.download import Download
from app.models.user import User
from app.schemas.download import DownloadCreate
from app.services.download_manager import download_manager
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()


class DownloadRequest(BaseModel):
    track_id: UUID
    source: str
    playlist_name: str | None = None


class TrackResponse(BaseModel):
    id: UUID
    title: str
    artist: str
    image_url: str | None = None


@router.post("/add")
async def add_download(
    request: DownloadRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    download_data = DownloadCreate(
        track_id=request.track_id,
        source=request.source,
        playlist_name=request.playlist_name,
    )
    return await download_manager.add_download(db, current_user.id, download_data)


@router.post("/{download_id}/pause")
async def pause_download(download_id: UUID, current_user: User = Depends(get_current_active_user)):
    await download_manager.pause_download(str(download_id))
    return {"status": "success"}


@router.post("/{download_id}/resume")
async def resume_download(
    download_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await download_manager.resume_download(db, str(download_id))
    return {"status": "success"}


@router.post("/{download_id}/retry")
async def retry_download(
    download_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await download_manager.resume_download(db, str(download_id))
    return {"status": "success"}


@router.delete("/{download_id}")  # Standardized path
async def remove_download(
    download_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # First check if file exists to delete it (as cancel_download deletes the DB record)
    result = await db.execute(select(Download).where(Download.id == download_id, Download.user_id == current_user.id))
    download = result.scalar_one_or_none()

    if not download:
        raise HTTPException(status_code=404, detail="Download not found")

    file_path = download.file_path

    # Use manager to cancel task and delete from DB
    await download_manager.cancel_download(db, str(download_id))

    # Delete physical file
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error deleting file {file_path}: {e}")

    return {"status": "success"}


@router.delete("/library/playlist")
async def delete_playlist(
    source: str,
    playlist_name: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an entire playlist and its contents."""
    await download_manager.delete_playlist(db, str(current_user.id), source, playlist_name)
    return {"status": "success", "message": f"Playlist {playlist_name} deleted"}


class ArtistDownloadRequest(BaseModel):
    source: str = "spotify"


@router.post("/artist/{artist_id}/download-all")
async def download_all_artist_tracks(
    artist_id: str,
    request: ArtistDownloadRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download all tracks from an artist's discography.
    Creates a folder with the artist's name and downloads all albums/singles.
    """
    import logging
    from app.services.spotify_service import SpotifyService
    from app.models.track import Track
    
    logger = logging.getLogger(__name__)
    
    if request.source != "spotify":
        raise HTTPException(status_code=400, detail="Only Spotify source is currently supported")
    
    service = SpotifyService()
    if not service.client:
        raise HTTPException(status_code=503, detail="Spotify service not configured")
    
    # Get artist details
    artist = service.get_artist_details(artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    
    artist_name = artist["name"]
    queued_count = 0
    
    # Get all albums for the artist
    albums = service.get_artist_albums(artist_id)
    
    for album in albums:
        album_id = album["id"]
        
        # Get tracks from the album
        tracks = service.get_album_tracks(album_id)
        
        for track_data in tracks:
            # Check if track already exists in DB
            existing = await db.execute(
                select(Track).where(
                    Track.spotify_id == track_data["id"]
                )
            )
            track_obj = existing.scalar_one_or_none()
            
            if not track_obj:
                # Create track in DB
                track_obj = Track(
                    title=track_data["title"],
                    artist=track_data["artist"],
                    spotify_id=track_data["id"],
                    duration_ms=track_data.get("duration_ms"),
                    metadata_content={
                        "image_url": track_data.get("image_url"),
                        "album_art": track_data.get("image_url"), # Fallback
                        "album": track_data.get("album"),
                        "isrc": track_data.get("isrc"),
                    }
                )
                db.add(track_obj)
                await db.flush()
            
            # Queue download with artist name as folder
            download_data = DownloadCreate(
                track_id=track_obj.id,
                source="spotify",
                playlist_name=artist_name,  # Use artist name as folder
            )
            
            try:
                await download_manager.add_download(db, current_user.id, download_data)
                queued_count += 1
            except Exception as e:
                logger.warning(f"Failed to queue track {track_data['title']}: {e}")
                continue
    
    await db.commit()
    
    return {
        "status": "success",
        "artist": artist_name,
        "queued_count": queued_count,
        "message": f"Queued {queued_count} tracks from {artist_name}"
    }


@router.post("/album/{album_id}/download")
async def download_album(
    album_id: str,
    request: ArtistDownloadRequest, # reusing this model as it just has 'source'
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download all tracks from a specific album.
    Creates a folder with the Album name (or Artist/Album structure handled by manager).
    """
    import logging
    from app.services.spotify_service import SpotifyService
    from app.models.track import Track
    
    logger = logging.getLogger(__name__)
    
    if request.source != "spotify":
        raise HTTPException(status_code=400, detail="Only Spotify source is currently supported")
    
    service = SpotifyService()
    if not service.client:
        raise HTTPException(status_code=503, detail="Spotify service not configured")
    
    # Get album details for name
    try:
        album_data = service.get_album(album_id)
        if not album_data:
             raise HTTPException(status_code=404, detail="Album not found")
        album_name = album_data["name"]
    except Exception as e:
        logger.error(f"Error fetching album {album_id}: {e}")
        raise HTTPException(status_code=404, detail="Album not found")
    
    queued_count = 0
    
    # Get tracks from the album
    tracks = service.get_album_tracks(album_id)
    
    for track_data in tracks:
        # Check if track already exists in DB
        existing = await db.execute(
            select(Track).where(
                Track.spotify_id == track_data["id"]
            )
        )
        track_obj = existing.scalar_one_or_none()
        
        if not track_obj:
            # Create track in DB
            track_obj = Track(
                title=track_data["title"],
                artist=track_data["artist"],
                spotify_id=track_data["id"],
                duration_ms=track_data.get("duration_ms"),
                metadata_content={
                    "image_url": track_data.get("image_url"),
                    "album_art": track_data.get("image_url"),
                    "album": track_data.get("album"),
                    "isrc": track_data.get("isrc"),
                }
            )
            db.add(track_obj)
            await db.flush()
        
        # Queue download with album name as playlist/folder? 
        # Usually user prefers Artist/Album structure.
        # But 'playlist_name' in DownloadCreate forces a specific folder.
        # If we pass None, the download manager uses default structure (Artist - Title).
        # Let's pass album_name to group them if desired, OR None for default flat/artist structure.
        # User request implies "download album", usually implying a folder.
        # Let's use album_name as playlist_name so they end up in a folder.
        
        download_data = DownloadCreate(
            track_id=track_obj.id,
            source="spotify",
            playlist_name=album_name, 
        )
        
        try:
            await download_manager.add_download(db, current_user.id, download_data)
            queued_count += 1
        except Exception as e:
            logger.warning(f"Failed to queue track {track_data['title']}: {e}")
            continue
            
    await db.commit()
    
    return {
        "status": "success",
        "album": album_name,
        "queued_count": queued_count,
        "message": f"Queued {queued_count} tracks from {album_name}"
    }


@router.post("/rescan")
async def rescan_library(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.library_maintenance import library_maintenance_service

    requeued_count = await library_maintenance_service.rescan_library_integrity(db, str(current_user.id))
    return {"status": "success", "rescanned_count": requeued_count}


@router.post("/clear-history")
async def clear_history(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.library_maintenance import library_maintenance_service

    await library_maintenance_service.clear_history(db, str(current_user.id))
    return {"status": "success"}


@router.post("/restart-all")
async def restart_all(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Restart all failed/cancelled downloads."""
    count = await download_manager.restart_all_downloads(db, str(current_user.id))
    return {"status": "success", "count": count}


@router.get("/library/folders")
async def get_library_folders(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the folder structure for the library: Service -> Playlists
    """
    # Get distinct sources
    result = await db.execute(
        select(Download.source, Download.playlist_name)
        .where(Download.user_id == current_user.id, Download.status == "completed")
        .distinct()
    )

    rows = result.all()

    # Construct grouping
    structure = {}

    for row in rows:
        source = row[0] or "other"
        playlist = row[1]

        if source not in structure:
            structure[source] = set()

        if playlist:
            structure[source].add(playlist)

    # Convert sets to sorted lists
    response = {}
    for source, playlists in structure.items():
        response[source] = sorted(list(playlists))

    return response


@router.get("/library")
async def get_library(
    skip: int = 0,
    limit: int = 50,
    source: str | None = None,
    playlist: str | None = None,
    search: str | None = None,
    artist: str | None = None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.library_data import library_data_service

    return await library_data_service.get_library_items(
        db,
        str(current_user.id),
        skip,
        limit,
        source,
        playlist,
        search,
        artist,
        min_duration,
        max_duration,
    )


class BulkUpdateRequest(BaseModel):
    """Request model for bulk updating library items."""
    download_ids: list[UUID]
    updates: dict  # Fields to update: artist, title, album, genre, year


@router.put("/library/bulk-update")
async def bulk_update_library_items(
    request: BulkUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk update metadata for multiple library items at once.
    All specified items will receive the same updates.
    """
    from app.services.library_maintenance import library_maintenance_service

    if not request.download_ids:
        raise HTTPException(status_code=400, detail="No items specified")

    if len(request.download_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 items per request")

    # Validate allowed update fields
    allowed_fields = {"artist", "title", "album", "genre", "year", "playlist_name"}
    invalid_fields = set(request.updates.keys()) - allowed_fields
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fields: {', '.join(invalid_fields)}. Allowed: {', '.join(allowed_fields)}"
        )

    success_count = 0
    failed_ids = []

    for d_id in request.download_ids:
        try:
            await library_maintenance_service.update_download_item(
                db, str(current_user.id), str(d_id), request.updates
            )
            success_count += 1
        except Exception:
            failed_ids.append(str(d_id))

    return {
        "status": "success" if not failed_ids else "partial",
        "updated_count": success_count,
        "failed_count": len(failed_ids),
        "failed_ids": failed_ids[:10],
    }


@router.put("/library/{download_id}")
async def update_library_item(
    download_id: UUID,
    updates: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.library_maintenance import library_maintenance_service

    try:
        await library_maintenance_service.update_download_item(db, str(current_user.id), str(download_id), updates)
        return {"status": "success"}
    except ValueError as e:
        if str(e) == "Item not found":
            raise HTTPException(status_code=404, detail="Item not found") from e
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/queue")
async def get_queue(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.library_data import library_data_service

    return await library_data_service.get_queue_items(db, str(current_user.id))


@router.post("/maintenance/fix-legacy-data")
async def fix_legacy_data(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Diagnose and fix legacy data.
    """
    from app.services.library_maintenance import library_maintenance_service

    fixed_count = await library_maintenance_service.fix_legacy_data(db)
    return {"status": "success", "fixed_count": fixed_count}


@router.post("/maintenance/scan-library")
async def scan_library(
    scan_path: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Scans the DOWNLOAD_DIR (or custom scan_path) for mp3 files.
    """
    from app.services.library_scanner import library_scanner_service

    result = await library_scanner_service.scan_directory(db, str(current_user.id), scan_path)

    if result.get("status") == "error" and "Access denied" in result.get("message", ""):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail=result["message"])

    return result
