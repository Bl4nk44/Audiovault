from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.watchlist import Watchlist
from app.models.schemas import UserCreate
from typing import List
from app.services.spotify_service import SpotifyService
from app.services.youtube_service import YouTubeService
from app.services.download_manager import download_manager
from app.models.download import Download
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class WatchlistEngine:
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
            metadata_content={'image_url': item.get('image_url')} if item.get('image_url') else {}
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
        spotify_service = SpotifyService()
        youtube_service = YouTubeService()
        
        new_downloads_count = 0
        
        for item in watchlist_items:
            logger.info(f"Checking item: {item.source_name} ({item.source_id}) - Auto download: {item.auto_download}")
            try:
                tracks = []
                if item.source == 'spotify':
                    if item.watch_type == 'playlist':
                        tracks = spotify_service.get_playlist_tracks(item.source_id)
                    elif item.watch_type == 'artist':
                        albums = spotify_service.get_artist_albums(item.source_id)
                        for album in albums:
                             album_tracks = spotify_service.get_album_tracks(album['id'])
                             tracks.extend(album_tracks)
                elif item.source == 'youtube':
                    if item.watch_type == 'playlist':
                         tracks = youtube_service.get_playlist_tracks(item.source_id)
                    elif item.watch_type == 'artist' or item.watch_type == 'channel':
                         tracks = youtube_service.get_artist_tracks(item.source_id)
                
                logger.info(f"Found {len(tracks)} tracks for {item.source_name}")
                
                if not tracks:
                    continue

                # Note: Download.track_id is UUID of the Track model.
                # We need to check if we have downloaded this track based on the source ID.
                # Since Track model uses specific columns (spotify_id, youtube_id), we need to check those.
                
                from app.models.track import Track
                from sqlalchemy import or_
                
                # Get all downloaded tracks for this user (excluding archived ones)
                downloaded_tracks_query = select(Track).join(Download, Download.track_id == Track.id).where(
                    Download.user_id == user_id,
                    Download.archived == False
                )
                downloaded_tracks_result = await db.execute(downloaded_tracks_query)
                downloaded_tracks = downloaded_tracks_result.scalars().all()
                
                # Create a set of existing IDs for the current source
                existing_source_ids = set()
                for t in downloaded_tracks:
                    if item.source == 'spotify' and t.spotify_id:
                        existing_source_ids.add(t.spotify_id)
                    elif item.source == 'youtube' and t.youtube_id:
                        existing_source_ids.add(t.youtube_id)
                    elif item.source == 'deezer' and t.deezer_id:
                        existing_source_ids.add(t.deezer_id)
                
                for track_data in tracks:
                    logger.info(f"Processing track: {track_data.get('title')} ({track_data.get('id')})")
                    if track_data['id'] in existing_source_ids:
                        logger.info("Skipped (in existing_source_ids)")
                        continue
                    
                    # Check if track exists in DB (globally)
                    track_query = select(Track)
                    if item.source == 'spotify':
                        track_query = track_query.where(Track.spotify_id == track_data['id'])
                    elif item.source == 'youtube':
                        track_query = track_query.where(Track.youtube_id == track_data['id'])
                    elif item.source == 'deezer':
                        track_query = track_query.where(Track.deezer_id == track_data['id'])
                        
                    track_result = await db.execute(track_query)
                    existing_track = track_result.scalar_one_or_none()
                    
                    track_uuid = None
                    if existing_track:
                        track_uuid = existing_track.id
                    else:
                        # Create track
                        track_kwargs = {
                            "title": track_data['title'],
                            "artist": track_data['artist'],
                            "album": track_data.get('album'),
                            "duration_ms": track_data.get('duration_ms'),
                            "metadata_content": {"image_url": track_data.get('image_url')}
                        }
                        
                        if item.source == 'spotify':
                            track_kwargs['spotify_id'] = track_data['id']
                        elif item.source == 'youtube':
                            track_kwargs['youtube_id'] = track_data['id']
                        elif item.source == 'deezer':
                            track_kwargs['deezer_id'] = track_data['id']
                            
                        new_track = Track(**track_kwargs)
                        db.add(new_track)
                        await db.commit()
                        await db.refresh(new_track)
                        track_uuid = new_track.id
                    
                    # Double check download existence for this user
                    download_exists_result = await db.execute(
                        select(Download).where(Download.user_id == user_id, Download.track_id == track_uuid)
                    )
                    existing_download = download_exists_result.scalar_one_or_none()
                    
                    if existing_download:
                        logger.info(f"Found existing download: {existing_download.id}, archived={existing_download.archived}, status={existing_download.status}")
                        if existing_download.archived:
                            # Restore archived download
                            logger.info(f"Restoring archived download: {track_data['title']}")
                            existing_download.archived = False
                            existing_download.status = 'pending'
                            existing_download.progress = 0
                            existing_download.error_message = None
                            
                            await db.commit()
                            await download_manager.queue.put(existing_download.id)
                            # Ensure worker is running
                            await download_manager.start_worker()
                            new_downloads_count += 1
                        continue 
                        
                    if item.auto_download:
                        logger.info(f"Queueing new download: {track_data['title']}")
                        playlist_name = item.source_name if item.watch_type == 'playlist' else None
                        await download_manager.add_download(db, user_id, track_uuid, item.source, playlist_name=playlist_name)
                        new_downloads_count += 1
            
            except Exception as e:
                logger.error(f"Error checking updates for {item.id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue
                
            item.last_checked_at = datetime.utcnow()
            await db.commit()
            
        return new_downloads_count

watchlist_engine = WatchlistEngine()
