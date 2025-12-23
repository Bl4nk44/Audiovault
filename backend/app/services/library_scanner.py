import os
import logging
import mutagen
from mutagen.easyid3 import EasyID3
from typing import Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.track import Track
from app.models.download import Download
from app.core.config import settings

logger = logging.getLogger(__name__)

class LibraryScannerService:
    def __init__(self):
        self.base_dir = os.path.abspath(settings.DOWNLOAD_DIR)

    def _validate_scan_path(self, scan_path: Optional[str]) -> str:
        if scan_path:
            target_path = os.path.abspath(scan_path)
            try:
                common = os.path.commonpath([self.base_dir, target_path])
            except ValueError:
                common = ""
            
            if common != self.base_dir:
                raise ValueError("Access denied: Cannot scan directories outside of download library.")
            return target_path
        return self.base_dir

    async def _get_known_paths(self, db: AsyncSession, user_id: str) -> Set[str]:
        result = await db.execute(select(Download.file_path).where(Download.user_id == user_id))
        known_paths = set()
        for row in result.all():
            if row[0]: # row[0] is Download.file_path
                known_paths.add(os.path.normpath(row[0]))
        return known_paths

    def _parse_audio_metadata(self, full_path: str, filename: str) -> tuple[str, str, str]:
        title = os.path.splitext(filename)[0]
        artist = "Unknown Artist"
        album = "Unknown Album"
        
        try:
            audio = EasyID3(full_path)
            if 'title' in audio:
                title = audio['title'][0]
            if 'artist' in audio:
                artist = audio['artist'][0]
            if 'album' in audio:
                album = audio['album'][0]
        except Exception:
            try:
                m = mutagen.File(full_path)
                if m and 'TIT2' in m:
                    title = str(m['TIT2'])
                if m and 'TPE1' in m:
                    artist = str(m['TPE1'])
            except Exception as e:
                logger.debug(f"Mutagen fallback failed for {filename}: {e}")
        return title, artist, album

    def _infer_source_info(self, full_path: str, root_dir: str) -> tuple[str, str]:
        source = "local_import"
        playlist_name = "Imported"
        
        try:
            rel_path = os.path.relpath(full_path, root_dir)
            parts = rel_path.split(os.sep)
            
            if len(parts) >= 3:
                source = parts[0].lower()
                playlist_name = parts[1]
            elif len(parts) == 2:
                folder = parts[0].lower()
                known_sources = {'spotify', 'youtube', 'deezer', 'apple_music', 'tidal', 'soundcloud', 'amazon_music'}
                if folder in known_sources:
                    source = folder
                    playlist_name = "Uncategorized"
                else:
                    playlist_name = parts[0]
        except Exception as e:
            logger.debug(f"Failed to infer source info for {full_path}: {e}") # Fallback to default
            
        return source, playlist_name

    async def scan_directory(self, db: AsyncSession, user_id: str, scan_path: Optional[str] = None) -> dict:
        try:
            root_dir = self._validate_scan_path(scan_path)
        except ValueError as e:
             return {"status": "error", "message": str(e)}

        if not os.path.exists(root_dir):
            return {"status": "error", "message": f"Directory {root_dir} does not exist"}

        known_paths = await self._get_known_paths(db, user_id)
        imported_count = 0
        errors = []
        total_found = 0

        for dirpath, dirnames, filenames in os.walk(root_dir):
            for filename in filenames:
                if not filename.lower().endswith('.mp3'):
                    continue
                
                total_found += 1
                full_path = os.path.join(dirpath, filename)
                norm_path = os.path.normpath(full_path)

                if norm_path in known_paths:
                    continue

                try:
                    title, artist, album = self._parse_audio_metadata(full_path, filename)
                    source, playlist_name = self._infer_source_info(full_path, root_dir)

                    new_track = Track(
                        title=title,
                        artist=artist,
                        album=album,
                        filename=filename,
                        duration_ms=0,
                        source_id=f"local:{filename}", 
                        metadata_content={"source": source, "imported": True}
                    )
                    db.add(new_track)
                    await db.flush()

                    new_download = Download(
                        user_id=user_id,
                        track_id=new_track.id,
                        status='completed',
                        file_path=full_path,
                        source=source,
                        playlist_name=playlist_name,
                        progress=100.0,
                        archived=False
                    )
                    db.add(new_download)
                    imported_count += 1

                except Exception as e:
                    error_msg = f"Failed to import {filename}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

        if imported_count > 0:
            await db.commit()

        return {
            "status": "success",
            "scanned_dir": root_dir,
            "total_files_found": total_found,
            "imported_count": imported_count,
            "errors": errors[:10]
        }

library_scanner_service = LibraryScannerService()
