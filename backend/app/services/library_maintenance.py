from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update, text
from app.models.download import Download
from app.services.download_manager import download_manager
from typing import List
import os
import logging

logger = logging.getLogger(__name__)

class LibraryMaintenanceService:
    
    async def fix_legacy_data(self, db: AsyncSession) -> int:
        """Fix missing source/playlist info based on track metadata or heuristics."""
        # Fix Source
        result = await db.execute(
            select(Download)
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
        
        if fixed_source_count > 0:
            await db.commit()
            
        return fixed_source_count

    async def rescan_library_integrity(self, db: AsyncSession, user_id: str) -> int:
        """Check for missing files and re-queue them."""
        result = await db.execute(
            select(Download).where(
                Download.user_id == user_id,
                Download.status == 'completed'
            )
        )
        downloads = result.scalars().all()
        
        requeued_ids = []
        for download in downloads:
            file_missing = False
            if download.file_path:
                if not os.path.exists(download.file_path):
                    file_missing = True
            else:
                file_missing = True
                
            if file_missing:
                # Reset to pending
                download.status = 'pending'
                download.progress = 0
                download.error_message = None
                download.file_path = None
                requeued_ids.append(download.id)
                
        if requeued_ids:
            await db.commit()
            for d_id in requeued_ids:
                await download_manager.queue.put(d_id)
            await download_manager.start_worker()
            
        return len(requeued_ids)

    async def clear_history(self, db: AsyncSession, user_id: str):
        """Archive all completed downloads."""
        # Auto-migration check (safe-guard)
        try:
            await db.execute(text("ALTER TABLE downloads ADD COLUMN archived BOOLEAN DEFAULT 0"))
            await db.commit()
        except Exception:
            await db.rollback()
            pass

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

library_maintenance_service = LibraryMaintenanceService()
