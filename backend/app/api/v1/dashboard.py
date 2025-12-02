from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
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

    return {
        "total_downloads": str(total_downloads),
        "tracks_in_library": str(tracks_in_library),
        "pending_queue": str(pending_queue),
        "storage_free": storage_free_text
    }
