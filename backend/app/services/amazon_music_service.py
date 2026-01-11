import logging

from app.services.base_music_service import BaseMusicService

logger = logging.getLogger(__name__)


class AmazonMusicService(BaseMusicService):
    def __init__(self):
        super().__init__()
        self.source_name = "amazon_music"

    def can_handle(self, url: str) -> bool:
        return "music.amazon." in url or "amazon.com/music" in url

    # Amazon music functionality is fully covered by BaseMusicService + yt-dlp defaults
    # unless we need specific handling that base doesn't cover.


amazon_music_service = AmazonMusicService()
