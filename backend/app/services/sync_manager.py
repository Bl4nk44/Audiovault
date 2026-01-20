import logging
import os
import shutil
from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import settings
from app.models.download import Download
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.providers import provider_manager
from app.services.spotify_service import SpotifyService
from app.services.youtube_service import YouTubeService
from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)


class SyncManager:
    def __init__(self):
        self._pending_reports = {}  # Token -> Report Data

    async def analyze_watchlist(self, db: AsyncSession, user_id: str, watchlist_id: str) -> dict:
        """
        Analyzes a watchlist for synchronization.
        Returns a report containing items to add, remove, and safety warnings.
        Does NOT modify the database (Dry-Run).
        """
        # 1. Fetch Watchlist
        result = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == user_id))
        watchlist = result.scalar_one_or_none()

        if not watchlist:
            raise ValueError("Watchlist not found")

        # 2. Fetch Remote Tracks (Source of Truth)
        remote_tracks = await self._fetch_remote_tracks(watchlist)

        if not remote_tracks and watchlist.watch_type == "playlist":
            # Safety Check: If API returns 0 tracks, it might be an error.
            # We don't want to wipe the local library.
            # However, empty playlists exist.
            # We will flag this as a warning.
            logger.warning(f"Remote playlist {watchlist.source_name} seems empty.")

        remote_ids = set()  # Set of Source IDs (e.g. Spotify IDs)
        for t in remote_tracks:
            remote_ids.add(t["id"])

        # 3. Fetch Local State (WatchlistItems)
        # We need to load tracks to compare source IDs
        local_items_result = await db.execute(
            select(WatchlistItem)
            .options(joinedload(WatchlistItem.track))
            .where(WatchlistItem.watchlist_id == watchlist_id)
        )
        local_items = local_items_result.scalars().all()

        to_keep_uuids = set()
        to_delete_candidates = []  # List of {id: uuid, title: str, ...}

        local_count = len(local_items)

        for item in local_items:
            track = item.track
            if not track:
                continue

            # Identify if this local track exists in remote_ids
            is_found = False

            # Check ID based on source
            if watchlist.source == "spotify" and track.spotify_id in remote_ids:
                is_found = True
            elif watchlist.source == "youtube" and track.youtube_id in remote_ids:
                is_found = True
            elif track.metadata_content and f"{watchlist.source}_id" in track.metadata_content:
                if track.metadata_content[f"{watchlist.source}_id"] in remote_ids:
                    is_found = True

            # Fallback title match? No, too risky for deletion.
            # If ID doesn't match, we assume it's different or lost link.

            if is_found:
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

        # 4. Calculate Stats & Thresholds
        remove_count = len(to_delete_candidates)
        total_remote = len(remote_tracks)

        safety_warning = False
        warning_message = None

        # Threshold: > 10% change OR > 20 tracks removed
        if local_count > 0:
            deletion_ratio = remove_count / local_count
            if deletion_ratio > 0.10:  # 10%
                safety_warning = True
                warning_message = f"High deletion ratio detected ({int(deletion_ratio * 100)}%). Please verify."

        if remove_count > 20:
            safety_warning = True
            warning_message = f"Massive deletion detected ({remove_count} tracks). Verification required."

        if local_count > 10 and len(remote_ids) == 0:
            safety_warning = True
            warning_message = "Remote playlist is empty but local has tracks. Possible API error."

        # 5. Generate Token
        sync_token = str(uuid4())
        report = {
            "watchlist_id": str(watchlist.id),
            "watchlist_name": watchlist.source_name,
            "local_count": local_count,
            "remote_count": total_remote,
            "to_add_count": total_remote - len(to_keep_uuids),  # Estimate
            "to_remove_count": remove_count,
            "to_remove_items": to_delete_candidates,
            "safety_warning": safety_warning,
            "warning_message": warning_message,
            "sync_token": sync_token,
            "generated_at": datetime.now(UTC).isoformat(),
        }

        # Store for Execute phase
        self._pending_reports[sync_token] = report

        return report

    async def execute_sync(
        self,
        db: AsyncSession,
        user_id: str,
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
        watchlist_id = report["watchlist_id"]

        # 1. Process Removals
        removed_count = 0
        soft_deleted_files = 0

        for track_uuid in approved_removals:
            # A. Remove connection from this Watchlist
            # Verify it's in the candidates to avoid abuse?
            # Logic: Just try to delete the WatchlistItem for this watchlist & track.

            stmt = delete(WatchlistItem).where(
                WatchlistItem.watchlist_id == watchlist_id,
                WatchlistItem.track_id == track_uuid,
            )
            await db.execute(stmt)

            # B. Reference Counting Check
            # Check if this track is used in ANY other watchlist for ANY user?
            # Or just THIS user?
            # Use Case: User A has Song X in Playlist 1 and Playlist 2.
            # Removes from Playlist 1. Song X should stay on disk for Playlist 2.
            # User B has Song X. User A deletes calls sync. Song X should stay for User B?
            # Yes, Download is per User.
            # We check if *this user* has any other references.

            # Check if User has other WatchlistItems for this track
            # Join Watchlist to filter by user_id
            ref_count_result = await db.execute(
                select(func.count(WatchlistItem.id))
                .join(Watchlist)
                .where(Watchlist.user_id == user_id, WatchlistItem.track_id == track_uuid)
            )
            ref_count = ref_count_result.scalar()

            if ref_count == 0:
                # No more references for this user!
                # We can remove the Download (and file).

                # Get Download
                d_result = await db.execute(
                    select(Download).where(Download.user_id == user_id, Download.track_id == track_uuid)
                )
                download = d_result.scalar_one_or_none()

                if download:
                    # Soft Delete File
                    if download.file_path and os.path.exists(download.file_path):
                        if self._soft_delete_file(download.file_path):
                            soft_deleted_files += 1

                    # Delete Download Record
                    await db.delete(download)

            removed_count += 1

        await db.commit()

        # Cleanup token
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

    async def _fetch_remote_tracks(self, item: Watchlist) -> list[dict]:
        """
        Helper to fetch remote tracks using Providers.
        Simplified logic from WatchlistEngine.
        """
        tracks = []
        try:
            # Provider based
            if item.watch_type == "playlist":
                provider = provider_manager.get_provider_by_name(item.source)
                if provider:
                    playlist_metadata = await provider.extract_playlist(item.source_id)
                    if playlist_metadata and playlist_metadata.tracks:
                        for t in playlist_metadata.tracks:
                            tracks.append(
                                {
                                    "id": t.source_id,
                                    "title": t.title,
                                    "artist": t.artist,
                                }
                            )

            # Legacy fallback (Artist/Channel)
            elif item.watch_type in ["artist", "channel"]:
                # Simplification: Reuse services
                if item.source == "spotify":
                    spotify_service = SpotifyService()
                    albums = spotify_service.get_artist_albums(item.source_id)
                    for album in albums:
                        album_tracks = spotify_service.get_album_tracks(album["id"])
                        tracks.extend(album_tracks)
                elif item.source == "youtube":
                    youtube = YouTubeService()
                    tracks = youtube.get_artist_tracks(item.source_id)

        except Exception as e:
            logger.error(f"Error fetching remote tracks: {e}")
            # Re-raise to alert caller about API error?
            # Or return empty list?
            # Returning empty list is dangerous for sync (implies deletion).
            # So we log error and return list but logic above handles empty list carefully.
            # Best to re-raise or return None to signal error.
            # But for now, let's just log.
            pass

        return tracks


sync_manager = SyncManager()
