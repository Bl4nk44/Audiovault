import asyncio
import logging
import os
from uuid import UUID

import aiofiles
from app.core.config import settings
from app.core.executors import stream_executor
from app.models.album import Album
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from mutagen import File as MutagenFile
from mutagen.easyid3 import EasyID3
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

UNKNOWN_ARTIST = "Unknown Artist"
UNKNOWN_ALBUM = "Unknown Album"


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
        from uuid import UUID as UUID_type  # noqa: N811

        try:
            u_id = UUID_type(str(user_id))
        except ValueError:
            return set()
        result = await db.execute(select(Download.file_path).where(Download.user_id == u_id))
        known_paths = set()
        for row in result.all():
            if row[0]:  # row[0] is Download.file_path
                known_paths.add(os.path.normpath(row[0]))
        return known_paths

    def _try_parse_easyid3(self, full_path: str) -> tuple[str, str, str, str | None]:
        title, artist, album, genre = self._get_default_metadata(os.path.basename(full_path))
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
        except Exception as e:
            logger.debug(f"EasyID3 parse failed: {e}")
        return title, artist, album, genre

    def _update_meta_from_tags(self, m, current_meta: tuple, filename: str) -> tuple[str, str, str, str | None]:
        title, artist, album, genre = current_meta
        default_title = os.path.splitext(filename)[0]

        if artist == UNKNOWN_ARTIST and "TPE1" in m:
            artist = str(m["TPE1"])
        if title == default_title and "TIT2" in m:
            title = str(m["TIT2"])
        if album == UNKNOWN_ALBUM and "TALB" in m:
            album = str(m["TALB"])
        if genre is None and "TCON" in m:
            genre = str(m["TCON"])

        return title, artist, album, genre

    def _extract_lyrics_from_lrc_file(self, full_path: str) -> str | None:
        base_path = os.path.splitext(full_path)[0]
        lrc_path = base_path + ".lrc"
        if os.path.exists(lrc_path):
            try:
                with open(lrc_path, encoding="utf-8", errors="replace") as f:
                    lrc_content = f.read().strip()
                    if lrc_content:
                        return lrc_content
            except Exception:  # noqa: S110
                pass
        return None

    def _extract_lyrics_from_tags(self, m) -> str | None:
        if not hasattr(m, "tags"):
            return None

        # ID3 (mp3)
        if "USLT::eng" in m.tags:
            return str(m.tags["USLT::eng"])
        elif "USLT:" in m.tags:
            return str(m.tags["USLT:"])

        # Generic lookup for frames starting with USLT
        for tag in m.tags:
            if tag.startswith("USLT"):
                return str(m.tags[tag])

        # FLAC/Vorbis
        if hasattr(m.tags, "__contains__") and "lyrics" in m.tags:
            return m.tags["lyrics"][0]

        return None

    def _try_parse_mutagen_fallback(
        self, full_path: str, current_meta: tuple
    ) -> tuple[str, str, str, str | None, int, str | None]:
        title, artist, album, genre = current_meta
        duration_ms = 0
        lyrics = None
        filename = os.path.basename(full_path)

        try:
            m = MutagenFile(full_path)
            if m:
                if m.info and hasattr(m.info, "length"):
                    duration_ms = int(m.info.length * 1000)

                title, artist, album, genre = self._update_meta_from_tags(m, (title, artist, album, genre), filename)

                # Extract Lyrics
                tag_lyrics = self._extract_lyrics_from_tags(m)
                if tag_lyrics:
                    lyrics = tag_lyrics

            # 3. Check for external .lrc file (prioritize over tags as it's likely better/synced)
            external_lyrics = self._extract_lyrics_from_lrc_file(full_path)
            if external_lyrics:
                lyrics = external_lyrics

        except Exception as e:
            logger.debug(f"Mutagen fallback failed for {filename}: {e}")

        return title, artist, album, genre, duration_ms, lyrics

    def _get_default_metadata(self, filename: str) -> tuple[str, str, str, str | None]:
        return os.path.splitext(filename)[0], UNKNOWN_ARTIST, UNKNOWN_ALBUM, None

    def _parse_audio_metadata_sync(self, full_path: str) -> tuple[str, str, str, str | None, int, str | None]:
        """Sync version of parse metadata (CPU bound)."""
        # 1. EasyID3
        title, artist, album, genre = self._try_parse_easyid3(full_path)

        # 2. Mutagen Fallback & Duration & Lyrics
        return self._try_parse_mutagen_fallback(full_path, (title, artist, album, genre))

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
    ) -> tuple[UUID | None, UUID | None]:
        """
        Get or create Artist and Album entities.
        Returns tuple of (artist_id, album_id) as UUIDs (or None).
        """
        if not artist_name:
            artist_name = UNKNOWN_ARTIST
        if not album_name:
            album_name = UNKNOWN_ALBUM

        # 1. Resolve Artist
        res_artist = await db.execute(select(Artist).where(Artist.name == artist_name))
        artist = res_artist.scalar_one_or_none()

        if not artist:
            artist = Artist(name=artist_name)
            db.add(artist)
            await db.flush()  # Get ID

        artist_id = artist.id

        # 2. Resolve Album
        res_album = await db.execute(select(Album).where(Album.title == album_name, Album.artist_id == artist_id))
        album = res_album.scalar_one_or_none()

        if not album:
            album = Album(title=album_name, artist_id=artist_id)
            db.add(album)
            await db.flush()

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

            async with aiofiles.open(full_path, encoding="utf-8", errors="ignore") as f:
                lines = await f.readlines()

            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                t_id = await self._find_track_for_playlist_line(db, line, base_dir, user_id)
                if t_id:
                    matched_tracks.append(t_id)

            # Only update playlist if we found tracks
            if matched_tracks:
                # Clear existing tracks
                from sqlalchemy import delete

                await db.execute(delete(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist.id))

                # Add new tracks
                for order, track_id in enumerate(matched_tracks):
                    pt = PlaylistTrack(playlist_id=playlist.id, track_id=track_id, order=order)
                    db.add(pt)

                await db.commit()
                logger.info(f"Imported playlist {name} with {len(matched_tracks)} tracks")
            else:
                logger.info(f"Playlist {name}: No tracks matched, keeping existing data")

        except Exception as e:
            logger.error(f"Failed to import playlist {full_path}: {e}")

    async def _find_track_for_playlist_line(self, db: AsyncSession, line: str, base_dir: str, user_id: str):
        # Resolve track path with path traversal protection
        if os.path.isabs(line):
            track_path = os.path.abspath(line)
        else:
            track_path = os.path.abspath(os.path.join(base_dir, line))

        # Security: ensure resolved path stays within the allowed download directory
        try:
            common = os.path.commonpath([self.base_dir, track_path])
        except ValueError:
            common = ""
        if common != self.base_dir:
            logger.warning(f"Path traversal blocked in playlist: {line!r}")
            return None

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
                pass

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
            return t_id
        return None

    async def _process_audio_file(
        self, db: AsyncSession, user_id: str, full_path: str, filename: str, root_dir: str
    ) -> bool:
        try:
            # Parse metadata in executor to avoid blocking event loop
            import functools

            loop = asyncio.get_event_loop()

            title, artist, album, genre, duration_ms, lyrics = await loop.run_in_executor(
                stream_executor, functools.partial(self._parse_audio_metadata_sync, full_path)
            )

            source, playlist_name = self._infer_source_info(full_path, root_dir)

            try:
                file_size = os.path.getsize(full_path)
            except OSError:
                file_size = 0

            metadata = {"source": source, "imported": True}
            if genre:
                metadata["genre"] = genre
            if lyrics:
                metadata["lyrics"] = lyrics

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

            from uuid import UUID as UUID_type  # noqa: N811

            try:
                u_id = UUID_type(str(user_id))
            except ValueError:
                return False

            new_download = Download(
                user_id=u_id,
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
            return True

        except Exception as e:
            logger.error(f"Failed to import {filename}: {str(e)}")
            raise e

    async def _handle_scan_file(self, db, user_id, full_path, filename, root_dir, known_paths) -> bool:
        lower_name = filename.lower()

        # Handle Playlists
        if lower_name.endswith((".m3u", ".m3u8")):
            await self._import_playlist(db, full_path, user_id)
            return False

        # Handle Audio
        if not lower_name.endswith(".mp3"):
            return False

        norm_path = os.path.normpath(full_path)
        if norm_path in known_paths:
            return False

        await self._process_audio_file(db, user_id, full_path, filename, root_dir)
        return True

    async def scan_directory(self, db: AsyncSession, user_id: str, scan_path: str | None = None) -> dict:
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

        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                if filename.lower().endswith(".mp3"):
                    total_found += 1

                try:
                    if await self._handle_scan_file(db, user_id, full_path, filename, root_dir, known_paths):
                        imported_count += 1
                except Exception as e:
                    errors.append(f"Failed to import {filename}: {str(e)}")

        if imported_count > 0:
            await db.commit()

        return {
            "status": "success",
            "scanned_dir": root_dir,
            "total_files_found": total_found,
            "imported_count": imported_count,
            "errors": errors[:10],
        }

    async def cleanup_orphans(self, db: AsyncSession) -> int:
        """Remove tracks from DB if their physical files are missing."""
        result = await db.execute(select(Download).where(Download.status == "completed"))
        downloads = result.scalars().all()

        removed_count = 0
        for download in downloads:
            if download.file_path and not os.path.exists(download.file_path):
                # Delete track and download
                if download.track_id:
                    from app.models.track import Track

                    await db.execute(delete(Track).where(Track.id == download.track_id))

                await db.delete(download)
                removed_count += 1

        if removed_count > 0:
            await db.commit()
            logger.info(f"Cleaned up {removed_count} orphaned tracks")

        return removed_count


library_scanner_service = LibraryScannerService()
