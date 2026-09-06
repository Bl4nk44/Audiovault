import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

import yt_dlp

from app.utils.log_sanitize import sanitize_log
from app.utils.ydl import apply_proxy

logger = logging.getLogger(__name__)

_SOUNDCLOUD_HOSTS = {"soundcloud.com", "www.soundcloud.com", "on.soundcloud.com", "m.soundcloud.com"}


class SoundCloudService:
    def __init__(self):
        pass  # No state required

    def can_handle(self, url: str) -> bool:
        try:
            host = (urlparse(url).hostname or "").lower()
        except ValueError:
            return False
        return host in _SOUNDCLOUD_HOSTS

    def _extract_tracks_from_info(self, info: dict, url: str) -> list[dict[str, Any]]:
        entries = info.get("entries", [])
        if not entries and info.get("_type") != "playlist":
            entries = [info]
        return [t for e in entries if (t := self._format_entry(e, url))]

    async def get_tracks(self, url: str) -> list[dict[str, Any]]:
        """
        Extract tracks from SoundCloud URL using yt-dlp.
        SoundCloud is well supported by yt-dlp.
        """
        ydl_opts = {
            "extract_flat": True,
            "dump_single_json": True,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
        }
        apply_proxy(ydl_opts)

        try:
            logger.info("Extracting SoundCloud metadata from: %s", sanitize_log(url))

            if "on.soundcloud.com" in url:
                from app.utils.url_helper import resolve_redirects

                url = await resolve_redirects(url)
                logger.info("Resolved SoundCloud short link to: %s", sanitize_log(url))

            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False),
            )

            if not info:
                logger.warning("No info extracted from SoundCloud URL")
                return []

            tracks = self._extract_tracks_from_info(info, url)
            logger.info(f"Extracted {len(tracks)} tracks from SoundCloud")
            return tracks

        except Exception as e:
            logger.error(f"Error extracting SoundCloud data: {e}")
            return []

    async def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Keyword track search on SoundCloud via yt-dlp's ``scsearch`` extractor.

        yt-dlp has no public SoundCloud metadata API, but ``scsearchN:<query>``
        performs a real keyword search and returns flat entries we can map to the
        unified track shape. No API key required.
        """
        count = max(1, min(limit, 50))
        ydl_opts = {
            "extract_flat": True,
            "dump_single_json": True,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
        }
        apply_proxy(ydl_opts)

        try:
            logger.info("SoundCloud keyword search: %s", sanitize_log(query))
            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(f"scsearch{count}:{query}", download=False),
            )
            if not info:
                return []
            entries = info.get("entries") or []
            tracks = [t for e in entries if (t := self._format_entry(e, ""))]
            logger.info("SoundCloud search returned %d tracks", len(tracks))
            return tracks
        except Exception as e:
            logger.error(f"Error searching SoundCloud: {e}")
            return []

    async def get_playlist_info(self, url: str) -> dict[str, Any] | None:
        """
        Extract playlist info (title, image, id) from SoundCloud URL.
        """
        ydl_opts = {
            "extract_flat": True,
            "dump_single_json": True,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "playlist_items": "1",
        }
        apply_proxy(ydl_opts)

        try:
            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False),
            )

            if not info:
                return None

            # SoundCloud specific: check if it's a set or user (user can be playlist-like)
            if info.get("_type") != "playlist" and "/sets/" not in url:
                # If it's a single track, we might not want to treat it as a playlist container
                # UNLESS the user pasted a track URL and expects it to be added as a "watched track"?
                # Current Watchlist logic supports "playlist", "artist", "channel".
                # For now, let's only support sets as playlists.
                return None

            image_url = None
            if info.get("thumbnails"):
                image_url = info["thumbnails"][-1]["url"]

            track_count = info.get("playlist_count")
            if not track_count and info.get("entries"):
                track_count = len(info["entries"])

            return {
                "id": url,
                "title": info.get("title", "Unknown Playlist"),
                "image_url": image_url,
                "source": "soundcloud",
                "type": "playlist",
                "track_count": track_count,
            }

        except Exception as e:
            logger.error(f"Error extracting SoundCloud playlist info: {e}")
            return None

    def _format_entry(self, entry: dict, fallback_url: str) -> dict | None:
        if not entry:
            return None
        title = entry.get("title")
        if not title:
            return None
        track_id = entry.get("id")
        uploader = entry.get("uploader") or entry.get("artist") or "Unknown Artist"
        source_url = entry.get("webpage_url") or entry.get("url") or fallback_url
        duration = entry.get("duration")
        return {
            "id": str(track_id) if track_id else None,
            "title": title,
            "artist": uploader,
            "album": "SoundCloud",
            "duration_ms": int(duration * 1000) if duration else None,
            "image_url": entry.get("thumbnail"),
            "source": "soundcloud",
            "source_url": source_url,
        }


soundcloud_service = SoundCloudService()
