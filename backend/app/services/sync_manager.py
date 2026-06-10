import logging
import os
import shutil
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.models.download import Download
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.providers import provider_manager
from app.services.spotify_service import SpotifyService  # noqa: F401
from app.services.youtube_service import YouTubeService

logger = logging.getLogger(__name__)


class SyncManager:
    def __init__(self):
        self._pending_reports = {}  # Token -> Report Data

    def _to_uuid(self, val: str | UUID) -> UUID:
        if isinstance(val, UUID):
            return val
        return UUID(str(val))

    def _is_track_in_remote(self, track, watchlist: Watchlist, remote_ids: set) -> bool:
        if watchlist.source == "spotify" and track.spotify_id in remote_ids:
            return True
        if watchlist.source == "youtube" and track.youtube_id in remote_ids:
            return True
        if track.metadata_content and f"{watchlist.source}_id" in track.metadata_content:
            return track.metadata_content[f"{watchlist.source}_id"] in remote_ids
        return False

    def _compute_safety_warning(self, remove_count: int, local_count: int, remote_ids: set) -> tuple[bool, str | None]:
        if local_count > 10 and len(remote_ids) == 0:
            return True, "Remote playlist is empty but local has tracks. Possible API error."
        if local_count > 0 and (remove_count / local_count) > 0.10:
            return True, f"High deletion ratio detected ({int(remove_count / local_count * 100)}%). Please verify."
        if remove_count > 20:
            return True, f"Massive deletion detected ({remove_count} tracks). Verification required."
        return False, None

    async def analyze_watchlist(self, db: AsyncSession, user_id: str | UUID, watchlist_id: str | UUID) -> dict:
        """
        Analyzes a watchlist for synchronization.
        Returns a report containing items to add, remove, and safety warnings.
        Does NOT modify the database (Dry-Run).
        """
        w_uuid = UUID(watchlist_id) if isinstance(watchlist_id, str) else watchlist_id
        u_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        result = await db.execute(select(Watchlist).where(Watchlist.id == w_uuid, Watchlist.user_id == u_uuid))
        watchlist = result.scalar_one_or_none()

        if not watchlist:
            raise ValueError("Watchlist not found")

        remote_tracks = await self._fetch_remote_tracks(watchlist)
        if not remote_tracks and watchlist.watch_type == "playlist":
            logger.warning(f"Remote playlist {watchlist.source_name} seems empty.")

        remote_ids = {t["id"] for t in remote_tracks}

        local_items_result = await db.execute(
            select(WatchlistItem)
            .options(joinedload(WatchlistItem.track))
            .where(WatchlistItem.watchlist_id == watchlist_id)
        )
        local_items = local_items_result.scalars().all()
        local_count = len(local_items)

        to_keep_uuids: set = set()
        to_delete_candidates = []

        for item in local_items:
            track = item.track
            if not track:
                continue
            if self._is_track_in_remote(track, watchlist, remote_ids):
                to_keep_uuids.add(track.id)
            else:
                to_delete_candidates.append(
                    {
                        "track_id": str(track.id),
                        "title": track.title,
                        "artist": track.artist,
                        "reason": "Missing from remote source",
                    }
                )

        remove_count = len(to_delete_candidates)
        safety_warning, warning_message = self._compute_safety_warning(remove_count, local_count, remote_ids)

        sync_token = str(uuid4())
        report = {
            "watchlist_id": str(watchlist.id),
            "watchlist_name": watchlist.source_name,
            "local_count": local_count,
            "remote_count": len(remote_tracks),
            "to_add_count": len(remote_tracks) - len(to_keep_uuids),
            "to_remove_count": remove_count,
            "to_remove_items": to_delete_candidates,
            "safety_warning": safety_warning,
            "warning_message": warning_message,
            "sync_token": sync_token,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        self._pending_reports[sync_token] = report
        return report

    async def _remove_download_if_unreferenced(self, db: AsyncSession, u_uuid: UUID, track_uuid: UUID) -> int:
        ref_result = await db.execute(
            select(func.count(WatchlistItem.id))
            .join(Watchlist)
            .where(Watchlist.user_id == u_uuid, WatchlistItem.track_id == track_uuid)
        )
        ref_count = ref_result.scalar()
        if ref_count:
            return 0
        d_result = await db.execute(select(Download).where(Download.user_id == u_uuid, Download.track_id == track_uuid))
        download = d_result.scalar_one_or_none()
        if not download:
            return 0
        deleted = 0
        if download.file_path and os.path.exists(download.file_path):
            if self._soft_delete_file(download.file_path):
                deleted = 1
        await db.delete(download)
        return deleted

    async def execute_sync(
        self,
        db: AsyncSession,
        user_id: str | UUID,
        sync_token: str,
        approved_removals: list[str],
    ):
        """
        Executes the sync based on approval.
        approved_removals: List of Track UUIDs to remove.
        """
        if sync_token not in self._pending_reports:
            raise ValueError("Invalid or expired sync token")

        report = self._pending_reports[sync_token]
        watchlist_id = self._to_uuid(report["watchlist_id"])
        u_uuid = self._to_uuid(user_id)

        removed_count = 0
        soft_deleted_files = 0

        for t_id in approved_removals:
            track_uuid = self._to_uuid(t_id)
            await db.execute(
                delete(WatchlistItem).where(
                    WatchlistItem.watchlist_id == watchlist_id,
                    WatchlistItem.track_id == track_uuid,
                )
            )
            soft_deleted_files += await self._remove_download_if_unreferenced(db, u_uuid, track_uuid)
            removed_count += 1

        await db.commit()
        del self._pending_reports[sync_token]

        return {
            "status": "success",
            "removed_from_playlist": removed_count,
            "files_soft_deleted": soft_deleted_files,
        }

    def _soft_delete_file(self, file_path: str) -> bool:
        """
        Moves file to .trash directory instead of deleting.
        """
        try:
            trash_dir = os.path.join(settings.DOWNLOAD_DIR, ".trash")
            os.makedirs(trash_dir, exist_ok=True)

            filename = os.path.basename(file_path)
            # Add timestamp to avoid collisions
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_name = f"{ts}_{filename}"
            dest_path = os.path.join(trash_dir, dest_name)

            shutil.move(file_path, dest_path)
            logger.info(f"Soft deleted file: {file_path} -> {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to soft delete {file_path}: {e}")
            return False

    async def auto_sync_all_deletions(
        self,
        db: AsyncSession,
        user_id: str | UUID,
        only_auto: bool = True,
    ) -> dict:
        """
        Runs analyze + execute for playlist watchlists.
        only_auto=True  → only items with auto_sync_deletions=True (scheduler use)
        only_auto=False → all playlist items (manual "Sync All" button)
        Skips items that trigger a safety warning.
        """
        u_uuid = self._to_uuid(user_id)
        result = await db.execute(
            select(Watchlist).where(
                Watchlist.user_id == u_uuid,
                Watchlist.watch_type == "playlist",
            )
        )
        watchlists = result.scalars().all()

        synced = []
        skipped = []

        for wl in watchlists:
            if only_auto and not wl.auto_sync_deletions:
                continue
            try:
                report = await self.analyze_watchlist(db, u_uuid, wl.id)
                if report["safety_warning"]:
                    skipped.append({"watchlist_name": wl.source_name, "reason": report["warning_message"]})
                    del self._pending_reports[report["sync_token"]]
                    continue
                if report["to_remove_count"] == 0:
                    del self._pending_reports[report["sync_token"]]
                    synced.append({"watchlist_name": wl.source_name, "removed_count": 0, "files_deleted": 0})
                    continue
                approved = [i["track_id"] for i in report["to_remove_items"]]
                exec_result = await self.execute_sync(db, u_uuid, report["sync_token"], approved)
                synced.append(
                    {
                        "watchlist_name": wl.source_name,
                        "removed_count": exec_result["removed_from_playlist"],
                        "files_deleted": exec_result["files_soft_deleted"],
                    }
                )
            except Exception as e:
                logger.error(f"auto_sync_deletions failed for {wl.source_name}: {e}")
                skipped.append({"watchlist_name": wl.source_name, "reason": str(e)})

        return {"synced": synced, "skipped": skipped}

    async def _fetch_playlist_tracks(self, item: Watchlist) -> list[dict]:
        if not item.source:
            return []
        provider = provider_manager.get_provider_by_name(item.source)
        if not (provider and item.source_id):
            return []
        playlist_metadata = await provider.extract_playlist(item.source_id)
        if not (playlist_metadata and playlist_metadata.tracks):
            return []
        return [{"id": t.source_id, "title": t.title, "artist": t.artist} for t in playlist_metadata.tracks]

    async def _fetch_artist_tracks(self, item: Watchlist) -> list[dict]:
        if item.source == "spotify" and item.source_id:
            spotify_svc = SpotifyService()
            albums = await spotify_svc.get_artist_albums(item.source_id)
            tracks = []
            for album in albums:
                tracks.extend(await spotify_svc.get_album_tracks(album["id"]))
            return tracks
        if item.source == "youtube" and item.source_id:
            return YouTubeService().get_artist_tracks(item.source_id)
        return []

    async def _fetch_remote_tracks(self, item: Watchlist) -> list[dict]:
        """Fetch remote tracks using Providers."""
        try:
            if item.watch_type == "playlist" and item.source:
                return await self._fetch_playlist_tracks(item)
            if item.watch_type in ["artist", "channel"]:
                return await self._fetch_artist_tracks(item)
        except Exception as e:
            logger.error(f"Error fetching remote tracks: {e}")
        return []


sync_manager = SyncManager()
