import logging
from typing import Optional

from app.models.user import User
from app.services.lastfm_service import LastfmError, LastfmService

logger = logging.getLogger(__name__)


class AudiovaultScrobbler:
    def __init__(self, lastfm_service: LastfmService):
        self.lastfm = lastfm_service

    async def update_now_playing(self, user: User, track: str, artist: str, album: Optional[str] = None) -> None:
        """Update "Now Playing" status on Last.fm if enabled."""
        if not user.lastfm_session_key:
            return

        try:
            await self.lastfm.update_now_playing(
                track=track, artist=artist, session_key=user.lastfm_session_key, album=album
            )
            logger.debug(f"Updated Now Playing for {user.username}: {artist} - {track}")
        except LastfmError as e:
            logger.error(f"Failed to update now playing for {user.username}: {e}")

    async def scrobble_track(
        self, user: User, track: str, artist: str, timestamp: Optional[int] = None, album: Optional[str] = None
    ) -> bool:
        """Scrobble a track to Last.fm."""
        if not user.lastfm_session_key:
            return False

        try:
            await self.lastfm.scrobble(
                track=track, artist=artist, session_key=user.lastfm_session_key, timestamp=timestamp, album=album
            )
            logger.info(f"Scrobbled for {user.username}: {artist} - {track}")
            return True
        except LastfmError as e:
            logger.error(f"Failed to scrobble for {user.username}: {e}")
            return False

    def _should_scrobble(self, user: User) -> bool:
        """Check if user has Last.fm connected and enabled."""
        if not user.lastfm_session_key:
            return False

        # Check user preferences if available
        # Default to True if logic not implemented yet in preferences
        preferences = user.preferences or {}
        return preferences.get("scrobble_enabled", True)
