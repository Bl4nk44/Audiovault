"""Last.fm as a :class:`ListeningProvider` — thin adapter over ``LastfmService``.

No behaviour of its own: it maps the provider contract onto the existing
``LastfmService`` calls and the ``lastfm_*`` columns on ``User``.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

from app.services.lastfm_service import LastfmError, LastfmService
from app.services.listening.base import (
    ListeningError,
    ListeningProvider,
    ProviderCredentials,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = logging.getLogger(__name__)


class LastfmProvider(ListeningProvider):
    name = "lastfm"
    display_name = "Last.fm"
    supports_recommendations = True
    connects_with_token = False

    def __init__(self, service: LastfmService | None = None) -> None:
        self._service = service or LastfmService()

    async def get_credentials(self, user: User, db: AsyncSession) -> ProviderCredentials | None:
        if not user.lastfm_session_key:
            return None
        return ProviderCredentials(
            provider=self.name,
            username=user.lastfm_username or user.username,
            secret=user.lastfm_session_key,
        )

    async def update_now_playing(
        self, creds: ProviderCredentials, track: str, artist: str, album: str | None = None
    ) -> None:
        try:
            await self._service.update_now_playing(track=track, artist=artist, session_key=creds.secret, album=album)
        except LastfmError as e:
            raise ListeningError(str(e)) from e

    async def scrobble(
        self,
        creds: ProviderCredentials,
        track: str,
        artist: str,
        timestamp: int,
        album: str | None = None,
    ) -> None:
        try:
            await self._service.scrobble(
                track=track, artist=artist, session_key=creds.secret, timestamp=timestamp, album=album
            )
        except LastfmError as e:
            raise ListeningError(str(e)) from e

    async def get_profile(self, creds: ProviderCredentials) -> dict:
        try:
            info, friends = await asyncio.gather(
                self._service.get_user_info(creds.username),
                self._service.get_user_friends(creds.username, limit=8),
                return_exceptions=True,
            )
            if isinstance(info, BaseException):
                raise ListeningError(str(info))
            return {"user": info, "friends": [] if isinstance(friends, BaseException) else friends}
        except LastfmError as e:
            raise ListeningError(str(e)) from e
