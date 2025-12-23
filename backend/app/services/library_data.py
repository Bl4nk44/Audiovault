from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, case
from sqlalchemy.orm import joinedload
from app.models.download import Download
from app.core.config import settings
import os
import uuid
from typing import List

class LibraryDataService:
    
    async def get_library_items(self, db: AsyncSession, user_id: str, skip: int = 0, limit: int = 50, source: str = None, playlist: str = None) -> dict:
        try:
            u_uuid = uuid.UUID(str(user_id))
        except ValueError:
            return {"items": [], "total": 0, "skip": skip, "limit": limit}

        # Build query filters
        conditions = [
            Download.user_id == u_uuid,
            Download.status == 'completed'
        ]
        
        if source:
            conditions.append(Download.source == source)
        
        if playlist:
            if playlist == "__none__":
                 conditions.append(Download.playlist_name.is_(None))
            else:
                 conditions.append(Download.playlist_name == playlist)
                 
        # First, get total count
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
            # Transformation logic
            item_data, updated = self._transform_download_item(d)
            items.append(item_data)
            if updated:
                updates_made = True
        
        if updates_made:
            await db.commit()
            
        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    def _transform_download_item(self, d: Download) -> tuple[dict, bool]:
        updated = False
        image_url = None
        if d.track.metadata_content:
            image_url = d.track.metadata_content.get('image_url') or d.track.metadata_content.get('album_art')
            
        # Auto-fix for extension mismatch
        if d.file_path and not os.path.exists(d.file_path):
            base, ext = os.path.splitext(d.file_path)
            if ext != '.mp3':
                potential_path = base + '.mp3'
                if os.path.exists(potential_path):
                    d.file_path = potential_path
                    updated = True

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

        return {
            "id": str(d.id),
            "track_id": str(d.track_id),
            "status": d.status,
            "progress": d.progress,
            "error_message": d.error_message,
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
        }, updated

    async def get_queue_items(self, db: AsyncSession, user_id: str) -> List[dict]:
        try:
            u_uuid = uuid.UUID(str(user_id))
        except ValueError:
            return []

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
                Download.user_id == u_uuid,
                Download.archived.is_(False) 
            )
            .order_by(status_order, Download.created_at.desc())
        )
        downloads = result.scalars().all()
        
        items = []
        for d in downloads:
            item_data, _ = self._transform_download_item(d)
            items.append(item_data)
            
        return items

library_data_service = LibraryDataService()
