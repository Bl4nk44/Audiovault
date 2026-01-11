import asyncio
import logging

import yt_dlp

from app.providers.base import MusicProvider
from app.schemas.metadata import PlaylistMetadata, TrackMetadata

logger = logging.getLogger(__name__)


class GenericProvider(MusicProvider):
    def __init__(self):
        self._name = "generic"

    @property
    def name(self) -> str:
        return self._name

    @property
    def domains(self) -> list[str]:
        # yt-dlp supports hundreds of domains.
        # We return a wildcard or empty list implies "try this if specific ones fail"
        return ["*"]

    def can_handle(self, url: str) -> bool:
        # The generic provider is a fallback, but we can check if yt-dlp supports it.
        # For now, we assume it handles everything that specific providers don't.
        return True

    async def extract_playlist(self, url: str) -> PlaylistMetadata | None:
        ydl_opts = {
            "extract_flat": True,  # Extract metadata only, fast
            "dump_single_json": True,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
        }

        try:
            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False),
            )

            if not info:
                return None

            entries = info.get("entries", [])
            tracks: list[TrackMetadata] = []

            # If single item (not playlist), entries might be empty/None, check plain info
            if not entries and info.get("_type") != "playlist":
                # It's a single track URL potentially passed as playlist
                entries = [info]

            for entry in entries:
                if not entry:
                    continue

                title = entry.get("title")
                # yt-dlp might put artist in 'uploader', 'artist', 'creator'
                artist = entry.get("artist") or entry.get("uploader") or entry.get("creator") or "Unknown Artist"

                if not title:
                    continue

                tracks.append(
                    TrackMetadata(
                        title=title,
                        artist=artist,
                        album=entry.get("album"),
                        duration_ms=int(entry.get("duration", 0) * 1000) if entry.get("duration") else None,
                        source_id=entry.get("id"),
                        source_url=entry.get("url") or entry.get("webpage_url"),
                        image_url=entry.get("thumbnail"),
                    )
                )

            return PlaylistMetadata(
                title=info.get("title", "Unknown Playlist"),
                description=info.get("description"),
                author=info.get("uploader"),
                tracks=tracks,
            )

        except Exception as e:
            logger.error(f"GenericProvider extraction failed: {e}")
            return None

    async def get_track(self, url: str) -> TrackMetadata | None:
        # Reuse playlist logic but expect single result
        playlist = await self.extract_playlist(url)
        if playlist and playlist.tracks:
            return playlist.tracks[0]
        return None
