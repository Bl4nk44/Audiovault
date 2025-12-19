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

@router.post("/add")
async def add_download(
    request: DownloadRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await download_manager.add_download(db, current_user.id, request.track_id, request.source, request.playlist_name)

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
        except Exception as e:
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
    # Get all completed downloads
    result = await db.execute(
        select(Download).where(
            Download.user_id == current_user.id,
            Download.status == 'completed'
        )
    )
    downloads = result.scalars().all()
    
    requeued_count = 0
    requeued_ids = []
    for download in downloads:
        # Check if file exists
        file_missing = False
        if download.file_path:
            if not os.path.exists(download.file_path):
                file_missing = True
        else:
            # No file path recorded, assume missing/broken
            file_missing = True
            
        if file_missing:
            # Reset to pending so it gets downloaded again
            download.status = 'pending'
            download.progress = 0
            download.error_message = None
            # Keep the metadata like track_id, source etc.
            # We might want to clear file_path to avoid confusion until new one is set
            download.file_path = None
            
            # Add to list
            requeued_ids.append(download.id)
            requeued_count += 1
            
    if requeued_count > 0:
        await db.commit()
        
        # Add to queue after commit to ensure worker sees updated status
        for d_id in requeued_ids:
            await download_manager.queue.put(d_id)
            
        await download_manager.start_worker()
        
    return {"status": "success", "rescanned_count": requeued_count}



from sqlalchemy import update, text

@router.post("/clear-history")
async def clear_history(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = current_user.id # Capture ID before potential rollback expires the user object

    # Auto-migration hack (safe to run multiple times)
    try:
        # Check if column exists is hard in generic SQL, so just try adding it and ignore error
        # Note: SQLite doesn't support IF NOT EXISTS for columns easily.
        # We can just catch the exception.
        await db.execute(text("ALTER TABLE downloads ADD COLUMN archived BOOLEAN DEFAULT 0"))
        await db.commit()
    except Exception:
        # Column likely exists
        await db.rollback()
        pass

    # Archive all completed downloads using ORM to handle UUID conversion correctly
    stmt = (
        update(Download)
        .where(
            Download.user_id == user_id,
            Download.status == 'completed'
        )
        .values(archived=True)
    )
    
    await db.execute(stmt)
    await db.commit()
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
    from sqlalchemy import func
    
    # 1. Get stats (ALL records)
    stats_result = await db.execute(
        select(Download.source, Download.playlist_name, func.count(Download.id))
        .group_by(Download.source, Download.playlist_name)
    )
    stats = [{"source": row[0], "playlist": row[1], "count": row[2]} for row in stats_result.all()]
    
    # 2. Fix Source
    result = await db.execute(
        select(Download)
        .options(joinedload(Download.track))
        .where(
            (Download.source == None) | 
            (Download.source == "") | 
            (Download.source == "other")
        )
    )
    downloads = result.scalars().all()
    fixed_source_count = 0
    
    for d in downloads:
        new_source = "youtube" 
        
        if d.track:
            if d.track.metadata_content and d.track.metadata_content.get('source'):
                new_source = d.track.metadata_content.get('source').lower()
            elif d.track.spotify_id:
                new_source = 'spotify'
            elif d.track.deezer_id:
                new_source = 'deezer'
            elif d.track.youtube_id:
                new_source = 'youtube'
            elif d.track.metadata_content and d.track.metadata_content.get('apple_music_id'):
                new_source = 'apple_music'
        
        if d.source != new_source:
             d.source = new_source
             fixed_source_count += 1

    # 3. Fix Playlist (if None -> 'Unknown Playlist' or try to infer)
    # For now, just ensuring it's not None if that causes issues, 
    # but frontend should handle None. Let's start with Source.
             

@router.post("/maintenance/scan-library")
async def scan_library(
    scan_path: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Scans the DOWNLOAD_DIR (or custom scan_path) for mp3 files.
    """
    import os
    import mutagen
    from mutagen.easyid3 import EasyID3
    from app.models.track import Track
    from app.core.config import settings
    
    base_dir = os.path.abspath(settings.DOWNLOAD_DIR)
    
    if scan_path:
        target_path = os.path.abspath(scan_path)
        # Security check: MUST start with safe base_dir
        # os.path.commonpath throws robust errors on mix of relative/abs, 
        # but here we normalized both to abs.
        try:
            common = os.path.commonpath([base_dir, target_path])
        except ValueError:
            common = ""
            
        if common != base_dir:
             raise HTTPException(status_code=403, detail="Access denied: Cannot scan directories outside of download library.")
        
        root_dir = target_path
    else:
        root_dir = base_dir

    if not os.path.exists(root_dir):
         return {"status": "error", "message": f"Directory {root_dir} does not exist"}

    # 1. Get all known file paths from DB to avoid duplicates
    # normalizing paths is crucial here
    result = await db.execute(select(Download.file_path).where(Download.user_id == current_user.id))
    known_paths = set()
    for row in result.all():
        if row[0]:
            known_paths.add(os.path.normpath(row[0]))

    imported_count = 0
    errors = []

    total_found = 0
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.lower().endswith('.mp3'):
                continue
            total_found += 1    
            full_path = os.path.join(dirpath, filename)
            norm_path = os.path.normpath(full_path)
            
            if norm_path in known_paths:
                continue
                
            # Orphan found!
            try:
                # Infer Metadata
                source = "local_import"
                playlist_name = "Imported"
                
                # Check relative path for Source/Playlist structure
                rel_path = os.path.relpath(full_path, root_dir)
                parts = rel_path.split(os.sep)
                
                if len(parts) >= 3:
                     # e.g. Spotify/MyPlaylist/Song.mp3
                     source = parts[0].lower()
                     playlist_name = parts[1]
                elif len(parts) == 2:
                     if parts[0].lower() in ['spotify', 'youtube', 'deezer', 'apple_music', 'tidal', 'soundcloud', 'amazon_music']:
                         source = parts[0].lower()
                         playlist_name = "Uncategorized" 
                     else:
                         playlist_name = parts[0]
                
                # Check explicit metadata first if possible or default to filename
                title = os.path.splitext(filename)[0]
                artist = "Unknown Artist"
                album = "Unknown Album"
                
                try:
                    audio = EasyID3(full_path)
                    if 'title' in audio:
                        title = audio['title'][0]
                    if 'artist' in audio:
                        artist = audio['artist'][0]
                    if 'album' in audio:
                        album = audio['album'][0]
                except Exception:
                     try:
                        m = mutagen.File(full_path)
                        if m and 'TIT2' in m:
                            title = str(m['TIT2'])
                        if m and 'TPE1' in m:
                            artist = str(m['TPE1'])
                     except:
                        pass
                
                new_track = Track(
                    title=title,
                    artist=artist,
                    album=album,
                    filename=filename,
                    duration_ms=0,
                    source_id=f"local:{filename}", 
                    metadata_content={"source": source, "imported": True}
                )
                db.add(new_track)
                await db.flush()
                
                new_download = Download(
                    id=None,
                    user_id=current_user.id,
                    track_id=new_track.id,
                    status='completed',
                    file_path=full_path,
                    source=source,
                    playlist_name=playlist_name,
                    progress=100.0
                )
                db.add(new_download)
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Failed to import {filename}: {str(e)}")
                
    if imported_count > 0:
        await db.commit()
        
    return {
        "status": "success", 
        "scanned_dir": root_dir,
        "total_files_found": total_found,
        "imported_count": imported_count, 
        "errors": errors[:10]
    }
