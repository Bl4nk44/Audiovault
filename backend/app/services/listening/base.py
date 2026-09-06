"""Provider-agnostic contract for listening / scrobbling services."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User


class ListeningError(Exception):
    """Any failure talking to a listening provider (auth, HTTP, API error)."""


@dataclass(frozen=True)
class ProviderIdentity:
    """Result of validating a raw credential — who the credential belongs to."""

    username: str


@dataclass(frozen=True)
class ProviderCredentials:
    """A resolved, ready-to-use credential for one connected provider.

    ``secret`` is whatever the provider authenticates requests with — a Last.fm
    session key or a ListenBrainz user token.
    """

    provider: str
    username: str
    secret: str


class ListeningProvider(ABC):
    """One external listening service (Last.fm, ListenBrainz, ...).

    Implementations wrap the concrete HTTP client and adapt it to this shape so
    the scrobbler and (later) the recommendation engine never branch on which
    service is in use.
    """

    #: stable identifier used in URLs, preferences and the credentials store
    name: str
    #: human-facing label
    display_name: str
    #: whether this provider can generate recommendations on its own
    supports_recommendations: bool = True
    #: True when connecting means pasting a secret we can validate directly
    #: (ListenBrainz); False for redirect/token-exchange flows (Last.fm).
    connects_with_token: bool = False

    async def validate_credentials(self, raw_secret: str) -> ProviderIdentity:
        """Check a user-supplied secret and return the account it belongs to.

        Only meaningful for token-paste providers (``connects_with_token``).
        Raises :class:`ListeningError` if the secret is invalid or the provider
        uses a different connect flow.
        """
        raise ListeningError(f"{self.name} does not support direct token validation")

    @abstractmethod
    async def get_credentials(self, user: User, db: AsyncSession) -> ProviderCredentials | None:
        """Return the stored credential for ``user``, or ``None`` if not connected."""

    @abstractmethod
    async def update_now_playing(
        self, creds: ProviderCredentials, track: str, artist: str, album: str | None = None
    ) -> None:
        """Set the "now playing" track. Raises :class:`ListeningError` on failure."""

    @abstractmethod
    async def scrobble(
        self,
        creds: ProviderCredentials,
        track: str,
        artist: str,
        timestamp: int,
        album: str | None = None,
    ) -> None:
        """Record a completed play. Raises :class:`ListeningError` on failure."""

    @abstractmethod
    async def get_profile(self, creds: ProviderCredentials) -> dict:
        """Return public profile info for the connected account."""
