from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy import case
from typing import Optional
from app.db.database import get_db
from app.services.download_manager import download_manager
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.download import Download
from pydantic import BaseModel
from uuid import UUID
import os
from app.core.config import settings

router = APIRouter()

class DownloadRequest(BaseModel):
    track_id: UUID
    source: str
    playlist_name: str | None = None

class TrackResponse(BaseModel):
    id: UUID
    title: str
    artist: str
    image_url: Optional[str] = None

class DownloadResponse(BaseModel):
    id: UUID
    status: str
    progress: float
    error_message: Optional[str] = None
    track: dict # Using dict to allow flexibility, or we can define a nested model
    # Let's use a custom structure for the response to flatten/inject image_url

from app.schemas.download import DownloadCreate

@router.post("/add")
async def add_download(
    request: DownloadRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    download_data = DownloadCreate(
        track_id=request.track_id, 
        source=request.source, 
        playlist_name=request.playlist_name
    )
    return await download_manager.add_download(db, current_user.id, download_data)

@router.post("/{download_id}/pause")
async def pause_download(
    download_id: UUID,
    current_user: User = Depends(get_current_active_user)
):
    await download_manager.pause_download(str(download_id))
    return {"status": "success"}

@router.post("/{download_id}/resume")
async def resume_download(
    download_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    await download_manager.resume_download(db, str(download_id))
    return {"status": "success"}

@router.post("/{download_id}/retry")
async def retry_download(
    download_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    await download_manager.retry_download(db, str(download_id))
    return {"status": "success"}

@router.delete("/{download_id}") # Standardized path
async def remove_download(
    download_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
):
    """Delete an entire playlist and its contents."""
    await download_manager.delete_playlist(db, str(current_user.id), source, playlist_name)
    return {"status": "success", "message": f"Playlist {playlist_name} deleted"}

@router.post("/rescan")
async def rescan_library(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.library_maintenance import library_maintenance_service
    requeued_count = await library_maintenance_service.rescan_library_integrity(db, str(current_user.id))
    return {"status": "success", "rescanned_count": requeued_count}



from sqlalchemy import update, text

@router.post("/clear-history")
async def clear_history(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.library_maintenance import library_maintenance_service
    await library_maintenance_service.clear_history(db, str(current_user.id))
    return {"status": "success"}

@router.get("/library/folders")
async def get_library_folders(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the folder structure for the library: Service -> Playlists
    """
    # Get distinct sources
    result = await db.execute(
        select(Download.source, Download.playlist_name)
        .where(
            Download.user_id == current_user.id,
            Download.status == 'completed'
        )
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
    source: Optional[str] = None,
    playlist: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Return all completed downloads (Library view)
    # Build query filters
    conditions = [
        Download.user_id == current_user.id,
        Download.status == 'completed'
    ]
    
    if source:
        conditions.append(Download.source == source)
    
    if playlist:
        if playlist == "__none__":
             conditions.append(Download.playlist_name == None)
        else:
             conditions.append(Download.playlist_name == playlist)
             
    # First, get total count
    from sqlalchemy import func
    count_query = select(func.count()).select_from(Download).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated items
    result = await db.execute(
        select(Download)
        .options(joinedload(Download.track))
        .where(*conditions)
        .order_by(Download.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    downloads = result.scalars().all()
    
    items = []
    updates_made = False
    
    for d in downloads:
        image_url = None
        if d.track.metadata_content:
            image_url = d.track.metadata_content.get('image_url') or d.track.metadata_content.get('album_art')
            
        # Auto-fix for extension mismatch (e.g. webm in DB but mp3 on disk)
        if d.file_path and not os.path.exists(d.file_path):
            base, ext = os.path.splitext(d.file_path)
            if ext != '.mp3':
                potential_path = base + '.mp3'
                if os.path.exists(potential_path):
                    d.file_path = potential_path
                    updates_made = True

        filename = None
        if d.file_path:
            try:
                rel_path = os.path.relpath(d.file_path, settings.DOWNLOAD_DIR).replace("\\", "/")
                if rel_path.startswith(".."):
                    filename = os.path.basename(d.file_path)
                else:
                    filename = rel_path
            except Exception:
                filename = os.path.basename(d.file_path)

        items.append({
            "id": str(d.id),
            "track_id": str(d.track_id),
            "status": d.status,
            "file_path": d.file_path,
            "created_at": d.created_at,
            "source": d.source,
            "playlist_name": d.playlist_name,
            "track": {
                "title": d.track.title,
                "artist": d.track.artist,
                "album": d.track.album,
                "image_url": image_url,
                "filename": filename
            }
        })
    
    if updates_made:
        await db.commit()
    
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.put("/library/{download_id}")
async def update_library_item(
    download_id: UUID,
    updates: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Download).options(joinedload(Download.track)).where(Download.id == download_id, Download.user_id == current_user.id))
    download = result.scalar_one_or_none()
    
    if not download:
        raise HTTPException(status_code=404, detail="Item not found")
        
    # Handle filename rename
    if 'filename' in updates:
        new_filename = updates['filename']
        if download.file_path and os.path.exists(download.file_path):
            dir_path = os.path.dirname(download.file_path)
            new_path = os.path.join(dir_path, new_filename)
            try:
                os.rename(download.file_path, new_path)
                download.file_path = new_path
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to rename file: {e}")
    
    # Handle metadata updates (title, artist)
    if 'title' in updates:
        download.track.title = updates['title']
    if 'artist' in updates:
        download.track.artist = updates['artist']
    if 'album' in updates:
        download.track.album = updates['album']
        
    await db.commit()
    return {"status": "success"}

@router.get("/queue")
async def get_queue(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Custom sorting: Downloading first, then Pending/Processing, then others
    status_order = case(
        (Download.status == 'downloading', 1),
        (Download.status == 'processing', 2),
        (Download.status == 'pending', 3),
        else_=4
    )

    # Filter out archived items
    result = await db.execute(
        select(Download)
        .options(joinedload(Download.track))
        .where(
            Download.user_id == current_user.id,
            Download.archived == False # Only show unarchived in queue
        )
        .order_by(status_order, Download.created_at.desc())
    )
    downloads = result.scalars().all()
    
    # Transform to include image_url from metadata
    response_data = []
    for d in downloads:
        image_url = None
        if d.track.metadata_content:
            image_url = d.track.metadata_content.get('image_url') or d.track.metadata_content.get('album_art')
            
        filename = None
        if d.file_path:
            try:
                rel_path = os.path.relpath(d.file_path, settings.DOWNLOAD_DIR).replace("\\", "/")
                if rel_path.startswith(".."):
                    filename = os.path.basename(d.file_path)
                else:
                    filename = rel_path
            except Exception:
                filename = os.path.basename(d.file_path)

        response_data.append({
            "id": str(d.id),
            "track_id": str(d.track_id),
            "status": d.status,
            "progress": d.progress,
            "error_message": d.error_message,
            "track": {
                "title": d.track.title,
                "artist": d.track.artist,
                "image_url": image_url,
                "filename": filename
            }
        })
        
@router.post("/maintenance/fix-legacy-data")
async def fix_legacy_data(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Diagnose and fix legacy data.
    """
    from app.services.library_maintenance import library_maintenance_service
    fixed_count = await library_maintenance_service.fix_legacy_data(db)
    return {"status": "success", "fixed_count": fixed_count}
             

@router.post("/maintenance/scan-library")
async def scan_library(
    scan_path: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
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

