import os
import uuid

from app.core.config import settings
from app.models.download import Download
from sqlalchemy import case, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from typing import Optional


class LibraryDataService:
    async def get_library_items(
        self,
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        source: Optional[str] = None,
        playlist: Optional[str] = None,
        search: Optional[str] = None,
        artist: Optional[str] = None,
        min_duration: Optional[int] = None,  # in seconds
        max_duration: Optional[int] = None,  # in seconds
    ) -> dict:
        from app.models.track import Track

        try:
            u_uuid = uuid.UUID(str(user_id))
        except ValueError:
            return {"items": [], "total": 0, "skip": skip, "limit": limit}

        # Build query filters
        conditions = [Download.user_id == u_uuid, Download.status == "completed"]

        if source:
            conditions.append(Download.source == source)

        if playlist:
            if playlist == "__none__":
                conditions.append(Download.playlist_name.is_(None))
            else:
                conditions.append(Download.playlist_name == playlist)

        # Build query with join for advanced filtering
        query = select(Download).options(joinedload(Download.track)).join(Track)

        # Search filter (title or artist contains search term)
        if search:
            search_term = f"%{search.lower()}%"
            conditions.append(
                (func.lower(Track.title).like(search_term)) |
                (func.lower(Track.artist).like(search_term)) |
                (func.lower(Track.album).like(search_term))
            )

        # Artist filter
        if artist:
            conditions.append(func.lower(Track.artist).like(f"%{artist.lower()}%"))

        # Duration filters (convert seconds to milliseconds)
        if min_duration is not None:
            conditions.append(Track.duration_ms >= min_duration * 1000)
        if max_duration is not None:
            conditions.append(Track.duration_ms <= max_duration * 1000)

        # Apply all conditions
        query = query.where(*conditions)

        # First, get total count
        count_query = select(func.count()).select_from(Download).join(Track).where(*conditions)
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Get paginated items
        result = await db.execute(
            query
            .order_by(Download.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        downloads = result.scalars().unique().all()

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

        return {"items": items, "total": total, "skip": skip, "limit": limit}

    def _transform_download_item(self, d: Download) -> tuple[dict, bool]:
        updated = False
        image_url = None
        if d.track.metadata_content:
            image_url = d.track.metadata_content.get("image_url") or d.track.metadata_content.get("album_art")

        # Fallback to native cover endpoint if no external URL
        if not image_url:
             # Use absolute path or relative? Frontend usually prepends API_URL if relative?
             # But here we are returning data. Frontend code in PlaylistCard uses `playlist.image_url` directly.
             # If it starts with http, it uses it. If not?
             # Let's check api.ts or component.
             # Actually PlaylistCard just sets src={playlist.image_url}. 
             # If we send "/api/v1/stream/.../cover", browser resolves relative to domain.
             # That works.
             image_url = f"{settings.API_V1_STR}/stream/{d.track.id}/cover"

        # Auto-fix for extension mismatch
        if d.file_path and not os.path.exists(d.file_path):
            base, ext = os.path.splitext(d.file_path)
            if ext != ".mp3":
                potential_path = base + ".mp3"
                if os.path.exists(potential_path):
                    d.file_path = potential_path
                    updated = True

        filename = None
        if d.file_path:
            # Smart path resolution for Docker <-> Local Windows mismatch
            current_path = d.file_path

            # Check if path is valid on current OS
            if not os.path.exists(current_path):
                # Helper to guess relative path from absolute DB path
                # E.g. /downloads/admin/... -> admin/...
                potential_rel = None
                normalized_db_path = d.file_path.replace("\\", "/")

                known_prefixes = ["/downloads/", "/app/downloads/"]
                for prefix in known_prefixes:
                    if normalized_db_path.startswith(prefix):
                        potential_rel = normalized_db_path[len(prefix) :]
                        break

                if potential_rel:
                    # Check if this relative path exists in current DOWNLOAD_DIR
                    candidate = os.path.join(settings.DOWNLOAD_DIR, potential_rel)
                    if os.path.exists(candidate):
                        # Found it! Use this candidate for rel_path calculation
                        current_path = candidate

            try:
                rel_path = os.path.relpath(current_path, settings.DOWNLOAD_DIR).replace("\\", "/")
                if rel_path.startswith(".."):
                    filename = os.path.basename(current_path)
                else:
                    filename = rel_path
            except ValueError:
                # Different drives on Windows
                filename = os.path.basename(current_path)
            except Exception:
                filename = os.path.basename(current_path)

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
                "filename": filename,
            },
        }, updated

    async def get_queue_items(self, db: AsyncSession, user_id: str) -> list[dict]:
        try:
            u_uuid = uuid.UUID(str(user_id))
        except ValueError:
            return []

        # Custom sorting: Downloading first, then Pending/Processing, then others
        status_order = case(
            (Download.status == "downloading", 1),
            (Download.status == "processing", 2),
            (Download.status == "pending", 3),
            else_=4,
        )

        # Filter out archived items
        result = await db.execute(
            select(Download)
            .options(joinedload(Download.track))
            .where(Download.user_id == u_uuid, Download.archived.is_(False))
            .order_by(status_order, Download.created_at.desc())
        )
        downloads = result.scalars().all()

        items = []
        for d in downloads:
            item_data, _ = self._transform_download_item(d)
            items.append(item_data)

        return items


library_data_service = LibraryDataService()
