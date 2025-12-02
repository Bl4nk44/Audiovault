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
        if self.processing_task is None:
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

    async def add_download(self, db: AsyncSession, user_id: str, track_id: str, source: str) -> Download:
        download = Download(
            user_id=user_id,
            track_id=track_id,
            source=source,
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
            result = await db.execute(select(Download).where(Download.id == download_id))
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

                def progress_hook(d):
                    if d['status'] == 'downloading':
                        try:
                            p = d.get('_percent_str', '0%').replace('%', '')
                            progress = float(p)
                            
                            # Schedule async emit
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

                ydl_opts = {
                    'format': 'bestaudio/best',
                    'writethumbnail': True,
                    'postprocessors': [
                        {
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        },
                        {
                            'key': 'FFmpegMetadata',
                            'add_metadata': True,
                        },
                        {
                            'key': 'EmbedThumbnail',
                        },
                    ],
                    'outtmpl': f'{settings.DOWNLOAD_DIR}/%(id)s.%(ext)s',
                    'progress_hooks': [progress_hook],
                    'quiet': True,
                    'no_warnings': True,
                }

                # Construct URL based on source
                url = ""
                if download.source == "youtube":
                    url = f"https://www.youtube.com/watch?v={download.track_id}"
                elif download.source == "spotify":
                    track_info = await self.get_track_info(db, str(download.track_id))
                    if track_info:
                        search_query = f"{track_info.artist} - {track_info.title}"
                        url = f"ytsearch1:{search_query}"
                
                if url:
                    # Run blocking download in executor
                    await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))
                    
                    download.status = "completed"
                    download.progress = 100
                    download.completed_at = datetime.utcnow()
                    # Note: We might need to find the actual file if ytsearch was used
                    download.file_path = f"{settings.DOWNLOAD_DIR}/{download.track_id}.mp3" 
                    await db.commit()
                    
                    await socket_manager.emit('download:completed', {
                        'download_id': str(download.id),
                        'filename': f"{download.track_id}.mp3"
                    })
                else:
                    raise Exception("Could not resolve download URL")
                
            except Exception as e:
                logger.error(f"Download failed: {e}")
                download.status = "failed"
                download.error_message = str(e)
                await db.commit()
                
                await socket_manager.emit('download:error', {
                    'download_id': str(download.id),
                    'error': str(e)
                })

    async def get_track_info(self, db: AsyncSession, track_id: str) -> Optional[Track]:
        result = await db.execute(select(Track).where(Track.id == track_id))
        return result.scalar_one_or_none()

download_manager = DownloadManager()
