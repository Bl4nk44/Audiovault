"""Listening-service providers — scrobbling and listening-metadata backends.

A "listening provider" is an external service that records what the user plays
and exposes their listening history (Last.fm, ListenBrainz). Providers share the
:class:`~app.services.listening.base.ListeningProvider` interface so scrobbling
and recommendations are provider-agnostic; the user may connect more than one and
scrobbles fan out to all of them.
"""

from app.services.listening.base import (
    ListeningError,
    ListeningProvider,
    ProviderCredentials,
    ProviderIdentity,
)
from app.services.listening.registry import (
    PROVIDERS,
    connected_providers,
    get_provider,
)

__all__ = [
    "PROVIDERS",
    "ListeningError",
    "ListeningProvider",
    "ProviderCredentials",
    "ProviderIdentity",
    "connected_providers",
    "get_provider",
]
