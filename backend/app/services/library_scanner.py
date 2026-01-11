import logging
import os

import mutagen
from app.core.config import settings
from app.models.album import Album
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from mutagen.easyid3 import EasyID3
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


class LibraryScannerService:
    def __init__(self):
        self.base_dir = os.path.abspath(settings.DOWNLOAD_DIR)

    def _validate_scan_path(self, scan_path: str | None) -> str:
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

    async def _get_known_paths(self, db: AsyncSession, user_id: str) -> set[str]:
        result = await db.execute(select(Download.file_path).where(Download.user_id == user_id))
        known_paths = set()
        for row in result.all():
            if row[0]:  # row[0] is Download.file_path
                known_paths.add(os.path.normpath(row[0]))
        return known_paths

    def _parse_audio_metadata(self, full_path: str, filename: str) -> tuple[str, str, str, str, int]:
        """Parse audio file metadata including duration.
        
        Returns:
            tuple: (title, artist, album, genre, duration_ms)
        """
        title = os.path.splitext(filename)[0]
        artist = "Unknown Artist"
        album = "Unknown Album"
        genre = None
        duration_ms = 0

        try:
            audio = EasyID3(full_path)
            if "title" in audio:
                title = audio["title"][0]
            if "artist" in audio:
                artist = audio["artist"][0]
            if "album" in audio:
                album = audio["album"][0]
            if "genre" in audio:
                genre = audio["genre"][0]
        except Exception:
            pass
        
        # Always try to get duration using mutagen.File
        try:
            m = mutagen.File(full_path)
            if m:
                # Get duration
                if m.info and hasattr(m.info, 'length'):
                    duration_ms = int(m.info.length * 1000)
                
                # Fallback for metadata if EasyID3 failed
                if artist == "Unknown Artist" and "TPE1" in m:
                    artist = str(m["TPE1"])
                if title == os.path.splitext(filename)[0]:
                    if "TIT2" in m:
                        title = str(m["TIT2"])
                if album == "Unknown Album" and "TALB" in m:
                    album = str(m["TALB"])
                if not genre and "TCON" in m:
                    genre = str(m["TCON"])
        except Exception as e:
            logger.debug(f"Mutagen fallback failed for {filename}: {e}")
        
        return title, artist, album, genre, duration_ms

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
                known_sources = {
                    "spotify",
                    "youtube",
                    "deezer",
                    "apple_music",
                    "tidal",
                    "soundcloud",
                    "amazon_music",
                }
                if folder in known_sources:
                    source = folder
                    playlist_name = "Uncategorized"
                else:
                    playlist_name = parts[0]
        except Exception as e:
            logger.debug(f"Failed to infer source info for {full_path}: {e}")  # Fallback to default

        return source, playlist_name

    async def resolve_artist_and_album(
        self, db: AsyncSession, artist_name: str, album_name: str
    ) -> tuple[str | None, str | None]:
        """
        Get or create Artist and Album entities.
        Returns tuple of (artist_id, album_id) as UUIDs (or None).
        """
        if not artist_name:
            artist_name = "Unknown Artist"
        if not album_name:
            album_name = "Unknown Album"

        # 1. Resolve Artist
        result = await db.execute(select(Artist).where(Artist.name == artist_name))
        artist = result.scalar_one_or_none()

        if not artist:
            artist = Artist(name=artist_name)
            db.add(artist)
            await db.flush()  # Get ID

        artist_id = artist.id

        # 2. Resolve Album
        result = await db.execute(select(Album).where(Album.title == album_name, Album.artist_id == artist_id))
        album = result.scalar_one_or_none()

        if not album:
            album = Album(title=album_name, artist_id=artist_id)
            db.add(album)
            await db.flush()

        album_id = album.id

        album_id = album.id
        return artist_id, album_id

    async def _import_playlist(self, db: AsyncSession, full_path: str, user_id: str):
        """
        Parse M3U/M3U8 file and sync to DB Playlist.
        Matches tracks using multiple strategies for robust path resolution.
        Only clears existing tracks if we have new tracks to add.
        """
        try:
            filename = os.path.basename(full_path)
            name = os.path.splitext(filename)[0]
            
            # Find or create Playlist
            from app.models.playlist import Playlist, PlaylistTrack
            stmt = select(Playlist).where(Playlist.name == name, Playlist.owner_id == user_id)
            result = await db.execute(stmt)
            playlist = result.scalar_one_or_none()
            
            if not playlist:
                playlist = Playlist(name=name, owner_id=user_id)
                db.add(playlist)
                await db.flush()
                logger.info(f"Created new playlist from file: {name}")

            # Parse file and collect matched tracks FIRST
            base_dir = os.path.dirname(full_path)
            matched_tracks = []  # List of track_ids in order
            
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Resolve track path
                if os.path.isabs(line):
                    track_path = line
                else:
                    track_path = os.path.normpath(os.path.join(base_dir, line))
                
                download = None
                
                # Strategy 1: Try exact path match
                stmt = select(Download).where(Download.file_path == track_path).limit(1)
                res = await db.execute(stmt)
                download = res.scalar_one_or_none()
                
                # Strategy 2: Try normalized path with /downloads/ prefix
                if not download:
                    try:
                        relative_rel = os.path.relpath(track_path, self.base_dir)
                        db_path_guess = f"/downloads/{relative_rel}".replace("\\", "/")
                        stmt = select(Download).where(Download.file_path == db_path_guess).limit(1)
                        res = await db.execute(stmt)
                        download = res.scalar_one_or_none()
                    except ValueError:
                        pass  # Different drives on Windows
                
                # Strategy 3: Match by filename only (for this user)
                if not download:
                    track_filename = os.path.basename(line)
                    stmt = (
                        select(Download)
                        .where(
                            Download.user_id == user_id,
                            Download.file_path.like(f"%/{track_filename}"),
                        )
                        .limit(1)
                    )
                    res = await db.execute(stmt)
                    download = res.scalar_one_or_none()
                
                if download and download.track_id:
                    from uuid import UUID
                    t_id = download.track_id
                    if isinstance(t_id, str):
                        t_id = UUID(t_id)
                    matched_tracks.append(t_id)

            # Only update playlist if we found tracks
            if matched_tracks:
                # Clear existing tracks
                from sqlalchemy import delete
                await db.execute(delete(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist.id))
                
                # Add new tracks
                for order, track_id in enumerate(matched_tracks):
                    pt = PlaylistTrack(
                        playlist_id=playlist.id, 
                        track_id=track_id,
                        order=order
                    )
                    db.add(pt)
                
                await db.commit()
                logger.info(f"Imported playlist {name} with {len(matched_tracks)} tracks")
            else:
                logger.info(f"Playlist {name}: No tracks matched, keeping existing data")

        except Exception as e:
            logger.error(f"Failed to import playlist {full_path}: {e}")





    async def scan_directory(self, db: AsyncSession, user_id: str, scan_path: str | None = None) -> dict:
        try:
            root_dir = self._validate_scan_path(scan_path)
        except ValueError as e:
            return {"status": "error", "message": str(e)}

        if not os.path.exists(root_dir):
            return {
                "status": "error",
                "message": f"Directory {root_dir} does not exist",
            }

        known_paths = await self._get_known_paths(db, user_id)
        imported_count = 0
        errors = []
        total_found = 0

        for dirpath, dirnames, filenames in os.walk(root_dir):
            for filename in filenames:
                lower_name = filename.lower()
                
                # Handle Playlists
                if lower_name.endswith(".m3u") or lower_name.endswith(".m3u8"):
                     full_path = os.path.join(dirpath, filename)
                     await self._import_playlist(db, full_path, user_id)
                     continue

                # Handle Audio
                if not lower_name.endswith(".mp3"):
                    continue

                total_found += 1
                full_path = os.path.join(dirpath, filename)
                norm_path = os.path.normpath(full_path)
                try:
                    file_size = os.path.getsize(full_path)
                except OSError:
                    file_size = 0

                if norm_path in known_paths:
                    continue

                try:
                    title, artist, album, genre, duration_ms = self._parse_audio_metadata(full_path, filename)
                    source, playlist_name = self._infer_source_info(full_path, root_dir)

                    metadata = {"source": source, "imported": True}
                    if genre:
                        metadata["genre"] = genre

                    new_track = Track(
                        title=title,
                        artist=artist,
                        album=album,
                        duration_ms=duration_ms,
                        metadata_content=metadata,
                    )

                    # Resolve relationships
                    artist_id, album_id = await self.resolve_artist_and_album(db, artist, album)
                    new_track.artist_id = artist_id
                    new_track.album_id = album_id

                    db.add(new_track)
                    await db.flush()

                    new_download = Download(
                        user_id=user_id,
                        track_id=new_track.id,
                        status="completed",
                        file_path=full_path,
                        source=source,
                        playlist_name=playlist_name,
                        progress=100.0,
                        file_size=file_size,
                        archived=False,
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
            "errors": errors[:10],
        }


library_scanner_service = LibraryScannerService()
