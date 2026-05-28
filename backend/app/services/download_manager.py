import asyncio
import logging
import os
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import aiofiles
import yt_dlp
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.cache import cache_manager
from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.models.download import Download
from app.models.track import Track
from app.schemas.download import DownloadCreate
from app.services.fallback_service import fallback_service
from app.services.socket_manager import socket_manager
from app.utils.sanitization import sanitize_filename

logger = logging.getLogger(__name__)


class DownloadPausedError(Exception):
    pass


class DownloadManager:
    DEFAULT_CONCURRENT_DOWNLOADS = 3

    def __init__(self):
        self.active_downloads = 0
        self.queue: asyncio.Queue = asyncio.Queue()
        self.processing_task = None
        self.paused_downloads = set()  # Set of download IDs that are paused
        self.active_tasks = {}  # Map download_id -> asyncio.Task
        self._background_tasks: set[asyncio.Task] = set()  # prevent GC of fire-and-forget tasks
        # Per-user semaphores for concurrent download limits
        self.user_semaphores: dict[str, asyncio.Semaphore] = {}

    def get_user_semaphore(self, user_id: str, max_concurrent: int | None = None) -> asyncio.Semaphore:
        """Get or create a semaphore for a specific user."""
        if max_concurrent is None:
            max_concurrent = self.DEFAULT_CONCURRENT_DOWNLOADS

        if user_id not in self.user_semaphores:
            self.user_semaphores[user_id] = asyncio.Semaphore(max_concurrent)
        return self.user_semaphores[user_id]

    def update_user_concurrency(self, user_id: str, max_concurrent: int):
        """Update concurrency limit for a user (creates new semaphore)."""
        self.user_semaphores[user_id] = asyncio.Semaphore(max_concurrent)

    def _ensure_permissions(self, path: str, is_file: bool = False):
        """
        Force permissions on created files/directories to ensure access for other services (e.g. Jellyfin).
        Dir: 777 (rwxrwxrwx), File: 666 (rw-rw-rw-)
        """
        try:
            mode = 0o666 if is_file else 0o777  # nosemgrep: insecure-file-permissions
            mode = 0o666 if is_file else 0o777  # nosec B103 - intentional for Docker interop with Jellyfin/Plex
            os.chmod(path, mode)  # nosemgrep: insecure-file-permissions
        except Exception as e:
            # On Windows this might fail or have limited effect, but we log warning only
            logger.debug(f"Could not set permissions on {path}: {e}")

    async def start_worker(self):  # NOSONAR
        if self.processing_task is None or self.processing_task.done():
            self.processing_task = asyncio.create_task(self.process_queue())

    async def process_queue(self):
        while True:
            download_id = await self.queue.get()
            if download_id in self.paused_downloads:
                self.queue.task_done()
                continue

            # Store task reference to prevent premature garbage collection
            task = asyncio.create_task(self._process_with_semaphore(download_id))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def _process_with_semaphore(self, download_id: str):
        """Wrapper that acquires per-user semaphore before processing download."""
        # First, ensure download_id is UUID for DB query
        try:
            d_uuid = uuid.UUID(str(download_id))
        except ValueError:
            self.queue.task_done()
            return

        # First, get user_id and their concurrency preference
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Download).options(selectinload(Download.user)).where(Download.id == d_uuid)
            )
            download = result.scalar_one_or_none()

            if not download:
                self.queue.task_done()
                return

            user_id = str(download.user_id)
            max_concurrent = self.DEFAULT_CONCURRENT_DOWNLOADS

            if download.user and download.user.preferences:
                max_concurrent = download.user.preferences.get(
                    "max_parallel_downloads", self.DEFAULT_CONCURRENT_DOWNLOADS
                )

        # Get or create user semaphore
        semaphore = self.get_user_semaphore(user_id, max_concurrent)

        async with semaphore:
            # Create a task for this download to allow cancellation/pause
            task = asyncio.create_task(self.process_download(download_id))
            self.active_tasks[download_id] = task
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Download task {download_id} cancelled")
                raise  # Re-raise CancelledError per asyncio contract
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
                Download.user_id == user_id, Download.status.in_(["failed", "cancelled", "error", "paused"])
            )
        )
        downloads = result.scalars().all()

        count = 0
        for download in downloads:
            # Reset metadata
            download.status = "pending"
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
                select(Download).where(Download.status.in_(["pending", "downloading", "processing"]))
            )
            pending_downloads = result.scalars().all()

            count = 0
            for download in pending_downloads:
                # Reset status to pending if it was downloading/processing to ensure clean retry
                if download.status in ["downloading", "processing"]:
                    download.status = "pending"
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

    async def add_download(self, db: AsyncSession, user_id: str | uuid.UUID, download_data: DownloadCreate) -> Download:
        download = Download(
            user_id=user_id,
            track_id=download_data.track_id,
            source=download_data.source,
            playlist_id=download_data.playlist_id,
            playlist_name=download_data.playlist_name,
            status="pending",
        )
        db.add(download)
        await db.commit()
        await db.refresh(download)

        await self.queue.put(download.id)
        # Ensure worker is running
        await self.start_worker()

        return download

    async def _notify_start(self, download):
        await socket_manager.emit(
            "download:progress",
            {
                "download_id": str(download.id),
                "progress": 0,
                "status": "downloading",
                "track": {
                    "title": download.track.title,
                    "artist": download.track.artist,
                    "image_url": download.track.metadata_content.get("image_url")
                    if download.track.metadata_content
                    else None,
                },
            },
        )

    async def _update_track_from_file(self, db, download) -> None:
        if not (download.file_path and os.path.exists(download.file_path)):
            return
        try:
            from app.services.library_scanner import library_scanner_service

            title, artist, album, genre, duration_ms, _ = library_scanner_service._parse_audio_metadata_sync(
                download.file_path
            )
            if not download.track:
                return
            download.track.title = title
            download.track.artist = artist
            download.track.album = album
            if duration_ms > 0:
                download.track.duration_ms = duration_ms
            meta = download.track.metadata_content or {}
            if genre:
                meta["genre"] = genre
            if "source" not in meta:
                meta["source"] = download.source
            artist_id, album_id = await library_scanner_service.resolve_artist_and_album(db, artist, album)
            download.track.artist_id = artist_id
            download.track.album_id = album_id
            download.track.metadata_content = meta
            db.add(download.track)
            logger.info(
                f"Updated Track metadata for {download.track.id}: {title} - {artist} [Duration: {duration_ms}ms]"
            )
        except Exception as e:
            logger.error(f"Failed to update track metadata from file: {e}")

    async def _handle_completion(self, db, download, final_filename_container, output_template):
        download.status = "completed"
        download.progress = 100
        download.completed_at = datetime.now(UTC)

        self._set_download_file_path(
            download, final_filename_container, output_template, getattr(self, "_target_format", "mp3")
        )
        self._fix_filename_artifacts(download)

        # Force file permissions
        if download.file_path and os.path.exists(download.file_path):
            self._ensure_permissions(download.file_path, is_file=True)

        logger.info(f"💾 Saving file for user '{download.user.username}' to: {download.file_path}")

        # Save file size to database for faster API responses
        if download.file_path and os.path.exists(download.file_path):
            try:
                download.file_size = os.path.getsize(download.file_path)
                logger.info(f"📏 File size: {download.file_size} bytes")
            except OSError as e:
                logger.warning(f"Could not get file size: {e}")

        await self._update_track_from_file(db, download)

        await db.commit()

        await self._notify_completion(download)

        if download.playlist_name:
            await self.update_playlist_m3u(db, download.user_id, download.playlist_name)

    def _validate_download_path(self, path: str) -> str | None:
        abs_path = os.path.abspath(path)
        abs_base = os.path.abspath(settings.DOWNLOAD_DIR)
        try:
            common = os.path.commonpath([abs_base, abs_path])
        except ValueError:
            common = ""
        if common != abs_base:
            logger.warning(f"User download path {path!r} escapes DOWNLOAD_DIR, falling back to default")
            return None
        return path

    def _set_download_file_path(self, download, final_filename_container, output_template, target_format="mp3"):
        target_ext = f".{target_format}"

        if final_filename_container["path"]:
            base, _ = os.path.splitext(final_filename_container["path"])
            download.file_path = base + target_ext
        else:
            download_path = None
            if download.user and download.user.preferences:
                raw = download.user.preferences.get("downloadPath")
                if raw:
                    download_path = self._validate_download_path(raw)

            if not download_path:
                sanitized_username = sanitize_filename(download.user.username)
                download_path = os.path.join(settings.DOWNLOAD_DIR, sanitized_username)

            if not os.path.exists(download_path):
                os.makedirs(download_path, exist_ok=True)
                self._ensure_permissions(download_path, is_file=False)

            download.file_path = os.path.join(  # nosemgrep: path-traversal
                download_path, f"{output_template}{target_ext}"
            )

    def _fix_filename_artifacts(self, download):
        if download.file_path and os.path.exists(download.file_path):
            directory, filename = os.path.split(download.file_path)
            new_filename = filename

            # 1. Remove "NA - " prefix
            if new_filename.startswith("NA -"):
                new_filename = new_filename[4:].strip()

            # 2. Remove "uploader｜creator - " prefix (and other variants)
            # The user reported: "uploader｜creator - ..." (Note the distinct pipe char ｜)
            prefixes_to_remove = ["uploader｜creator - ", "uploader|creator - ", "uploader - ", "creator - "]

            for prefix in prefixes_to_remove:
                if new_filename.lower().startswith(prefix.lower()):  # Check lower but remove from original
                    new_filename = new_filename[len(prefix) :].strip()

            # Apply rename if changed
            if new_filename != filename and len(new_filename) > 0:
                new_path = os.path.join(directory, new_filename)
                try:
                    os.rename(download.file_path, new_path)
                    download.file_path = new_path
                    logger.info(f"Renamed file to clean artifacts: {filename} -> {new_filename}")
                except Exception as e:
                    logger.warning(f"Failed to rename artifact file: {e}")

    async def _notify_completion(self, download):
        actual_filename = os.path.basename(download.file_path) if download.file_path else f"{download.track_id}.mp3"

        await socket_manager.emit(
            "download:completed",
            {
                "download_id": str(download.id),
                "filename": actual_filename,
                "track": {
                    "title": download.track.title,
                    "artist": download.track.artist,
                    "image_url": download.track.metadata_content.get("image_url")
                    if download.track.metadata_content
                    else None,
                },
            },
        )

    async def _handle_error(self, db, download, e):
        if isinstance(e, DownloadPausedError) or str(e) == "DOWNLOAD_PAUSED":
            logger.info(f"Download {download.id} paused by user")
            download.status = "paused"
            await db.commit()
            await socket_manager.emit("download:paused", {"download_id": str(download.id)})
            return

        logger.error(f"Download failed for {download.id}: {e}", exc_info=True)
        download.status = "failed"
        download.error_message = str(e)
        # Increment retry count
        download.retry_count = (download.retry_count or 0) + 1
        await db.commit()

        await socket_manager.emit("download:error", {"download_id": str(download.id), "error": str(e)})

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
                final_filename_container = {"path": None}

                progress_hook = self._create_progress_hook(download_id, download, loop, final_filename_container)
                ydl_opts, output_template = self._get_ydl_options(download, progress_hook)

                url = await self._resolve_url(db, download)

                if url:
                    await self._execute_download_task(loop, ydl_opts, url, download_id)
                    await self._handle_completion(db, download, final_filename_container, output_template)
                else:
                    raise ValueError("Could not resolve download URL")

            except Exception as e:
                await self._handle_error(db, download, e)

    async def _mark_download_started(self, db, download):
        download.status = "downloading"
        download.started_at = datetime.now(UTC)
        await db.commit()
        await self._notify_start(download)

    async def _notify_processing(self, download):
        await socket_manager.emit("download:processing", {"download_id": str(download.id), "status": "processing"})

    def _create_progress_hook(self, download_id, download, loop, final_filename_container):
        def progress_hook(d):
            if d["status"] == "downloading":
                if download_id in self.paused_downloads:
                    raise DownloadPausedError("DOWNLOAD_PAUSED")
                self._handle_progress_update(d, download_id, download, loop)
            elif d["status"] == "finished":
                try:
                    logger.info(f"Download finished: {d['filename']}. Starting conversion/processing...")

                    # Update status to processing in DB
                    asyncio.run_coroutine_threadsafe(self._set_processing_status(download_id), loop)

                    final_filename_container["path"] = d["filename"]
                except Exception as e:
                    logger.error(f"Finished hook error: {e}")

        return progress_hook

    async def _set_processing_status(self, download_id):
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Download).where(Download.id == download_id))
                download = result.scalar_one_or_none()
                if download:
                    download.status = "processing"
                    download.progress = 100
                    await db.commit()
                    await self._notify_processing(download)
        except Exception as e:
            logger.error(f"Failed to set processing status: {e}")

    def _handle_progress_update(self, d, download_id, download, loop):
        try:
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)

            if total_bytes:
                progress = (downloaded / total_bytes) * 100
            else:
                p = d.get("_percent_str", "0%").replace("%", "")
                progress = float(p)

            # Cap at 99% during downloading phase
            if progress >= 100:
                progress = 99.9

            speed_str = d.get("_speed_str", "").strip()

            asyncio.run_coroutine_threadsafe(
                socket_manager.emit(
                    "download:progress",
                    {
                        "download_id": str(download_id),
                        "progress": progress,
                        "status": "downloading",
                        "speed": speed_str,
                        "track": {
                            "title": download.track.title,
                            "artist": download.track.artist,
                            "image_url": download.track.metadata_content.get("image_url")
                            if download.track.metadata_content
                            else None,
                        },
                    },
                ),
                loop,
            )

            # Throttle DB updates - explicitly check last update time or just modulo?
            # Modulo on progress is okay but for large files it might be too frequent or too sparse.
            # Let's stick to simple modulo for now, but maybe 2% steps?
            if int(progress) % 5 == 0:
                asyncio.run_coroutine_threadsafe(self.update_progress_db(download_id, progress), loop)
        except Exception as e:
            logger.error(f"Progress hook error: {e}")

    async def _resolve_url_cache_optimized(self, loop, ydl_opts, url: str) -> str:
        cache_key = f"metadata_resolve:{url}"
        cached_url = await cache_manager.get(cache_key)

        if cached_url:
            logger.info(f"Cache HIT for {url} -> {cached_url}")
            return cached_url

        logger.info(f"Cache MISS for {url}. Resolving via extract_info...")
        try:

            def resolve_info():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False, process=True)

            info = await loop.run_in_executor(None, resolve_info)
            if info:
                if "entries" in info and len(info["entries"]) > 0:
                    entry = info["entries"][0]
                    real_url = entry.get("webpage_url") or entry.get("url")
                else:
                    real_url = info.get("webpage_url") or info.get("url")

                if real_url:
                    logger.info(f"Resolved {url} to {real_url}. Caching for 24h.")
                    await cache_manager.set(cache_key, real_url, expire=86400)
                    return real_url
        except Exception as e:
            logger.warning(
                f"Failed to resolve/cache metadata for {url}: {e}. Falling back to default download behavior."
            )
        return url

    async def _execute_download_task(self, loop, ydl_opts, url, download_id):
        logger.info(f"Starting download for {download_id} from URL: {url}")

        final_url = url
        if url.startswith("ytsearch") or url.startswith("scsearch"):
            final_url = await self._resolve_url_cache_optimized(loop, ydl_opts, url)

        def download_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([final_url])

        await loop.run_in_executor(None, download_sync)
        logger.info(f"Download finished for {download_id}")

    async def pause_download_async(self, download_id: str):  # NOSONAR
        return self.pause_download(download_id)

    async def resume_download(self, db: AsyncSession, download_id: str):
        if download_id in self.paused_downloads:
            self.paused_downloads.remove(download_id)

        try:
            d_uuid = uuid.UUID(str(download_id))
        except ValueError:
            return

        # Check current status
        result = await db.execute(select(Download).where(Download.id == d_uuid))
        download = result.scalar_one_or_none()

        if download and download.status in ["paused", "failed", "pending"]:
            download.status = "pending"
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

        try:
            d_uuid = uuid.UUID(str(download_id))
        except ValueError:
            return

        result = await db.execute(select(Download).where(Download.id == d_uuid))
        download = result.scalar_one_or_none()

        if download:
            await db.delete(download)
            await db.commit()
            logger.info(f"Cancelled and deleted download {download_id}")

            await socket_manager.emit("download:cancelled", {"download_id": download_id})

    async def retry_failed_downloads(self, db: AsyncSession):
        """Retry all failed downloads that haven't exceeded max retries."""
        MAX_RETRIES = 3  # noqa: N806

        result = await db.execute(
            select(Download).where(
                Download.status == "failed", (Download.retry_count.is_(None)) | (Download.retry_count < MAX_RETRIES)
            )
        )
        failed_downloads = result.scalars().all()

        count = 0
        for download in failed_downloads:
            logger.info(f"Auto-retrying failed download {download.id} (Attempt {download.retry_count or 0 + 1})")
            download.status = "pending"
            await self.queue.put(download.id)
            count += 1

        if count > 0:
            await db.commit()
            await self.start_worker()
            logger.info(f"Scheduled {count} failed downloads for retry")

    def _build_postprocessors(self, bitrate_or_format: str) -> list:
        if bitrate_or_format == "flac":
            self._target_format = "flac"
            return [
                {"key": "FFmpegExtractAudio", "preferredcodec": "flac"},
                {"key": "FFmpegMetadata", "add_metadata": True},
                {"key": "EmbedThumbnail"},
            ]
        self._target_format = "mp3"
        return [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": bitrate_or_format},
            {"key": "FFmpegMetadata", "add_metadata": True},
            {"key": "EmbedThumbnail"},
        ]

    def _build_output_template(self, download: Download, filename_schema: str, schema_map: dict) -> str:
        PLAYLIST_TAG = "{playlist}"  # noqa: N806
        tmpl = filename_schema.replace("{service}", download.source or "")
        if PLAYLIST_TAG in tmpl:
            playlist_val = sanitize_filename(download.playlist_name) if download.playlist_name else ""
            tmpl = tmpl.replace(PLAYLIST_TAG, playlist_val).replace("//", "/")
        for tag, replacement in schema_map.items():
            if tag != PLAYLIST_TAG:
                tmpl = tmpl.replace(tag, replacement)
        if not tmpl or "%" not in tmpl:
            logger.warning(f"Output template '{tmpl}' invalid or missing tags. Fallback to default.")
            tmpl = "%(artist)s - %(title)s"
        return tmpl

    def _resolve_ydl_download_path(self, download: Download, filename_schema: str) -> str:
        raw_path = download.user.preferences.get("download_path")
        download_path = self._validate_download_path(raw_path) if raw_path else None
        if not download_path:
            root_norm = os.path.normpath(settings.DOWNLOAD_DIR)
            if filename_schema.strip().startswith("{user}") or os.path.basename(root_norm) == download.user.username:
                download_path = settings.DOWNLOAD_DIR
            else:
                download_path = os.path.join(  # nosemgrep: path-traversal
                    settings.DOWNLOAD_DIR, sanitize_filename(download.user.username)
                )
        logger.info(f"Resolved base download path: {download_path}")
        if not os.path.exists(download_path):
            try:
                os.makedirs(download_path, exist_ok=True)
                self._ensure_permissions(download_path, is_file=False)
            except Exception as e:
                logger.error(f"Failed to create directory {download_path}: {e}")
                download_path = settings.DOWNLOAD_DIR
        return download_path

    def _get_ydl_options(self, download: Download, progress_hook):
        quality_map = {"low": "128", "normal": "192", "high": "320", "best": "320", "lossless": "flac"}
        bitrate_or_format = quality_map.get(download.user.preferences.get("quality", "high"), "320")
        postprocessors = self._build_postprocessors(bitrate_or_format)

        ydl_opts = {
            "format": "bestaudio/best",
            "writethumbnail": True,
            "socket_timeout": 30,
            "postprocessors": postprocessors,
            "outtmpl": f"{settings.DOWNLOAD_DIR}/%(id)s.%(ext)s",
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
        }

        schema_map = {
            "{artist}": "%(artist)s",
            "{title}": "%(title)s",
            "{album}": "%(album|Single)s",
            "{id}": "%(id)s",
            "{year}": "%(release_date>%Y|Unknown)s",
            "{track_number}": "%(playlist_index)s",
            "{user}": download.user.username,
        }
        filename_schema = download.user.preferences.get("filename_schema", "{artist} - {title}")
        logger.info(f"Processing download {download.id} with schema: '{filename_schema}'")

        output_template = self._build_output_template(download, filename_schema, schema_map)
        download_path = self._resolve_ydl_download_path(download, filename_schema)

        final_outtmpl = os.path.normpath(f"{download_path}/{output_template}.%(ext)s").replace("\\", "/")
        logger.info(f"Final yt-dlp outtmpl: {final_outtmpl}")
        ydl_opts["outtmpl"] = final_outtmpl
        return ydl_opts, output_template

    def _resolve_direct_soundcloud(self, download: Download, track_info) -> str:
        if track_info:
            from urllib.parse import urlparse

            meta = track_info.metadata_content or {}
            track_id_str = str(download.track_id)
            try:
                host = (urlparse(track_id_str).hostname or "").lower()
            except ValueError:
                host = ""
            if host == "soundcloud.com" or host.endswith(".soundcloud.com"):
                return track_id_str
            if meta.get("source_url"):
                return meta["source_url"]
            return f"scsearch1:{track_info.artist} - {track_info.title}"
        return ""

    async def _resolve_url(self, db: AsyncSession, download: Download) -> str:
        attempt = (download.retry_count or 0) + 1
        track_info = await self.get_track_info(db, str(download.track_id)) if download.track_id else None
        instruction = fallback_service.get_fallback_instruction(str(download.source or "unknown"), attempt, track_info)
        logger.info(f"Fallback instruction for {download.source} (Attempt {attempt}): {instruction}")

        resp_type = instruction.get("type")
        value = instruction.get("value")

        if resp_type == "yt_search":
            return f"ytsearch1:{value}"
        if resp_type == "sc_search":
            return f"scsearch1:{value}"
        if resp_type == "direct_youtube":
            return f"https://www.youtube.com/watch?v={download.track_id}"
        if resp_type == "direct_soundcloud":
            return self._resolve_direct_soundcloud(download, track_info)
        if resp_type == "none" and track_info:
            return f"ytsearch1:{track_info.artist} - {track_info.title}"
        return ""

    async def get_track_info(self, db: AsyncSession, track_id: str) -> Track | None:
        result = await db.execute(select(Track).where(Track.id == track_id))
        return result.scalar_one_or_none()

    async def _write_m3u_file(self, downloads: Sequence[Download], target_dir: str, playlist_file_path: str):
        """Helper to write M3U8 file."""
        async with aiofiles.open(playlist_file_path, "w", encoding="utf-8") as f:
            await f.write("#EXTM3U\n")
            for d in downloads:
                if d.file_path:
                    try:
                        rel_path = os.path.relpath(d.file_path, target_dir)
                        await f.write(f"#EXTINF:-1,{d.track.artist} - {d.track.title}\n")
                        await f.write(f"{rel_path}\n")
                    except ValueError:
                        await f.write(f"#EXTINF:-1,{d.track.artist} - {d.track.title}\n")
                        await f.write(f"{d.file_path}\n")

    async def _sync_playlist_to_db(
        self, db: AsyncSession, user_id: uuid.UUID, playlist_name: str, downloads: Sequence[Download]
    ):
        """Helper to sync playlist tracks to database."""
        from sqlalchemy import delete

        from app.models.playlist import Playlist, PlaylistTrack

        # 1. Resolve which playlist to update
        playlist = None
        playlist_id = next((d.playlist_id for d in downloads if d.playlist_id), None)
        if playlist_id:
            pl_result = await db.execute(select(Playlist).where(Playlist.id == playlist_id))
            playlist = pl_result.scalar_one_or_none()

        if not playlist:
            pl_result = await db.execute(
                select(Playlist).where(Playlist.owner_id == user_id, Playlist.name == playlist_name)
            )
            playlist = pl_result.scalar_one_or_none()

        if not playlist:
            playlist = Playlist(
                name=playlist_name, owner_id=user_id, public=False, comment="Auto-created from downloads"
            )
            db.add(playlist)
            await db.flush()
            logger.info(f"Created new DB playlist: {playlist_name}")

        # 2. Collect valid track IDs
        valid_track_ids = [d.track.id for d in downloads if d.track] or [d.track_id for d in downloads if d.track_id]
        valid_track_ids = [tid for tid in valid_track_ids if tid]

        if valid_track_ids:
            await db.execute(delete(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist.id))
            for idx, track_id in enumerate(valid_track_ids):
                try:
                    pt = PlaylistTrack(playlist_id=playlist.id, track_id=track_id, order=idx)
                    db.add(pt)
                except Exception as e:
                    logger.error(f"Failed to add track {track_id} to playlist {playlist.name}: {e}")
            await db.commit()
            logger.info(f"Synced '{playlist_name}' to DB with {len(valid_track_ids)} tracks")

    async def update_playlist_m3u(self, db: AsyncSession, user_id: str, playlist_name: str):
        try:
            result = await db.execute(
                select(Download)
                .options(selectinload(Download.user), selectinload(Download.track))
                .where(
                    Download.user_id == user_id, Download.playlist_name == playlist_name, Download.status == "completed"
                )
                .order_by(Download.created_at)
            )
            downloads = result.scalars().all()

            if not downloads:
                return

            if downloads[0].file_path:
                target_dir = os.path.dirname(downloads[0].file_path)
            else:
                target_dir = os.path.join(settings.DOWNLOAD_DIR, downloads[0].user.username)
                os.makedirs(target_dir, exist_ok=True)

            safe_playlist_name = sanitize_filename(playlist_name)
            playlist_file_path = os.path.join(target_dir, f"{safe_playlist_name}.m3u8")

            await self._write_m3u_file(downloads, target_dir, playlist_file_path)
            logger.info(f"Updated playlist file {playlist_file_path}")

            try:
                await self._sync_playlist_to_db(db, uuid.UUID(str(user_id)), playlist_name, downloads)
            except Exception as e_db:
                logger.error(f"Failed to sync playlist to DB: {e_db}")

        except Exception as e:
            logger.error(f"Failed to update playlist m3u: {e}")

    async def update_progress_db(self, download_id: str, progress: float):
        """Update download progress in DB to support polling fallback"""
        try:
            d_uuid = uuid.UUID(str(download_id)) if not isinstance(download_id, uuid.UUID) else download_id
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Download).where(Download.id == d_uuid))
                download = result.scalar_one_or_none()

                if download:
                    download.progress = int(progress)
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

            # Also delete from playlists table if matches
            from app.models.playlist import Playlist, PlaylistTrack

            pl_query = select(Playlist).where(Playlist.owner_id == user_id, Playlist.name == playlist_name)
            pl_res = await db.execute(pl_query)
            playlist_obj = pl_res.scalar_one_or_none()

            if playlist_obj:
                # Delete tracks mapping first to avoid FK constraint error
                await db.execute(delete(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_obj.id))
                await db.execute(delete(Playlist).where(Playlist.id == playlist_obj.id))

            logger.info(f"Deleted playlist {playlist_name} for user {user_id} and synced with playlists/tracks tables")

        except Exception as e:
            logger.error(f"Error deleting playlist {playlist_name}: {e}")
            raise e

    async def _get_playlist_downloads(self, db: AsyncSession, user_id, source, playlist_name):
        try:
            u_id = uuid.UUID(str(user_id))
        except ValueError:
            return []
        result = await db.execute(
            select(Download).where(
                Download.user_id == u_id, Download.source == source, Download.playlist_name == playlist_name
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

    def _get_user_download_dir(self, download, parent_dir: str) -> str:
        user_dir = os.path.dirname(parent_dir) if parent_dir else None
        if not user_dir:
            if download.user and download.user.preferences:
                user_dir = download.user.preferences.get("downloadPath")
            if not user_dir:
                user_dir = os.path.join(  # nosemgrep: path-traversal
                    settings.DOWNLOAD_DIR, sanitize_filename(download.user.username)
                )
        return user_dir

    @staticmethod
    def _safe_under_download_dir(target: str) -> str | None:
        """Resolve target; return realpath only if it stays under DOWNLOAD_DIR. None otherwise."""
        try:
            base = os.path.realpath(settings.DOWNLOAD_DIR)
            resolved = os.path.realpath(target)
            if os.path.commonpath([base, resolved]) == base:
                return resolved
        except OSError, ValueError:
            pass
        return None

    def _cleanup_empty_directory(self, downloads, playlist_name):
        if not (downloads and downloads[0].file_path):
            return
        parent_dir = os.path.dirname(downloads[0].file_path)
        user_download_dir = self._get_user_download_dir(downloads[0], parent_dir)

        try:
            base_real = os.path.realpath(settings.DOWNLOAD_DIR)
        except OSError, ValueError:
            return

        safe_name = sanitize_filename(playlist_name)
        m3u8_path = os.path.join(user_download_dir, f"{safe_name}.m3u8")
        try:
            m3u8_real = os.path.realpath(m3u8_path)
            if os.path.commonpath([base_real, m3u8_real]) == base_real and os.path.exists(m3u8_real):
                os.remove(m3u8_real)  # nosec B610 — path verified under DOWNLOAD_DIR via commonpath
                logger.info("Removed playlist file")
        except (OSError, ValueError) as e:
            logger.error("Failed to remove playlist file: %s", type(e).__name__)

        safe_dir_name = playlist_name.replace("/", "-").replace("\\", "-")
        try:
            parent_real = os.path.realpath(parent_dir)
            if os.path.commonpath([base_real, parent_real]) == base_real and safe_dir_name in os.path.basename(
                parent_real
            ):
                os.rmdir(parent_real)  # nosec B610 — path verified under DOWNLOAD_DIR via commonpath
                logger.info("Removed empty directory")
        except (OSError, ValueError) as e:
            logger.debug("Failed to remove directory: %s", type(e).__name__)

    async def _delete_db_records(self, db, downloads):
        # 4. Delete DB records
        for download in downloads:
            await db.delete(download)
        await db.commit()


download_manager = DownloadManager()
