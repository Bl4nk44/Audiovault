import os
import shutil
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID

from app.core.config import settings
from app.core.dependencies import get_current_active_user
from app.db.database import get_db
from app.models.download import Download
from app.models.user import User
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    total_downloads = await _get_count(db, current_user.id)
    tracks_in_library = await _get_count(db, current_user.id, status="completed")
    pending_queue = await _get_queue_count(db, current_user.id)

    storage_free_text = _get_storage_free_space()
    recent_activity = await _get_recent_activity(db, current_user.id)
    active_download = await _get_active_download(db, current_user.id)

    return {
        "total_downloads": str(total_downloads),
        "tracks_in_library": str(tracks_in_library),
        "pending_queue": str(pending_queue),
        "storage_free": storage_free_text,
        "recent_activity": recent_activity,
        "active_download": active_download,
    }


async def _get_count(db: AsyncSession, user_id: UUID, status: Optional[str] = None) -> int:
    query = select(func.count(Download.id)).where(Download.user_id == user_id)
    if status:
        query = query.where(Download.status == status)
    result = await db.execute(query)
    return result.scalar() or 0


async def _get_queue_count(db: AsyncSession, user_id: UUID) -> int:
    query = select(func.count(Download.id)).where(
        Download.user_id == user_id,
        Download.status.in_(["pending", "downloading", "processing"]),
    )
    result = await db.execute(query)
    return result.scalar() or 0


def _get_storage_free_space() -> str:
    try:
        if not os.path.exists(settings.DOWNLOAD_DIR):
            os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)
        _, _, free = shutil.disk_usage(settings.DOWNLOAD_DIR)
        storage_free_gb = round(free / (1024**3), 1)
        return f"{storage_free_gb} GB"
    except Exception:
        return "Unknown"


# ... (skipping unchanged helper functions)


async def _get_recent_activity(db: AsyncSession, user_id: UUID) -> list[dict[str, Any]]:
    recent_query = (
        select(Download)
        .options(selectinload(Download.track))
        .where(Download.user_id == user_id, Download.status == "completed")
        .order_by(Download.completed_at.desc())
        .limit(20)
    )
    result = await db.execute(recent_query)
    recent_downloads = result.scalars().all()

    activity = []
    for d in recent_downloads:
        activity.append(
            {
                "id": str(d.id),
                "track_id": str(d.track_id),
                "title": d.track.title if d.track else "Unknown Title",
                "artist": d.track.artist if d.track else "Unknown Artist",
                "time_ago": _calculate_time_ago(d.completed_at) if d.completed_at else "Unknown",
                "progress": 100,
                "image_url": _get_image_url(d),
                "filename": _get_filename(d),
            }
        )
    return activity


async def _get_active_download(db: AsyncSession, user_id: UUID) -> dict[str, Any] | None:
    # Priority: Downloading
    active_query = (
        select(Download)
        .options(selectinload(Download.track))
        .where(Download.user_id == user_id, Download.status == "downloading")
        .limit(1)
    )
    active_result = await db.execute(active_query)
    active_item = active_result.scalar_one_or_none()

    # Fallback: Pending/Processing
    if not active_item:
        pending_query = (
            select(Download)
            .options(selectinload(Download.track))
            .where(
                Download.user_id == user_id,
                Download.status.in_(["pending", "processing"]),
            )
            .order_by(Download.created_at.asc())
            .limit(1)
        )
        pending_result = await db.execute(pending_query)
        active_item = pending_result.scalar_one_or_none()

    if active_item:
        return {
            "id": str(active_item.id),
            "title": active_item.track.title if active_item.track else "Unknown",
            "artist": active_item.track.artist if active_item.track else "Unknown",
            "status": active_item.status,
            "progress": active_item.progress or 0,
            "image_url": _get_image_url(active_item),
        }
    return None


def _calculate_time_ago(dt: datetime) -> str:
    if not dt:
        return "Just now"
    # Assuming dt is stored as naive UTC or aware UTC.
    # If naive, assume UTC.
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    diff = now - dt
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600}h ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60}m ago"
    return "Just now"


def _get_image_url(download: Download) -> str | None:
    if not download.track or not download.track.metadata_content:
        return None
    meta = download.track.metadata_content
    url = meta.get("image_url") or meta.get("album_art")
    if url:
        return url

    # Fallback to native endpoint
    return f"{settings.API_V1_STR}/stream/{download.track.id}/cover"


def _get_filename(download: Download) -> str:
    if not download.file_path:
        return "Unknown"
    try:
        rel_path = os.path.relpath(download.file_path, settings.DOWNLOAD_DIR).replace("\\", "/")
        if rel_path.startswith(".."):
            return os.path.basename(download.file_path)
        return rel_path
    except Exception:
        return "Unknown"
