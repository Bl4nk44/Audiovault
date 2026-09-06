"""ListenBrainz as a :class:`ListeningProvider`.

Credentials live in the encrypted ``service_credentials`` table
(``service="listenbrainz"``): the personal token in ``access_token``, the
resolved username in ``extra_data.username``.
"""

import logging
from typing import TYPE_CHECKING

from app.services.credentials_service import credentials_service
from app.services.listenbrainz_service import ListenBrainzError, ListenBrainzService
from app.services.listening.base import (
    ListeningError,
    ListeningProvider,
    ProviderCredentials,
    ProviderIdentity,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = logging.getLogger(__name__)

SERVICE_NAME = "listenbrainz"


class ListenBrainzProvider(ListeningProvider):
    name = SERVICE_NAME
    display_name = "ListenBrainz"
    supports_recommendations = True
    connects_with_token = True

    def __init__(self, service: ListenBrainzService | None = None) -> None:
        self._service = service or ListenBrainzService()

    async def validate_credentials(self, raw_secret: str) -> ProviderIdentity:
        try:
            username = await self._service.validate_token(raw_secret.strip())
        except ListenBrainzError as e:
            raise ListeningError(str(e)) from e
        return ProviderIdentity(username=username)

    async def get_credentials(self, user: User, db: AsyncSession) -> ProviderCredentials | None:
        tokens = await credentials_service.get_tokens(db, user.id, SERVICE_NAME)
        if not tokens or not tokens.get("access_token"):
            return None
        username = (tokens.get("extra_data") or {}).get("username") or user.username
        return ProviderCredentials(provider=self.name, username=username, secret=tokens["access_token"])

    async def update_now_playing(
        self, creds: ProviderCredentials, track: str, artist: str, album: str | None = None
    ) -> None:
        try:
            await self._service.submit_now_playing(creds.secret, track=track, artist=artist, album=album)
        except ListenBrainzError as e:
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
            await self._service.submit_listen(
                creds.secret, track=track, artist=artist, listened_at=timestamp, album=album
            )
        except ListenBrainzError as e:
            raise ListeningError(str(e)) from e

    async def get_profile(self, creds: ProviderCredentials) -> dict:
        try:
            return await self._service.get_profile(creds.username)
        except ListenBrainzError as e:
            raise ListeningError(str(e)) from e
