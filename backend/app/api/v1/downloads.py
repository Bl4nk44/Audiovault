from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from app.db.database import get_db
from app.services.download_manager import download_manager
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.download import Download
from pydantic import BaseModel
from uuid import UUID
import os
from app.schemas.download import DownloadCreate


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
    from app.services.library_data import library_data_service
    return await library_data_service.get_library_items(db, str(current_user.id), skip, limit, source, playlist)

@router.put("/library/{download_id}")
async def update_library_item(
    download_id: UUID,
    updates: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.library_maintenance import library_maintenance_service
    try:
        await library_maintenance_service.update_download_item(db, str(current_user.id), str(download_id), updates)
        return {"status": "success"}
    except ValueError as e:
        if str(e) == "Item not found":
            raise HTTPException(status_code=404, detail="Item not found")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/queue")
async def get_queue(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.library_data import library_data_service
    return await library_data_service.get_queue_items(db, str(current_user.id))
        
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

