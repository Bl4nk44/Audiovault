"""Listening-provider registry and per-user connection lookup."""

import logging
from typing import TYPE_CHECKING

from app.services.listening.base import ListeningProvider, ProviderCredentials
from app.services.listening.lastfm import LastfmProvider

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = logging.getLogger(__name__)

#: All known providers, keyed by their stable ``name``. Order defines the
#: fan-out / "first connected" preference order.
PROVIDERS: dict[str, ListeningProvider] = {p.name: p for p in (LastfmProvider(),)}


def get_provider(name: str) -> ListeningProvider | None:
    return PROVIDERS.get(name)


async def connected_providers(user: User, db: AsyncSession) -> list[tuple[ListeningProvider, ProviderCredentials]]:
    """Return ``(provider, credentials)`` pairs for every provider ``user`` has connected."""
    out: list[tuple[ListeningProvider, ProviderCredentials]] = []
    for provider in PROVIDERS.values():
        try:
            creds = await provider.get_credentials(user, db)
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("Failed to resolve %s credentials for user %s: %s", provider.name, user.id, e)
            continue
        if creds is not None:
            out.append((provider, creds))
    return out
