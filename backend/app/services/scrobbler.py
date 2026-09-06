import logging
import time
from typing import TYPE_CHECKING

from app.models.user import User
from app.services.listening.base import ListeningError, ListeningProvider, ProviderCredentials
from app.services.listening.registry import connected_providers
from app.utils.log_sanitize import sanitize_log

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def scrobbling_enabled(user: User) -> bool:
    """Whether the user has scrobbling turned on (default on)."""
    preferences = user.preferences or {}
    return bool(preferences.get("scrobble_enabled", True))


class AudiovaultScrobbler:
    """Fans a play/now-playing event out to every listening provider the user
    has connected (Last.fm, ListenBrainz, ...). Best effort — a failure on one
    provider never blocks the others."""

    def __init__(self, providers: list[tuple[ListeningProvider, ProviderCredentials]] | None = None) -> None:
        self._providers = providers or []

    @classmethod
    async def for_user(cls, user: User, db: AsyncSession) -> AudiovaultScrobbler:
        """Build a scrobbler bound to ``user``'s connected providers.

        Returns an empty (no-op) scrobbler if scrobbling is disabled or nothing
        is connected.
        """
        if not scrobbling_enabled(user):
            return cls([])
        return cls(await connected_providers(user, db))

    @property
    def has_targets(self) -> bool:
        return bool(self._providers)

    async def update_now_playing(self, user: User, track: str, artist: str, album: str | None = None) -> None:
        artist_name = artist or "Unknown Artist"
        for provider, creds in self._providers:
            try:
                await provider.update_now_playing(creds, track=track, artist=artist_name, album=album)
                logger.debug(
                    "Now playing on %s for %s: %s - %s",
                    provider.name,
                    sanitize_log(user.username),
                    sanitize_log(artist_name),
                    sanitize_log(track),
                )
            except ListeningError as e:
                logger.error("Failed now-playing on %s for %s: %s", provider.name, sanitize_log(user.username), e)

    async def scrobble_track(
        self,
        user: User,
        track: str,
        artist: str,
        timestamp: int | None = None,
        album: str | None = None,
    ) -> bool:
        """Scrobble to every connected provider. Returns True if at least one accepted it."""
        artist_name = artist or "Unknown Artist"
        ts = timestamp or int(time.time())
        scrobbled_anywhere = False
        for provider, creds in self._providers:
            try:
                await provider.scrobble(creds, track=track, artist=artist_name, timestamp=ts, album=album)
                scrobbled_anywhere = True
                logger.info(
                    "Scrobbled on %s for %s: %s - %s",
                    provider.name,
                    sanitize_log(user.username),
                    sanitize_log(artist_name),
                    sanitize_log(track),
                )
            except ListeningError as e:
                logger.error("Failed to scrobble on %s for %s: %s", provider.name, sanitize_log(user.username), e)
        return scrobbled_anywhere
