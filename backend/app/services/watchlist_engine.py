from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.watchlist import Watchlist
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
        
        # Legacy services for Artist support (until providers support artists)
        spotify_service = SpotifyService()
        youtube_service = YouTubeService()
        from app.services.deezer_service import DeezerService
        deezer_service = DeezerService()
        
        new_downloads_count = 0
        
        for item in watchlist_items:
            logger.info(f"Checking item: {item.source_name} ({item.source_id}) - Auto download: {item.auto_download}")
            try:
                tracks = []
                provider = provider_manager.get_provider_by_name(item.source)
                
                # Fetch tracks logic
                if item.watch_type == 'playlist':
                    if provider:
                        # For new services, source_id might be a URL. Providers handle both IDs and URLs usually.
                        playlist_metadata = await provider.extract_playlist(item.source_id)
                        if playlist_metadata and playlist_metadata.tracks:
                            # Convert TrackMetadata to dicts if needed, or use objects
                            # The loop below expects dicts currently (track_data['id'])
                            # Let's standardize on using TrackMetadata objects or dicts.
                            # Existing logic uses dicts. Let's convert metadata to dicts.
                            for t in playlist_metadata.tracks:
                                tracks.append({
                                    "id": t.source_id,
                                    "title": t.title,
                                    "artist": t.artist,
                                    "album": t.album,
                                    "duration_ms": t.duration_ms,
                                    "image_url": t.image_url,
                                    "isrc": t.isrc,
                                    "source_url": t.source_url # Important for direct download (SoundCloud)
                                })
                    else:
                         logger.warning(f"No provider found for source: {item.source}")

                elif item.watch_type in ['artist', 'channel']:
                    # Fallback to legacy service calls for Artists as Provider interface doesn't support them yet
                    if item.source == 'spotify':
                        albums = spotify_service.get_artist_albums(item.source_id)
                        for album in albums:
                             album_tracks = spotify_service.get_album_tracks(album['id'])
                             tracks.extend(album_tracks)
                    elif item.source == 'youtube':
                         tracks = youtube_service.get_artist_tracks(item.source_id)
                    elif item.source == 'deezer':
                         # Deezer artist implementation missing in original code, skipping or keeping what might be added
                         pass
                
                logger.info(f"Found {len(tracks)} tracks for {item.source_name}")
                
                if not tracks:
                    continue

                from app.models.track import Track
                
                # Get all downloaded tracks for this user (to avoid re-downloading things user already has)
                downloaded_tracks_query = select(Track).join(Download, Download.track_id == Track.id).where(
                    Download.user_id == user_id,
                    Download.archived == False
                )
                downloaded_tracks_result = await db.execute(downloaded_tracks_query)
                downloaded_tracks = downloaded_tracks_result.scalars().all()
                
                # Create a set of existing IDs for the current source
                existing_source_ids = set()
                
                # Determine identification logic
                is_legacy_source = item.source in ['spotify', 'youtube', 'deezer']
                
                for t in downloaded_tracks:
                    if item.source == 'spotify' and t.spotify_id:
                        existing_source_ids.add(t.spotify_id)
                    elif item.source == 'youtube' and t.youtube_id:
                        existing_source_ids.add(t.youtube_id)
                    elif item.source == 'deezer' and t.deezer_id:
                        existing_source_ids.add(t.deezer_id)
                    else:
                        # For new services, check metadata_content
                        # We store e.g. 'soundcloud_id' or 'apple_music_id' in metadata
                        source_id_key = f"{item.source}_id"
                        if t.metadata_content and source_id_key in t.metadata_content:
                            existing_source_ids.add(t.metadata_content[source_id_key])
                
                for track_data in tracks:
                    # logger.info(f"Processing track: {track_data.get('title')} ({track_data.get('id')})")
                    if track_data['id'] in existing_source_ids:
                        # logger.info("Skipped (in existing_source_ids)")
                        continue
                    
                    # Check if track exists in DB (globally)
                    track_query = select(Track)
                    if item.source == 'spotify':
                        track_query = track_query.where(Track.spotify_id == track_data['id'])
                    elif item.source == 'youtube':
                        track_query = track_query.where(Track.youtube_id == track_data['id'])
                    elif item.source == 'deezer':
                        track_query = track_query.where(Track.deezer_id == track_data['id'])
                    else:
                        # JSON query for new sources
                        # Postgres/SQLite compatible way via text cast or simple retrieval?
                        # Since we don't have many tracks, we could verify after retrieval if query is complex.
                        # But let's try to use JSON operator if possible.
                        # SQLite JSON is valid.
                        # track_query = track_query.where(func.json_extract(Track.metadata_content, f'$.{item.source}_id') == track_data['id'])
                        source_id_key = f"{item.source}_id"
                        # Fallback: We might not be able to easily query JSON in generic way without native JSON type support details in Alembic/SQLAlchemy for this project.
                        # Safest approach: Don't check global DB for valid deduplication on new services? 
                        # OR: Retrieve duplicates by title/artist?
                        # Let's try basic title/artist match to minimize duplicates?
                        # No, that's risky.
                        # Let's skip global DB check for new services for now OR fetch potential candidates.
                        # Actually, if we just create a new track, it's fine. 
                        # But we duplicate tracks.
                        # Let's try to match by exact title + artist.
                        track_query = track_query.where(
                            Track.title == track_data['title'], 
                            Track.artist == track_data['artist']
                        )
                        
                    track_result = await db.execute(track_query)
                    existing_track = track_result.scalar_one_or_none()
                    
                    track_uuid = None
                    if existing_track:
                        # If found by title/artist, update the ID in metadata if missing
                        if not is_legacy_source:
                            source_id_key = f"{item.source}_id"
                            meta = dict(existing_track.metadata_content or {})
                            if source_id_key not in meta:
                                meta[source_id_key] = track_data['id']
                                existing_track.metadata_content = meta
                                db.add(existing_track) # Update
                        track_uuid = existing_track.id
                    else:
                        # Create track
                        # Prepare metadata
                        meta = {"image_url": track_data.get('image_url')}
                        # Add source ID to metadata for new serivces
                        if not is_legacy_source:
                             meta[f"{item.source}_id"] = track_data['id']
                             # Store direct source_url if available (SoundCloud)
                             if track_data.get('source_url'):
                                 meta['source_url'] = track_data['source_url']

                        track_kwargs = {
                            "title": track_data['title'],
                            "artist": track_data['artist'],
                            "album": track_data.get('album'),
                            "duration_ms": track_data.get('duration_ms'),
                            "metadata_content": meta
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
                    
                    # Ensure WatchlistItem exists (Self-healing Reference Count)
                    from app.models.watchlist_item import WatchlistItem
                    
                    # Check if connection exists
                    wl_item_check = await db.execute(
                        select(WatchlistItem).where(
                            WatchlistItem.watchlist_id == item.id,
                            WatchlistItem.track_id == track_uuid
                        )
                    )
                    existing_wl_item = wl_item_check.scalar_one_or_none()
                    
                    if not existing_wl_item:
                        new_wl_item = WatchlistItem(
                            watchlist_id=item.id,
                            track_id=track_uuid,
                            position=None # We could store position from playlist_metadata if available
                        )
                        db.add(new_wl_item)
                        await db.commit()
                    
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
