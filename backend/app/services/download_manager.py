import asyncio
import os
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.download import Download
from app.models.track import Track
from app.db.database import AsyncSessionLocal
from app.core.config import settings
import yt_dlp

from app.services.fallback_service import fallback_service

logger = logging.getLogger(__name__)

class DownloadManager:
    def __init__(self):
        self.active_downloads = 0
        self.queue = asyncio.Queue()
        self.processing_task = None
        self.paused_downloads = set() # Set of download IDs that are paused
        self.active_tasks = {} # Map download_id -> asyncio.Task

    async def start_worker(self):
        if self.processing_task is None or self.processing_task.done():
            self.processing_task = asyncio.create_task(self.process_queue())

    async def process_queue(self):
        while True:
            download_id = await self.queue.get()
            if download_id in self.paused_downloads:
                self.queue.task_done()
                continue
            
            # Create a task for this download to allow cancellation/pause
            task = asyncio.create_task(self.process_download(download_id))
            self.active_tasks[download_id] = task
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Download task {download_id} cancelled")
            except Exception as e:
                logger.error(f"Error processing download {download_id}: {e}")
            finally:
                self.active_tasks.pop(download_id, None)
                self.queue.task_done()

    async def resume_pending_downloads(self, db: AsyncSession):
        """Resume downloads that were pending or interrupted during restart."""
        logger.info("Checking for pending downloads to resume...")
        result = await db.execute(
            select(Download).where(
                Download.status.in_(['pending', 'downloading', 'processing'])
            )
        )
        pending_downloads = result.scalars().all()
        
        count = 0
        for download in pending_downloads:
            # Reset status to pending if it was downloading/processing to ensure clean retry
            if download.status in ['downloading', 'processing']:
                download.status = 'pending'
                download.progress = 0
                
            await self.queue.put(download.id)
            count += 1
            
        if count > 0:
            await db.commit()
            logger.info(f"Resumed {count} pending downloads")
            await self.start_worker()
        else:
            logger.info("No pending downloads found")

    async def add_download(self, db: AsyncSession, user_id: str, track_id: str, source: str, playlist_name: str = None) -> Download:
        download = Download(
            user_id=user_id,
            track_id=track_id,
            source=source,
            playlist_name=playlist_name,
            status="pending"
        )
        db.add(download)
        await db.commit()
        await db.refresh(download)
        
        await self.queue.put(download.id)
        # Ensure worker is running
        await self.start_worker()
        
        return download

    async def process_download(self, download_id: str):
        async with AsyncSessionLocal() as db:
            # Eager load user to get preferences
            result = await db.execute(
                select(Download)
                .options(selectinload(Download.user), selectinload(Download.track))
                .where(Download.id == download_id)
            )
            download = result.scalar_one_or_none()
            
            if not download:
                return

            try:
                from app.services.socket_manager import socket_manager
                
                # Update status to downloading
                download.status = "downloading"
                download.started_at = datetime.utcnow()
                await db.commit()
                
                # Notify start
                await socket_manager.emit('download:progress', {
                    'download_id': str(download.id),
                    'progress': 0,
                    'status': 'downloading',
                    'track': {
                        'title': download.track.title,
                        'artist': download.track.artist,
                        'image_url': download.track.metadata_content.get('image_url') if download.track.metadata_content else None
                    }
                })

                loop = asyncio.get_running_loop()
                final_filename_container = {'path': None}

                def progress_hook(d):
                    if d['status'] == 'downloading':
                        # Check if paused (this is a bit hacky for yt-dlp, relying on raising exception to stop)
                        if download_id in self.paused_downloads:
                            raise Exception("DOWNLOAD_PAUSED")

                        try:
                            p = d.get('_percent_str', '0%').replace('%', '')
                            progress = float(p)
                            # Update progress in DB every 5% or so to avoid spamming DB? 
                            # tracking internal state might be better
                            
                            asyncio.run_coroutine_threadsafe(
                                socket_manager.emit('download:progress', {
                                    'download_id': str(download_id),
                                    'progress': progress,
                                    'status': 'downloading',
                                    'track': {
                                        'title': download.track.title,
                                        'artist': download.track.artist,
                                        'image_url': download.track.metadata_content.get('image_url') if download.track.metadata_content else None
                                    }
                                    }
                                ),
                                loop
                            )

                            # Update DB periodically (every ~5%) to support polling fallback
                            # We can't do async db commit here easily in sync hook
                            # But we can verify if we should fire a separate async task to update DB
                            if progress % 5 == 0:
                                asyncio.run_coroutine_threadsafe(
                                    self.update_progress_db(download_id, progress),
                                    loop
                                )
                        except Exception as e:
                            logger.error(f"Progress hook error: {e}")
                    elif d['status'] == 'finished':
                        try:
                            logger.info(f"Download finished: {d['filename']}")
                            final_filename_container['path'] = d['filename']
                        except Exception as e:
                            logger.error(f"Finished hook error: {e}")

                ydl_opts, output_template = self._get_ydl_options(download, progress_hook)
                url = await self._resolve_url(db, download)
                
                if url:
                    logger.info(f"Starting download for {download_id} from URL: {url}")
                    # Run blocking download in executor
                    await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))
                    logger.info(f"Download finished for {download_id}")
                    
                    download.status = "completed"
                    download.progress = 100
                    download.completed_at = datetime.utcnow()
                    
                    if final_filename_container['path']:
                        # Ensure extension matches the converted format (mp3)
                        base, ext = os.path.splitext(final_filename_container['path'])
                        if ext != '.mp3':
                            download.file_path = base + '.mp3'
                        else:
                            download.file_path = final_filename_container['path']
                    else:
                        download_path = download.user.preferences.get('downloadPath')
                        if not download_path:
                            # Default to user subdirectory
                            download_path = os.path.join(settings.DOWNLOAD_DIR, download.user.username)
                            if not os.path.exists(download_path):
                                os.makedirs(download_path, exist_ok=True)
                        elif not os.path.exists(download_path):
                             # Create custom path if it doesn't exist (optional safety)
                             os.makedirs(download_path, exist_ok=True)

                        download.file_path = os.path.join(download_path, f"{output_template}.mp3")

                    # Post-processing: Fix "NA" artifacts from yt-dlp (common when artist metadata is missing)
                    if download.file_path and os.path.exists(download.file_path):
                        directory, filename = os.path.split(download.file_path)
                        # Check for "NA -" prefix
                        if filename.startswith("NA -"):
                             new_filename = filename[4:].strip() # Remove "NA -"
                             if len(new_filename) > 0:
                                  new_path = os.path.join(directory, new_filename)
                                  try:
                                      os.rename(download.file_path, new_path)
                                      download.file_path = new_path
                                      logger.info(f"Renamed file to remove NA prefix: {filename} -> {new_filename}")
                                  except Exception as e:
                                      logger.warning(f"Failed to rename NA file: {e}")

                    logger.info(f"💾 Saving file for user '{download.user.username}' to: {download.file_path}")
                    await db.commit()
                    

                    actual_filename = os.path.basename(download.file_path) if download.file_path else f"{download.track_id}.mp3"

                    await socket_manager.emit('download:completed', {
                        'download_id': str(download.id),
                        'filename': actual_filename,
                        'track': {
                            'title': download.track.title,
                            'artist': download.track.artist,
                            'image_url': download.track.metadata_content.get('image_url') if download.track.metadata_content else None
                        }
                    })

                    if download.playlist_name:
                        await self.update_playlist_m3u(db, download.user_id, download.playlist_name)
                else:
                    raise Exception("Could not resolve download URL")
                
            except Exception as e:
                if str(e) == "DOWNLOAD_PAUSED":
                    logger.info(f"Download {download_id} paused by user")
                    download.status = "paused"
                    await db.commit()
                    await socket_manager.emit('download:paused', {'download_id': str(download.id)})
                    return

                logger.error(f"Download failed for {download_id}: {e}", exc_info=True)
                download.status = "failed"
                download.error_message = str(e)
                # Increment retry count
                download.retry_count = (download.retry_count or 0) + 1
                await db.commit()
                
                await socket_manager.emit('download:error', {
                    'download_id': str(download.id),
                    'error': str(e)
                })

    async def pause_download(self, download_id: str):
        self.paused_downloads.add(download_id)
        # If it's currently running, we can't easily stop yt-dlp except via the hook exception
        # The hook will raise exception and process_download will catch it and update DB
        logger.info(f"Requested pause for {download_id}")

    async def resume_download(self, db: AsyncSession, download_id: str):
        if download_id in self.paused_downloads:
            self.paused_downloads.remove(download_id)
        
        # Check current status
        result = await db.execute(select(Download).where(Download.id == download_id))
        download = result.scalar_one_or_none()
        
        if download and download.status in ['paused', 'failed', 'pending']:
            download.status = 'pending'
            await db.commit()
            await self.queue.put(download.id)
            await self.start_worker()
            logger.info(f"Resumed download {download_id}")

    async def cancel_download(self, db: AsyncSession, download_id: str):
        # Remove from pause list if there
        if download_id in self.paused_downloads:
            self.paused_downloads.remove(download_id)
            
        # Cancel active task if exists
        if download_id in self.active_tasks:
            self.active_tasks[download_id].cancel()
            
        result = await db.execute(select(Download).where(Download.id == download_id))
        download = result.scalar_one_or_none()
        
        if download:
            await db.delete(download)
            await db.commit()
            logger.info(f"Cancelled and deleted download {download_id}")
            
            from app.services.socket_manager import socket_manager
            await socket_manager.emit('download:cancelled', {'download_id': download_id})

    async def retry_download(self, db: AsyncSession, download_id: str):
        await self.resume_download(db, download_id)

    def _get_ydl_options(self, download: Download, progress_hook):
        quality_setting = download.user.preferences.get('quality', 'high')
        quality_map = {
            'low': '128',
            'normal': '192',
            'high': '320', # Let's bump high to 320
            'best': '320'
        }
        bitrate = quality_map.get(quality_setting, '192')

        ydl_opts = {
            'format': 'bestaudio/best',
            'writethumbnail': True,
            'socket_timeout': 30,
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': bitrate},
                {'key': 'FFmpegMetadata', 'add_metadata': True},
                {'key': 'EmbedThumbnail'},
            ],
            'outtmpl': f'{settings.DOWNLOAD_DIR}/%(id)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'quiet': True,
            'no_warnings': True,
        }



        schema_map = {
            '{artist}': '%(artist|uploader|creator)s', # Try hard to find an artist-like string
            '{title}': '%(title)s',
            '{album}': '%(album|Single)s',
            '{id}': '%(id)s',
            '{year}': '%(release_date>%Y|Unknown)s',
            '{track_number}': '%(playlist_index)s',
            '{user}': download.user.username,
        }
        # Updated default schema as requested
        filename_schema = download.user.preferences.get('filename_schema', '{artist} - {title}')
        
        output_template = filename_schema.replace('{service}', download.source)
        if not output_template or '%' not in output_template:
             # This fallback seems redundant if we set a robust default above, but good for safety.
             # Use the new default structure as fallback too
             output_template = '%(artist)s - %(title)s'

        # Pre-process playlist tag manually because yt-dlp might not know it (e.g. single track form Spotify)
        if '{playlist}' in output_template:
            playlist_val = download.playlist_name
            if playlist_val:
                # Sanitize to avoid accidental subdirs
                playlist_val = playlist_val.replace('/', '-').replace('\\', '-')
            else:
                # If no playlist, we remove the {playlist} tag and any preceding slash to avoid empty folder
                # Simple approach: replace with empty string. 
                # Better approach: if schema is .../{playlist}/... -> ...//... -> .../...
                playlist_val = ""
            
            output_template = output_template.replace('{playlist}', playlist_val)
            # Cleanup double slashes if playlist was empty
            output_template = output_template.replace('//', '/')

        for tag, replacement in schema_map.items():
            if tag == '{playlist}': continue # Handled above
            output_template = output_template.replace(tag, replacement)
        
        if not output_template or '%' not in output_template:
             output_template = '%(artist)s - %(title)s'

        download_path = download.user.preferences.get('downloadPath')
        if not download_path:
            # Default to user subdirectory
            download_path = os.path.join(settings.DOWNLOAD_DIR, download.user.username)
        
        # Ensure directory exists
        if not os.path.exists(download_path):
            try:
                os.makedirs(download_path, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory {download_path}: {e}")
                # Fallback to root if creation fails (though unlikely if permissions are ok)
                download_path = settings.DOWNLOAD_DIR

        ydl_opts['outtmpl'] = f'{download_path}/{output_template}.%(ext)s'
        return ydl_opts, output_template

    async def _resolve_url(self, db: AsyncSession, download: Download) -> str:
        # Check retry count to determine attempt number
        attempt = (download.retry_count or 0) + 1
        
        # Get Track info for metadata access
        track_info = None
        if download.track_id:
             track_info = await self.get_track_info(db, str(download.track_id))
        
        # Get instruction from FallbackService
        instruction = fallback_service.get_fallback_instruction(download.source, attempt, track_info)
        logger.info(f"Fallback instruction for {download.source} (Attempt {attempt}): {instruction}")
        
        resp_type = instruction.get('type')
        value = instruction.get('value')
        
        if resp_type == 'yt_search':
            return f"ytsearch1:{value}"
            
        elif resp_type == 'sc_search':
            return f"scsearch1:{value}"
            
        elif resp_type == 'direct_youtube':
            # Original logic for direct YT
            url = f"https://www.youtube.com/watch?v={download.track_id}"
            return url
            

                
        elif resp_type == 'direct_soundcloud':
            if track_info and track_info.source_url:
                 # Check if we have source_url in metadata
                 # Actually track_info might handle metadata_content
                 meta = track_info.metadata_content or {}
                 url = meta.get('source_url') or track_info.source_url # track model has source_url column? No, generic
                 # Track model usually has source_url if we look at updated models? 
                 # Let's rely on stored metadata or re-reconstruction logic if ID is URL.
                 
                 # If download.track_id looks like URL, use it
                 if "soundcloud.com" in str(download.track_id):
                     return str(download.track_id)
                 
                 if url: 
                     return url
            
            # Fallback to search if direct fails/missing
            if track_info:
                return f"scsearch1:{track_info.artist} - {track_info.title}"
            return None
            
        elif resp_type == 'none':
            # Try default legacy logic if no instruction covers it (shouldn't happen with new logic covering all known sources)
            # Default for imports etc.
            if track_info:
                 return f"ytsearch1:{track_info.artist} - {track_info.title}"
        
        return ""

    async def get_track_info(self, db: AsyncSession, track_id: str) -> Optional[Track]:
        result = await db.execute(select(Track).where(Track.id == track_id))
        return result.scalar_one_or_none()

    async def update_playlist_m3u(self, db: AsyncSession, user_id: str, playlist_name: str):
        try:
            # Get all completed downloads for this playlist
            result = await db.execute(
                select(Download)
                .options(selectinload(Download.user))
                .where(
                    Download.user_id == user_id,
                    Download.playlist_name == playlist_name,
                    Download.status == "completed"
                )
                .order_by(Download.created_at) # Preserve order of addition
            )
            downloads = result.scalars().all()
            
            if not downloads:
                return

            # Determine playlist file path
            # We try to put it in the same folder as the first track if possible, 
            # otherwise in the root download dir
            
            download_path = downloads[0].user.preferences.get('downloadPath')
            if not download_path:
                 download_path = os.path.join(settings.DOWNLOAD_DIR, downloads[0].user.username)
            if not download_path: # Fallback just in case
                 download_path = settings.DOWNLOAD_DIR

            # Simple heuristic: Use the playlist name as filename
            safe_playlist_name = playlist_name.replace('/', '-').replace('\\', '-')
            playlist_file_path = f"{download_path}/{safe_playlist_name}.m3u8"
            
            with open(playlist_file_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                for d in downloads:
                    if d.file_path:
                        rel_path = d.file_path.replace(f"{download_path}/", "")
                        f.write(f"#EXTINF:-1,{d.playlist_name} - Track\n")
                        f.write(f"{rel_path}\n")
                        
            logger.info(f"Updated playlist {playlist_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to update playlist m3u: {e}")


    async def update_progress_db(self, download_id: str, progress: float):
        """Update download progress in DB to support polling fallback"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Download).where(Download.id == download_id))
                download = result.scalar_one_or_none()
                
                if download:
                    download.progress = progress
                    await db.commit()
        except Exception as e:
            logger.error(f"Failed to update progress in DB for {download_id}: {e}")

    async def delete_playlist(self, db: AsyncSession, user_id: str, source: str, playlist_name: str):
        """Delete an entire playlist, including files and DB records."""
        try:
            # 1. Get all downloads for this playlist
            result = await db.execute(
                select(Download).where(
                    Download.user_id == user_id,
                    Download.source == source,
                    Download.playlist_name == playlist_name
                )
            )
            downloads = result.scalars().all()
            
            if not downloads:
                 logger.info(f"No downloads found for playlist {playlist_name} ({source})")
                 return

            # 2. Delete files
            for download in downloads:
                if download.file_path and os.path.exists(download.file_path):
                    try:
                        os.remove(download.file_path)
                    except Exception as e:
                        logger.error(f"Failed to delete file {download.file_path}: {e}")
                
                # Also remove from active tasks if downloading
                if download.id in self.active_tasks:
                     self.active_tasks[download.id].cancel()
                     self.active_tasks.pop(download.id, None)

            # 3. Clean up empty directory (heuristic)
            # Assuming files are in DOWNLOAD_DIR/Artist - Title.mp3 or similar flat structure, 
            # or grouped by playlist if schema was used.
            # If files were in a folder named after the playlist, try to remove it.
            # We check the directory of the first download.
            if downloads and downloads[0].file_path:
                 parent_dir = os.path.dirname(downloads[0].file_path)
                 # Check if this dir name matches playlist name normalized
                 safe_playlist_name = playlist_name.replace('/', '-').replace('\\', '-')
                 if safe_playlist_name in os.path.basename(parent_dir):
                      # Try to remove dir if empty
                      try:
                          os.rmdir(parent_dir)
                          logger.info(f"Removed empty directory {parent_dir}")
                      except Exception:
                          pass # Not empty or other error

            # 4. Delete DB records
            for download in downloads:
                await db.delete(download)
            
            await db.commit()
            logger.info(f"Deleted playlist {playlist_name} for user {user_id}")

        except Exception as e:
            logger.error(f"Error deleting playlist {playlist_name}: {e}")
            raise e

download_manager = DownloadManager()
