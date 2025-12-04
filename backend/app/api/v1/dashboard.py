from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from datetime import datetime
import shutil
import os

from app.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.download import Download
from app.core.config import settings

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Total Downloads (All time, any status)
    total_downloads_query = select(func.count(Download.id)).where(Download.user_id == current_user.id)
    total_downloads_result = await db.execute(total_downloads_query)
    total_downloads = total_downloads_result.scalar() or 0

    # Tracks in Library (Completed downloads)
    library_query = select(func.count(Download.id)).where(
        Download.user_id == current_user.id,
        Download.status == 'completed'
    )
    library_result = await db.execute(library_query)
    tracks_in_library = library_result.scalar() or 0

    # Pending Queue
    queue_query = select(func.count(Download.id)).where(
        Download.user_id == current_user.id,
        Download.status.in_(['pending', 'downloading', 'processing'])
    )
    queue_result = await db.execute(queue_query)
    pending_queue = queue_result.scalar() or 0

    # Storage Free
    try:
        # Ensure directory exists to get usage
        if not os.path.exists(settings.DOWNLOAD_DIR):
            os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)
            
        total, used, free = shutil.disk_usage(settings.DOWNLOAD_DIR)
        # Convert to GB
        storage_free_gb = round(free / (1024**3), 1)
        storage_free_text = f"{storage_free_gb} GB"
    except Exception:
        storage_free_text = "Unknown"

    # Recent Activity (Last 3 completed)
    recent_query = select(Download).options(selectinload(Download.track)).where(
        Download.user_id == current_user.id,
        Download.status == 'completed'
    ).order_by(Download.completed_at.desc()).limit(3)
    recent_result = await db.execute(recent_query)
    recent_downloads = recent_result.scalars().all()
    
    recent_activity = []
    for d in recent_downloads:
        # Calculate time ago roughly
        time_ago = "Just now"
        if d.completed_at:
            diff = datetime.utcnow() - d.completed_at
            if diff.days > 0:
                time_ago = f"{diff.days}d ago"
            elif diff.seconds > 3600:
                time_ago = f"{diff.seconds // 3600}h ago"
            elif diff.seconds > 60:
                time_ago = f"{diff.seconds // 60}m ago"
            else:
                time_ago = "Just now"
                
        metadata = d.track.metadata_content or {}
        image_url = metadata.get('image_url') or metadata.get('album_art')

        recent_activity.append({
            "id": str(d.id),
            "title": d.track.title if d.track else "Unknown Title",
            "artist": d.track.artist if d.track else "Unknown Artist",
            "time_ago": time_ago,
            "progress": 100,
            "image_url": image_url,
            "filename": os.path.basename(d.file_path) if d.file_path else None
        })

    # Active Download Logic
    # 1. Priority: Downloading
    active_query = select(Download).options(selectinload(Download.track)).where(
        Download.user_id == current_user.id,
        Download.status == 'downloading'
    ).limit(1)
    active_result = await db.execute(active_query)
    active_download_item = active_result.scalar_one_or_none()

    # 2. Fallback: Pending/Processing (FIFO - Oldest first)
    if not active_download_item:
        pending_query = select(Download).options(selectinload(Download.track)).where(
            Download.user_id == current_user.id,
            Download.status.in_(['pending', 'processing'])
        ).order_by(Download.created_at.asc()).limit(1)
        pending_result = await db.execute(pending_query)
        active_download_item = pending_result.scalar_one_or_none()
    
    active_download = None
    if active_download_item:
        metadata = active_download_item.track.metadata_content or {}
        image_url = metadata.get('image_url') or metadata.get('album_art')
        
        active_download = {
            "id": str(active_download_item.id),
            "title": active_download_item.track.title if active_download_item.track else "Unknown",
            "artist": active_download_item.track.artist if active_download_item.track else "Unknown",
            "status": active_download_item.status,
            "progress": active_download_item.progress or 0,
            "image_url": image_url
        }

    return {
        "total_downloads": str(total_downloads),
        "tracks_in_library": str(tracks_in_library),
        "pending_queue": str(pending_queue),
        "storage_free": storage_free_text,
        "recent_activity": recent_activity,
        "active_download": active_download
    }
