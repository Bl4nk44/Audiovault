import asyncio
import os
import logging
from typing import Optional
from datetime import datetime, timezone
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import update
from app.models.download import Download
from app.models.track import Track
from app.db.database import AsyncSessionLocal
from app.core.config import settings
import yt_dlp
from app.schemas.download import DownloadCreate

from app.services.fallback_service import fallback_service
from app.services.socket_manager import socket_manager
from app.utils.sanitization import sanitize_filename

logger = logging.getLogger(__name__)

class DownloadPausedError(Exception):
    pass

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
                raise # Re-raise to ensure proper task cancellation propagation
            except Exception as e:
                logger.error(f"Error processing download {download_id}: {e}")
            finally:
                self.active_tasks.pop(download_id, None)
                self.queue.task_done()




    async def restart_all_downloads(self, db: AsyncSession, user_id: str):
        """Restart all failed, cancelled, or error downloads for a user."""
        logger.info(f"Restarting all failed downloads for user {user_id}")
        
        # 1. Select relevant downloads
        result = await db.execute(
            select(Download).where(
                Download.user_id == user_id,
                Download.status.in_(['failed', 'cancelled', 'error', 'paused'])
            )
        )
        downloads = result.scalars().all()
        
        count = 0
        for download in downloads:
            # Reset metadata
            download.status = 'pending'
            download.progress = 0
            download.error_message = None
            download.retry_count = 0
            
            # Re-queue
            await self.queue.put(download.id)
            count += 1
            
        if count > 0:
            await db.commit()
            logger.info(f"Restarted {count} downloads")
            await self.start_worker()
            
        return count

    def pause_download(self, download_id: str):
        self.paused_downloads.add(download_id)
        # If it's currently running, we can't easily stop yt-dlp except via the hook exception
        # The hook will raise exception and process_download will catch it and update DB
        logger.info(f"Requested pause for {download_id}")

    async def resume_pending_downloads(self, db: AsyncSession):
        """Resume downloads that were pending or interrupted during restart."""
        logger.info("Checking for pending downloads to resume...")
        try:
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
        except Exception as e:
            logger.error(f"Failed to resume pending downloads: {e}")
            # Do not re-raise, allow app to start
            pass

    async def add_download(self, db: AsyncSession, user_id: str, download_data: 'DownloadCreate') -> Download:
        download = Download(
            user_id=user_id,
            track_id=str(download_data.track_id),
            source=download_data.source,
            playlist_name=download_data.playlist_name,
            status="pending"
        )
        db.add(download)
        await db.commit()
        await db.refresh(download)
        
        await self.queue.put(download.id)
        # Ensure worker is running
        await self.start_worker()
        
        return download

    async def _notify_start(self, download):
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

    async def _handle_completion(self, db, download, final_filename_container, output_template):
        download.status = "completed"
        download.progress = 100
        download.completed_at = datetime.now(timezone.utc)
        
        self._set_download_file_path(download, final_filename_container, output_template)
        self._fix_filename_artifacts(download)

        logger.info(f"💾 Saving file for user '{download.user.username}' to: {download.file_path}")
        await db.commit()
        
        await self._notify_completion(download)

        if download.playlist_name:
            await self.update_playlist_m3u(db, download.user_id, download.playlist_name)

    def _set_download_file_path(self, download, final_filename_container, output_template):
        if final_filename_container['path']:
            base, ext = os.path.splitext(final_filename_container['path'])
            if ext != '.mp3':
                download.file_path = base + '.mp3'
            else:
                download.file_path = final_filename_container['path']
        else:
            download_path = download.user.preferences.get('downloadPath')
            if not download_path:
                download_path = os.path.join(settings.DOWNLOAD_DIR, download.user.username)
            
            if not os.path.exists(download_path):
                os.makedirs(download_path, exist_ok=True)

            download.file_path = os.path.join(download_path, f"{output_template}.mp3")

    def _fix_filename_artifacts(self, download):
        if download.file_path and os.path.exists(download.file_path):
            directory, filename = os.path.split(download.file_path)
            if filename.startswith("NA -"):
                 new_filename = filename[4:].strip()
                 if len(new_filename) > 0:
                      new_path = os.path.join(directory, new_filename)
                      try:
                          os.rename(download.file_path, new_path)
                          download.file_path = new_path
                          logger.info(f"Renamed file to remove NA prefix: {filename} -> {new_filename}")
                      except Exception as e:
                          logger.warning(f"Failed to rename NA file: {e}")

    async def _notify_completion(self, download):
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

    async def _handle_error(self, db, download, e):
        if isinstance(e, DownloadPausedError) or str(e) == "DOWNLOAD_PAUSED":
            logger.info(f"Download {download.id} paused by user")
            download.status = "paused"
            await db.commit()
            await socket_manager.emit('download:paused', {'download_id': str(download.id)})
            return

        logger.error(f"Download failed for {download.id}: {e}", exc_info=True)
        download.status = "failed"
        download.error_message = str(e)
        # Increment retry count
        download.retry_count = (download.retry_count or 0) + 1
        await db.commit()
        
        await socket_manager.emit('download:error', {
            'download_id': str(download.id),
            'error': str(e)
        })

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
                await self._mark_download_started(db, download)
                
                loop = asyncio.get_running_loop()
                final_filename_container = {'path': None}

                progress_hook = self._create_progress_hook(download_id, download, loop, final_filename_container)
                ydl_opts, output_template = self._get_ydl_options(download, progress_hook)
                
                url = await self._resolve_url(db, download)
                
                if url:
                    await self._execute_download_task(loop, ydl_opts, url, download_id)
                    await self._handle_completion(db, download, final_filename_container, output_template)
                else:
                    raise Exception("Could not resolve download URL")
                
            except Exception as e:
                await self._handle_error(db, download, e)

    async def _mark_download_started(self, db, download):
        download.status = "downloading"
        download.started_at = datetime.now(timezone.utc)
        await db.commit()
        await self._notify_start(download)

    async def _notify_processing(self, download):
        await socket_manager.emit('download:processing', {
            'download_id': str(download.id),
            'status': 'processing'
        })

    def _create_progress_hook(self, download_id, download, loop, final_filename_container):
        def progress_hook(d):
            if d['status'] == 'downloading':
                if download_id in self.paused_downloads:
                    raise DownloadPausedError("DOWNLOAD_PAUSED")
                self._handle_progress_update(d, download_id, download, loop)
            elif d['status'] == 'finished':
                try:
                    logger.info(f"Download finished: {d['filename']}. Starting conversion/processing...")
                    
                    # Update status to processing in DB
                    asyncio.run_coroutine_threadsafe(
                        self._set_processing_status(download_id),
                        loop
                    )
                    
                    final_filename_container['path'] = d['filename']
                except Exception as e:
                    logger.error(f"Finished hook error: {e}")
        return progress_hook

    async def _set_processing_status(self, download_id):
        try:
             async with AsyncSessionLocal() as db:
                result = await db.execute(select(Download).where(Download.id == download_id))
                download = result.scalar_one_or_none()
                if download:
                    download.status = 'processing'
                    download.progress = 100
                    await db.commit()
                    await self._notify_processing(download)
        except Exception as e:
            logger.error(f"Failed to set processing status: {e}")

    def _handle_progress_update(self, d, download_id, download, loop):
        try:
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            
            if total_bytes:
                progress = (downloaded / total_bytes) * 100
            else:
                p = d.get('_percent_str', '0%').replace('%', '')
                progress = float(p)
            
            # Cap at 99% during downloading phase
            if progress >= 100:
                progress = 99.9
            
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
                }),
                loop
            )

            # Throttle DB updates - explicitly check last update time or just modulo? 
            # Modulo on progress is okay but for large files it might be too frequent or too sparse.
            # Let's stick to simple modulo for now, but maybe 2% steps?
            if int(progress) % 5 == 0:
                asyncio.run_coroutine_threadsafe(
                    self.update_progress_db(download_id, progress),
                    loop
                )
        except Exception as e:
            logger.error(f"Progress hook error: {e}")

    async def _execute_download_task(self, loop, ydl_opts, url, download_id):
        logger.info(f"Starting download for {download_id} from URL: {url}")
        # Run blocking download in executor
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))
        logger.info(f"Download finished for {download_id}")

    async def pause_download_async(self, download_id: str):
         # Renaming to avoid conflict if necessary, but actually the previous one was sync (line 133)
         # and this one is async (line 362). 
         # Line 133: def pause_download(self, download_id: str): -> Sync
         # Line 362: async def pause_download(self, download_id: str): -> Async
         # The issue says "implementation equivalent".
         # The sync one sets the flag. The async one does the same + logs.
         # Let's keep one unified async method if possible, or alias.
         # Since this is "async def", and the other "def", check usage.
         return self.pause_download(download_id)

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
        
        logger.info(f"Processing download {download.id} with schema: '{filename_schema}'")

        output_template = filename_schema.replace('{service}', download.source)
        
        # Pre-process playlist tag manually
        PLAYLIST_TAG = '{playlist}'
        if PLAYLIST_TAG in output_template:
            playlist_val = download.playlist_name
            if playlist_val:
                # Sanitize to avoid accidental subdirs and OS restricted chars
                playlist_val = sanitize_filename(playlist_val)
            else:
                playlist_val = ""
            
            output_template = output_template.replace(PLAYLIST_TAG, playlist_val)
            # Cleanup double slashes if playlist was empty
            output_template = output_template.replace('//', '/')

        for tag, replacement in schema_map.items():
            if tag == PLAYLIST_TAG:
                continue # Handled above
            output_template = output_template.replace(tag, replacement)
        
        if not output_template or '%' not in output_template:
             logger.warning(f"Output template '{output_template}' invalid or missing tags. Fallback to default.")
             output_template = '%(artist)s - %(title)s'

        # Correct key is 'download_path' (snake_case) as stored in DB settings.py
        download_path = download.user.preferences.get('download_path')
        if not download_path:
            # Default to user subdirectory
            download_path = os.path.join(settings.DOWNLOAD_DIR, download.user.username)
        
        logger.info(f"Resolved base download path: {download_path}")

        # Ensure directory exists
        if not os.path.exists(download_path):
            try:
                os.makedirs(download_path, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory {download_path}: {e}")
                download_path = settings.DOWNLOAD_DIR

        final_outtmpl = f'{download_path}/{output_template}.%(ext)s'
        # Normalize slashes for OS
        final_outtmpl = os.path.normpath(final_outtmpl).replace('\\', '/')
        
        logger.info(f"Final yt-dlp outtmpl: {final_outtmpl}")
        ydl_opts['outtmpl'] = final_outtmpl
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
            return ""
            
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
            
            async with aiofiles.open(playlist_file_path, 'w', encoding='utf-8') as f:
                await f.write("#EXTM3U\n")
                for d in downloads:
                    if d.file_path:
                        rel_path = d.file_path.replace(f"{download_path}/", "")
                        await f.write(f"#EXTINF:-1,{d.playlist_name} - Track\n")
                        await f.write(f"{rel_path}\n")
                        
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
            downloads = await self._get_playlist_downloads(db, user_id, source, playlist_name)
            
            if not downloads:
                 logger.info(f"No downloads found for playlist {playlist_name} ({source})")
                 return

            self._delete_physical_files(downloads)
            self._cleanup_empty_directory(downloads, playlist_name)
            
            await self._delete_db_records(db, downloads)
            
            logger.info(f"Deleted playlist {playlist_name} for user {user_id}")

        except Exception as e:
            logger.error(f"Error deleting playlist {playlist_name}: {e}")
            raise e

    async def _get_playlist_downloads(self, db: AsyncSession, user_id, source, playlist_name):
        result = await db.execute(
            select(Download).where(
                Download.user_id == user_id,
                Download.source == source,
                Download.playlist_name == playlist_name
            )
        )
        return result.scalars().all()

    def _delete_physical_files(self, downloads):
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

    def _cleanup_empty_directory(self, downloads, playlist_name):
        # 3. Clean up empty directory (heuristic)
        if downloads and downloads[0].file_path:
             parent_dir = os.path.dirname(downloads[0].file_path)
             # Check if this dir name matches playlist name normalized
             safe_playlist_name = playlist_name.replace('/', '-').replace('\\', '-')
             if safe_playlist_name in os.path.basename(parent_dir):
                  # Try to remove dir if empty
                  try:
                      os.rmdir(parent_dir)
                      logger.info(f"Removed empty directory {parent_dir}")
                  except Exception as e:
                      logger.debug(f"Failed to remove directory {parent_dir}: {e}")

    async def _delete_db_records(self, db, downloads):
        # 4. Delete DB records
        for download in downloads:
            await db.delete(download)
        await db.commit()

download_manager = DownloadManager()
