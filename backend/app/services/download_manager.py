import asyncio
import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.download import Download
from app.models.track import Track
from app.db.database import AsyncSessionLocal
from app.core.config import settings
import yt_dlp

logger = logging.getLogger(__name__)

class DownloadManager:
    def __init__(self):
        self.active_downloads = 0
        self.queue = asyncio.Queue()
        self.processing_task = None

    async def start_worker(self):
        if self.processing_task is None or self.processing_task.done():
            self.processing_task = asyncio.create_task(self.process_queue())

    async def process_queue(self):
        while True:
            download_id = await self.queue.get()
            try:
                await self.process_download(download_id)
            except Exception as e:
                logger.error(f"Error processing download {download_id}: {e}")
            finally:
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
            from sqlalchemy.orm import selectinload
            from app.models.user import User
            result = await db.execute(
                select(Download)
                .options(selectinload(Download.user))
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
                    'status': 'downloading'
                })

                loop = asyncio.get_running_loop()
                final_filename_container = {'path': None}

                def progress_hook(d):
                    if d['status'] == 'downloading':
                        try:
                            p = d.get('_percent_str', '0%').replace('%', '')
                            progress = float(p)
                            asyncio.run_coroutine_threadsafe(
                                socket_manager.emit('download:progress', {
                                    'download_id': str(download_id),
                                    'progress': progress,
                                    'status': 'downloading'
                                }),
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
                        download.file_path = final_filename_container['path']
                    else:
                        download.file_path = f"{settings.DOWNLOAD_DIR}/{output_template}.mp3"

                    await db.commit()
                    
                    import os
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
                logger.error(f"Download failed for {download_id}: {e}", exc_info=True)
                download.status = "failed"
                download.error_message = str(e)
                await db.commit()
                
                await socket_manager.emit('download:error', {
                    'download_id': str(download.id),
                    'error': str(e)
                })

    def _get_ydl_options(self, download: Download, progress_hook):
        ydl_opts = {
            'format': 'bestaudio/best',
            'writethumbnail': True,
            'socket_timeout': 30,
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                {'key': 'FFmpegMetadata', 'add_metadata': True},
                {'key': 'EmbedThumbnail'},
            ],
            'outtmpl': f'{settings.DOWNLOAD_DIR}/%(id)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
        }

        filename_schema = download.user.preferences.get('filename_schema', '{artist} - {title}')
        schema_map = {
            '{artist}': '%(artist)s',
            '{title}': '%(title)s',
            '{album}': '%(album)s',
            '{id}': '%(id)s',
            '{year}': '%(release_date>%Y)s',
            '{track_number}': '%(playlist_index)s',
            '{playlist}': '%(playlist)s',
        }
        
        output_template = filename_schema.replace('{service}', download.source)
        for tag, replacement in schema_map.items():
            output_template = output_template.replace(tag, replacement)
        
        if not output_template or '%' not in output_template:
             output_template = '%(artist)s - %(title)s'

        ydl_opts['outtmpl'] = f'{settings.DOWNLOAD_DIR}/{output_template}.%(ext)s'
        return ydl_opts, output_template

    async def _resolve_url(self, db: AsyncSession, download: Download) -> str:
        if download.source == "youtube":
            return f"https://www.youtube.com/watch?v={download.track_id}"
        elif download.source == "spotify":
            track_info = await self.get_track_info(db, str(download.track_id))
            if track_info:
                search_query = f"{track_info.artist} - {track_info.title}"
                return f"ytsearch1:{search_query}"
        return ""

    async def get_track_info(self, db: AsyncSession, track_id: str) -> Optional[Track]:
        result = await db.execute(select(Track).where(Track.id == track_id))
        return result.scalar_one_or_none()

    async def update_playlist_m3u(self, db: AsyncSession, user_id: str, playlist_name: str):
        try:
            # Get all completed downloads for this playlist
            result = await db.execute(
                select(Download)
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
            
            # Simple heuristic: Use the playlist name as filename
            safe_playlist_name = playlist_name.replace('/', '-').replace('\\', '-')
            playlist_file_path = f"{settings.DOWNLOAD_DIR}/{safe_playlist_name}.m3u8"
            
            # If tracks are in a subfolder (e.g. Spotify/PlaylistName/...), 
            # we might want the m3u8 there too.
            # But since file_path in DB might be absolute or relative, we need to be careful.
            # For now, let's put it in the root download dir for simplicity and reliability.
            
            with open(playlist_file_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                for d in downloads:
                    if d.file_path:
                        # Make path relative to the playlist file if possible
                        # For now, just write the filename/relative path from download dir
                        # Assuming d.file_path is absolute or relative to app root?
                        # Let's assume d.file_path stores the full path as saved in process_download
                        
                        # We need to extract the relative path from DOWNLOAD_DIR
                        # d.file_path is currently: f"{settings.DOWNLOAD_DIR}/{download.track_id}.mp3" (from line 175)
                        # BUT we changed line 151 to use output_template.
                        # We need to update line 175 to reflect the actual path used!
                        
                        # Wait, line 175 in original code was: download.file_path = f"{settings.DOWNLOAD_DIR}/{download.track_id}.mp3"
                        # This is WRONG if we use output_template. 
                        # I need to fix line 175 first to store the correct path.
                        
                        # Assuming line 175 is fixed (I will fix it in next step),
                        # we write the path relative to DOWNLOAD_DIR
                        
                        rel_path = d.file_path.replace(f"{settings.DOWNLOAD_DIR}/", "")
                        f.write(f"#EXTINF:-1,{d.playlist_name} - Track\n") # We don't have title here easily without join
                        f.write(f"{rel_path}\n")
                        
            logger.info(f"Updated playlist {playlist_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to update playlist m3u: {e}")

download_manager = DownloadManager()
