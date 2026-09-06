import logging
from typing import Any
from urllib.parse import urlparse

import aiohttp

from app.services.base_music_service import BaseMusicService
from app.utils.log_sanitize import sanitize_log

logger = logging.getLogger(__name__)

_APPLE_MUSIC_HOSTS = {
    "music.apple.com",
    "beta.music.apple.com",
    "embed.music.apple.com",
    "geo.music.apple.com",
}
_APPLE_SHORT_HOSTS = {"apple.co"}


class AppleMusicService(BaseMusicService):
    ITUNES_SEARCH_URL = "https://itunes.apple.com/search"

    def __init__(self):
        super().__init__()
        self.source_name = "apple_music"

    @staticmethod
    def _host(url: str) -> str:
        try:
            return (urlparse(url).hostname or "").lower()
        except ValueError:
            return ""

    def can_handle(self, url: str) -> bool:
        host = self._host(url)
        return host in _APPLE_MUSIC_HOSTS or host in _APPLE_SHORT_HOSTS

    async def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Keyword track search via Apple's public iTunes Search API (no key).

        Apple Music has no yt-dlp keyword search; the iTunes Search API is the
        supported public surface for catalogue lookups.
        """
        params: dict[str, str | int] = {
            "term": query,
            "media": "music",
            "entity": "song",
            "limit": max(1, min(limit, 200)),
        }
        try:
            async with (
                aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session,
                session.get(self.ITUNES_SEARCH_URL, params=params) as response,
            ):
                if response.status != 200:
                    logger.warning("iTunes search HTTP %s for %s", response.status, sanitize_log(query))
                    return []
                # iTunes serves JSON as text/javascript — disable content-type check.
                data = await response.json(content_type=None)
        except Exception as e:
            logger.error("Error searching Apple Music (iTunes API): %s", sanitize_log(e))
            return []

        return [self._format_itunes_track(item) for item in data.get("results", []) if item.get("trackId")]

    def _format_itunes_track(self, item: dict[str, Any]) -> dict[str, Any]:
        artwork = item.get("artworkUrl100") or ""
        image_url = artwork.replace("100x100bb", "600x600bb") or None
        return {
            "id": str(item.get("trackId")),
            "title": item.get("trackName"),
            "artist": item.get("artistName"),
            "album": item.get("collectionName"),
            "duration_ms": item.get("trackTimeMillis"),
            "image_url": image_url,
            "source": "apple_music",
            "type": "track",
            "popularity": 0,
            "isrc": None,
        }

    async def _resolve_url(self, url: str) -> str:
        if self._host(url) in _APPLE_SHORT_HOSTS:
            from app.utils.url_helper import resolve_redirects

            resolved = await resolve_redirects(url)
            logger.info("Resolved Apple Music short link to: %s", sanitize_log(resolved))
            return resolved
        return url

    async def get_tracks(self, url: str) -> list[dict[str, Any]]:
        url = await self._resolve_url(url)
        return await super().get_tracks(url)

    async def get_playlist_info(self, url: str) -> dict[str, Any] | None:
        url = await self._resolve_url(url)
        return await super().get_playlist_info(url)


apple_music_service = AppleMusicService()
