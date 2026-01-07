import logging
from typing import List, Dict, Any, Optional
from app.services.base_music_service import BaseMusicService
# Lazy import or direct import if circular dependency is not an issue.
# Assuming unl_helper is fine.
# We will do dynamic import inside methods to be safe as done in original code effectively (it was imported inside try block? No it was inside method).

logger = logging.getLogger(__name__)


class AppleMusicService(BaseMusicService):
    def __init__(self):
        super().__init__()
        self.source_name = "apple_music"

    def can_handle(self, url: str) -> bool:
        return "music.apple.com" in url or "apple.co" in url

    async def _resolve_url(self, url: str) -> str:
        if "apple.co" in url:
            from app.utils.url_helper import resolve_redirects

            resolved = await resolve_redirects(url)
            logger.info(f"Resolved Apple Music short link to: {resolved}")
            return resolved
        return url

    async def get_tracks(self, url: str) -> List[Dict[str, Any]]:
        url = await self._resolve_url(url)
        return await super().get_tracks(url)

    async def get_playlist_info(self, url: str) -> Optional[Dict[str, Any]]:
        url = await self._resolve_url(url)
        return await super().get_playlist_info(url)


apple_music_service = AppleMusicService()
