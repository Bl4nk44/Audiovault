from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.watchlist import Watchlist
from typing import List, Optional
from app.services.spotify_service import SpotifyService
from app.services.youtube_service import YouTubeService
from app.services.download_manager import download_manager
from app.models.download import Download
from datetime import datetime
import logging
from app.models.track import Track
from app.models.watchlist_item import WatchlistItem
from app.schemas.download import DownloadCreate
from sqlalchemy import delete, func

logger = logging.getLogger(__name__)

from app.models.track import Track
from app.models.watchlist_item import WatchlistItem
from app.schemas.download import DownloadCreate
from sqlalchemy import delete, func


class WatchlistEngine:
    async def _get_or_create_track(self, db: AsyncSession, track_data: dict, source: str, is_legacy_source: bool) -> tuple[str, bool]:
        """Find or create a track and return its UUID and whether it was created."""
        existing_track = await self._find_existing_track(db, track_data, source)
        
        if existing_track:
            if not is_legacy_source:
                self._update_existing_track_metadata(db, existing_track, track_data, source)
            return existing_track.id, False
        else:
            new_track = self._create_new_track_instance(track_data, source, is_legacy_source)
            db.add(new_track)
            await db.commit()
            await db.refresh(new_track)
            return new_track.id, True

    async def _find_existing_track(self, db: AsyncSession, track_data: dict, source: str) -> Optional[Track]:
        track_query = select(Track)
        if source == 'spotify':
            track_query = track_query.where(Track.spotify_id == track_data['id'])
        elif source == 'youtube':
            track_query = track_query.where(Track.youtube_id == track_data['id'])
        elif source == 'deezer':
            track_query = track_query.where(Track.deezer_id == track_data['id'])
        else:
            track_query = track_query.where(
                Track.title == track_data['title'], 
                Track.artist == track_data['artist']
            )
        result = await db.execute(track_query)
        return result.scalar_one_or_none()

    def _update_existing_track_metadata(self, db: AsyncSession, track: Track, track_data: dict, source: str):
        source_id_key = f"{source}_id"
        meta = dict(track.metadata_content or {})
        if source_id_key not in meta:
            meta[source_id_key] = track_data['id']
            track.metadata_content = meta
            db.add(track)

    def _create_new_track_instance(self, track_data: dict, source: str, is_legacy_source: bool) -> Track:
        meta = {"image_url": track_data.get('image_url')}
        if not is_legacy_source:
            meta[f"{source}_id"] = track_data['id']
            if track_data.get('source_url'):
                meta['source_url'] = track_data.get('source_url')

        track_kwargs = {
            "title": track_data['title'],
            "artist": track_data['artist'],
            "album": track_data.get('album'),
            "duration_ms": track_data.get('duration_ms'),
            "metadata_content": meta
        }
        
        if source == 'spotify':
            track_kwargs['spotify_id'] = track_data['id']
        elif source == 'youtube':
            track_kwargs['youtube_id'] = track_data['id']
        elif source == 'deezer':
            track_kwargs['deezer_id'] = track_data['id']
            
        return Track(**track_kwargs)

    async def _ensure_watchlist_item_link(self, db: AsyncSession, watchlist_id: str, track_id: str):
        """Ensure the link between watchlist and track exists."""
        wl_item_check = await db.execute(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == watchlist_id,
                WatchlistItem.track_id == track_id
            )
        )
        if not wl_item_check.scalar_one_or_none():
            new_wl_item = WatchlistItem(
                watchlist_id=watchlist_id,
                track_id=track_id,
                position=None
            )
            db.add(new_wl_item)
            await db.commit()

    async def _handle_download(self, db: AsyncSession, user_id: str, track_id: str, item, track_title: str) -> bool:
        """Handle download logic: restore archived or queue new. Returns True if a download was initiated."""
        download_exists_result = await db.execute(
            select(Download).where(Download.user_id == user_id, Download.track_id == track_id)
        )
        existing_download = download_exists_result.scalar_one_or_none()
        
        if existing_download:
            if existing_download.archived:
                logger.info(f"Restoring archived download: {track_title}")
                existing_download.archived = False
                existing_download.status = 'pending'
                existing_download.progress = 0
                existing_download.error_message = None
                
                await db.commit()
                await download_manager.queue.put(existing_download.id)
                await download_manager.start_worker()
                return True
            return False
            
        if item.auto_download:
            logger.info(f"Queueing new download: {track_title}")
            playlist_name = item.source_name if item.watch_type == 'playlist' else None
            download_data = DownloadCreate(
                track_id=track_id, 
                source=item.source, 
                playlist_name=playlist_name
            )
            await download_manager.add_download(db, user_id, download_data)
            return True
            
        return False

    async def _fetch_tracks_for_item(self, item, provider_manager, spotify_service, youtube_service) -> list:
        """Fetch tracks from the appropriate provider for a given watchlist item."""
        try:
            if item.watch_type == 'playlist':
                return await self._fetch_playlist_tracks(item, provider_manager)
            elif item.watch_type in ['artist', 'channel']:
                return self._fetch_artist_or_channel_tracks(item, spotify_service, youtube_service)
        except Exception as e:
            logger.error(f"Error fetching tracks for item {item.source_name}: {e}")
        return []

    async def _fetch_playlist_tracks(self, item, provider_manager) -> list:
        provider = provider_manager.get_provider_by_name(item.source)
        if not provider:
            logger.warning(f"No provider found for source: {item.source}")
            return []

        playlist_metadata = await provider.extract_playlist(item.source_id)
        tracks = []
        if playlist_metadata and playlist_metadata.tracks:
            for t in playlist_metadata.tracks:
                tracks.append({
                    "id": t.source_id,
                    "title": t.title,
                    "artist": t.artist,
                    "album": t.album,
                    "duration_ms": t.duration_ms,
                    "image_url": t.image_url,
                    "isrc": t.isrc,
                    "source_url": t.source_url
                })
        return tracks

    def _fetch_artist_or_channel_tracks(self, item, spotify_service, youtube_service) -> list:
        tracks = []
        if item.source == 'spotify':
            albums = spotify_service.get_artist_albums(item.source_id)
            for album in albums:
                album_tracks = spotify_service.get_album_tracks(album['id'])
                tracks.extend(album_tracks)
        elif item.source == 'youtube':
            tracks = youtube_service.get_artist_tracks(item.source_id)
        elif item.source == 'deezer':
             logger.warning(f"Deezer artist fetching not implemented for {item.source_id}")
        return tracks

    async def _get_existing_download_ids(self, db: AsyncSession, user_id: str, source: str) -> set:
        """Get set of source IDs for tracks already downloaded by the user."""
        downloaded_tracks_query = select(Track).join(Download, Download.track_id == Track.id).where(
            Download.user_id == user_id,
            Download.archived == False
        )
        downloaded_tracks_result = await db.execute(downloaded_tracks_query)
        downloaded_tracks = downloaded_tracks_result.scalars().all()
        
        existing_ids = set()
        for t in downloaded_tracks:
            if source == 'spotify' and t.spotify_id:
                existing_ids.add(t.spotify_id)
            elif source == 'youtube' and t.youtube_id:
                existing_ids.add(t.youtube_id)
            elif source == 'deezer' and t.deezer_id:
                existing_ids.add(t.deezer_id)
            else:
                source_id_key = f"{source}_id"
                if t.metadata_content and source_id_key in t.metadata_content:
                    existing_ids.add(t.metadata_content[source_id_key])
        return existing_ids

    async def add_to_watchlist(self, db: AsyncSession, user_id: str, item: dict) -> Watchlist:
        logger.info(f"Adding to watchlist: {item}")
        # Check if exists
        result = await db.execute(
            select(Watchlist).where(
                Watchlist.user_id == user_id,
                Watchlist.source_id == item['source_id'],
                Watchlist.source == item['source']
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"Item already exists in watchlist: {existing.id}")
            return existing

        watchlist_item = Watchlist(
            user_id=user_id,
            watch_type=item['watch_type'],
            source=item['source'],
            source_id=item['source_id'],
            source_name=item['source_name'],
            auto_download=item.get('auto_download', False),
            metadata_content=item.get('metadata_content') or ({'image_url': item.get('image_url')} if item.get('image_url') else {})
        )
        db.add(watchlist_item)
        await db.commit()
        await db.refresh(watchlist_item)

        if watchlist_item.auto_download:
            # Trigger update check immediately for this item
            # We run this in the background or await it? 
            # For responsiveness, we should probably await it or use background tasks, 
            # but since we are in a service, let's just await it for now to ensure it works.
            # Optimization: We could pass the specific item to check_for_updates to avoid checking everything.
            # But check_for_updates iterates all, which is fine for now.
            try:
                await self.check_for_updates(db, user_id)
            except Exception as e:
                logger.error(f"Error triggering auto-download for {watchlist_item.id}: {e}")

        return watchlist_item

    async def get_watchlist(self, db: AsyncSession, user_id: str) -> List[Watchlist]:
        result = await db.execute(select(Watchlist).where(Watchlist.user_id == user_id))
        return result.scalars().all()

    async def remove_from_watchlist(self, db: AsyncSession, watchlist_id: str, user_id: str):
        result = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == user_id))
        item = result.scalar_one_or_none()
        if item:
            # If it's a playlist, remove pending downloads for this playlist
            if item.watch_type == 'playlist' and item.source_name:
                logger.info(f"Removing pending downloads for playlist: {item.source_name}")
                # We match by playlist_name. Note: source_name in Watchlist corresponds to playlist_name in Download
                from app.models.download import Download
                # Delete pending downloads
                # Note: We need to be careful not to delete downloads that are already processing/downloading/completed
                # But user requested "zanim ona skonczy sie pobierac usunie ja... to zeby to sie odswiezyło"
                # So we should probably remove pending ones.
                
                # Using delete statement directly
                from sqlalchemy import delete
                await db.execute(
                    delete(Download).where(
                        Download.user_id == user_id,
                        Download.playlist_name == item.source_name,
                        Download.status == 'pending'
                    )
                )
            
            await db.delete(item)
            await db.commit()
            return True
        return False

    async def update_watchlist_item(self, db: AsyncSession, watchlist_id: str, user_id: str, updates: dict):
        result = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == user_id))
        item = result.scalar_one_or_none()
        if item:
            for key, value in updates.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            await db.commit()
            await db.refresh(item)
            return item
        return None

    async def check_for_updates(self, db: AsyncSession, user_id: str):
        logger.info(f"Checking for updates for user {user_id}")
        watchlist_items = await self.get_watchlist(db, user_id)
        from app.providers import provider_manager
        

        # Legacy services initialization
        spotify_service = SpotifyService()
        youtube_service = YouTubeService()
        
        new_downloads_count = 0
        
        for item in watchlist_items:
            logger.info(f"Checking item: {item.source_name} ({item.source_id}) - Auto download: {item.auto_download}")
            try:
                tracks = await self._fetch_tracks_for_item(item, provider_manager, spotify_service, youtube_service)
                logger.info(f"Found {len(tracks)} tracks for {item.source_name}")
                
                if not tracks:
                    continue

                existing_source_ids = await self._get_existing_download_ids(db, user_id, item.source)
                is_legacy_source = item.source in ['spotify', 'youtube', 'deezer']
                
                for track_data in tracks:

                    if track_data['id'] in existing_source_ids:
                        continue
                    
                    track_uuid, _ = await self._get_or_create_track(db, track_data, item.source, is_legacy_source)
                    
                    await self._ensure_watchlist_item_link(db, item.id, track_uuid)
                    
                    if await self._handle_download(db, user_id, track_uuid, item, track_data['title']):
                        new_downloads_count += 1
            
            except Exception as e:
                logger.error(f"Error checking updates for {item.id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue
                
            from datetime import timezone
            item.last_checked_at = datetime.now(timezone.utc)
            await db.commit()
            
        return new_downloads_count



watchlist_engine = WatchlistEngine()
