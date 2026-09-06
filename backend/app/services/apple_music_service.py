import logging
from typing import Any

import aiohttp

from app.services.base_music_service import BaseMusicService
from app.utils.log_sanitize import sanitize_log

# Lazy import or direct import if circular dependency is not an issue.
# Assuming unl_helper is fine.
# We will do dynamic import inside methods to be safe as done in original
# code effectively (it was imported inside try block? No it was inside method).

logger = logging.getLogger(__name__)


class AppleMusicService(BaseMusicService):
    ITUNES_SEARCH_URL = "https://itunes.apple.com/search"

    def __init__(self):
        super().__init__()
        self.source_name = "apple_music"

    def can_handle(self, url: str) -> bool:
        return "music.apple.com" in url or "apple.co" in url

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
        if "apple.co" in url:
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
