import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.download import Download
from app.models.watchlist import Watchlist
from app.schemas.download import DownloadCreate
from app.services.download_manager import download_manager
from app.services.spotify_service import spotify_service as _spotify_singleton
from app.services.watchlist import WatchlistItemProcessor, WatchlistStorage
from app.services.youtube_service import YouTubeService

logger = logging.getLogger(__name__)


class WatchlistEngine:
    def __init__(self):
        self.storage = WatchlistStorage()
        # processor initialized lazily or injected?
        # Services are stateless mostly, so we can init them here or lazily
        self._spotify_service = _spotify_singleton
        self._youtube_service = YouTubeService()

    def _to_uuid(self, val: str | uuid.UUID) -> uuid.UUID:
        if isinstance(val, uuid.UUID):
            return val
        return uuid.UUID(str(val))

    async def _handle_download(
        self, db: AsyncSession, user_id: str | uuid.UUID, track_id: str | uuid.UUID, item, track_title: str
    ) -> bool:
        """Handle download logic: restore archived or queue new. Returns True if a download was initiated."""
        user_uuid = self._to_uuid(user_id)
        track_uuid = self._to_uuid(track_id)

        download_exists_result = await db.execute(
            select(Download).where(Download.user_id == user_uuid, Download.track_id == track_uuid)
        )
        existing_download = download_exists_result.scalar_one_or_none()

        if existing_download:
            if existing_download.archived:
                logger.info(f"Restoring archived download: {track_title}")
                existing_download.archived = False
                existing_download.status = "pending"
                existing_download.progress = 0
                existing_download.error_message = None

                await db.commit()
                await download_manager.queue.put(existing_download.id)
                await download_manager.start_worker()
                return True
            return False

        if item.auto_download:
            logger.info(f"Queueing new download: {track_title}")
            playlist_name = item.source_name if item.watch_type == "playlist" else None
            download_data = DownloadCreate(track_id=track_uuid, source=item.source, playlist_name=playlist_name)
            await download_manager.add_download(db, user_uuid, download_data)
            return True

        return False

    async def add_to_watchlist(self, db: AsyncSession, user_id: str | uuid.UUID, item: dict) -> Watchlist:
        logger.info(f"Adding to watchlist: {item}")
        user_uuid = self._to_uuid(user_id)

        # Check if exists
        result = await db.execute(
            select(Watchlist).where(
                Watchlist.user_id == user_uuid,
                Watchlist.source_id == item["source_id"],
                Watchlist.source == item["source"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"Item already exists in watchlist: {existing.id}")
            return existing

        watchlist_item = Watchlist(
            user_id=user_uuid,
            watch_type=item["watch_type"],
            source=item["source"],
            source_id=item["source_id"],
            source_name=item["source_name"],
            auto_download=item.get("auto_download", False),
            metadata_content=item.get("metadata_content")
            or ({"image_url": item.get("image_url")} if item.get("image_url") else {}),
        )
        db.add(watchlist_item)
        await db.commit()
        await db.refresh(watchlist_item)

        if watchlist_item.auto_download:
            try:
                await self.check_for_updates(db, user_uuid)
            except Exception as e:
                logger.error(f"Error triggering auto-download for {watchlist_item.id}: {e}")

        return watchlist_item

    async def get_watchlist(self, db: AsyncSession, user_id: str | uuid.UUID) -> list[Watchlist]:
        user_uuid = self._to_uuid(user_id)
        result = await db.execute(select(Watchlist).where(Watchlist.user_id == user_uuid))
        return list(result.scalars().all())

    async def remove_from_watchlist(self, db: AsyncSession, watchlist_id: str | uuid.UUID, user_id: str | uuid.UUID):
        wl_uuid = self._to_uuid(watchlist_id)
        user_uuid = self._to_uuid(user_id)

        result = await db.execute(select(Watchlist).where(Watchlist.id == wl_uuid, Watchlist.user_id == user_uuid))
        item = result.scalar_one_or_none()
        if item:
            if item.watch_type == "playlist" and item.source_name:
                logger.info(f"Removing pending downloads for playlist: {item.source_name}")
                from sqlalchemy import delete

                from app.models.download import Download

                await db.execute(
                    delete(Download).where(
                        Download.user_id == user_uuid,
                        Download.playlist_name == item.source_name,
                        Download.status == "pending",
                    )
                )

            await db.delete(item)
            await db.commit()
            return True
        return False

    async def update_watchlist_item(
        self, db: AsyncSession, watchlist_id: str | uuid.UUID, user_id: str | uuid.UUID, updates: dict
    ):
        wl_uuid = self._to_uuid(watchlist_id)
        user_uuid = self._to_uuid(user_id)

        result = await db.execute(select(Watchlist).where(Watchlist.id == wl_uuid, Watchlist.user_id == user_uuid))
        item = result.scalar_one_or_none()
        if item:
            for key, value in updates.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            await db.commit()
            await db.refresh(item)
            return item
        return None

    async def check_for_updates(self, db: AsyncSession, user_id: str | uuid.UUID):
        user_uuid = self._to_uuid(user_id)
        logger.info(f"Checking for updates for user {user_uuid}")
        watchlist_items = await self.get_watchlist(db, user_id)
        from app.providers import provider_manager

        processor = WatchlistItemProcessor(
            provider_manager=provider_manager,
            spotify_service=self._spotify_service,
            youtube_service=self._youtube_service,
        )

        new_downloads_count = 0

        for item in watchlist_items:
            logger.info(f"Checking item: {item.source_name} ({item.source_id}) - Auto download: {item.auto_download}")
            try:
                tracks = await processor.fetch_tracks_for_item(item)
                logger.info(f"Found {len(tracks)} tracks for {item.source_name}")

                if not tracks:
                    continue

                if not item.source:
                    continue

                existing_source_ids = await self.storage.get_existing_download_ids(db, user_id, item.source)
                is_legacy_source = item.source in ["spotify", "youtube", "deezer"]

                for track_data in tracks:
                    if track_data["id"] in existing_source_ids:
                        continue

                    track_uuid, _ = await self.storage.get_or_create_track(
                        db, track_data, item.source, is_legacy_source
                    )

                    await self.storage.ensure_watchlist_item_link(db, item.id, track_uuid)

                    if await self._handle_download(db, user_id, track_uuid, item, track_data["title"]):
                        new_downloads_count += 1

            except Exception as e:
                logger.error(f"Error checking updates for {item.id}: {e}")
                import traceback

                logger.error(traceback.format_exc())
                continue

            item.last_checked_at = datetime.now(UTC)
            await db.commit()

        return new_downloads_count


watchlist_engine = WatchlistEngine()
