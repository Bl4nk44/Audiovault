"""Tests for the listening-provider abstraction (Last.fm adapter + registry)."""

from unittest.mock import AsyncMock

import pytest

from app.models.user import User
from app.services.listening import connected_providers, get_provider
from app.services.listening.base import ListeningError, ProviderCredentials
from app.services.listening.lastfm import LastfmProvider


@pytest.fixture
def lastfm_service():
    svc = AsyncMock()
    return svc


@pytest.fixture
def provider(lastfm_service):
    return LastfmProvider(service=lastfm_service)


# --- registry ---


def test_registry_exposes_lastfm():
    p = get_provider("lastfm")
    assert isinstance(p, LastfmProvider)
    assert p.display_name == "Last.fm"


def test_registry_unknown_provider_is_none():
    assert get_provider("bandcamp") is None


@pytest.mark.asyncio
async def test_connected_providers_empty_when_nothing_linked():
    user = User(username="u")
    assert await connected_providers(user, db=None) == []


@pytest.mark.asyncio
async def test_connected_providers_returns_lastfm_when_session_key_present():
    user = User(username="u", lastfm_session_key="sk", lastfm_username="lfm")
    pairs = await connected_providers(user, db=None)
    assert len(pairs) == 1
    prov, creds = pairs[0]
    assert prov.name == "lastfm"
    assert creds.secret == "sk"
    assert creds.username == "lfm"


# --- LastfmProvider adapter ---


@pytest.mark.asyncio
async def test_get_credentials_none_without_session_key(provider):
    assert await provider.get_credentials(User(username="u"), db=None) is None


@pytest.mark.asyncio
async def test_get_credentials_falls_back_to_username(provider):
    user = User(username="fallback", lastfm_session_key="sk")  # no lastfm_username
    creds = await provider.get_credentials(user, db=None)
    assert creds.username == "fallback"


@pytest.mark.asyncio
async def test_scrobble_delegates_to_service(provider, lastfm_service):
    creds = ProviderCredentials(provider="lastfm", username="lfm", secret="sk")
    await provider.scrobble(creds, "Track", "Artist", timestamp=123, album="Album")

    lastfm_service.scrobble.assert_awaited_once_with(
        track="Track", artist="Artist", session_key="sk", timestamp=123, album="Album"
    )


@pytest.mark.asyncio
async def test_now_playing_delegates_to_service(provider, lastfm_service):
    creds = ProviderCredentials(provider="lastfm", username="lfm", secret="sk")
    await provider.update_now_playing(creds, "Track", "Artist")

    lastfm_service.update_now_playing.assert_awaited_once_with(
        track="Track", artist="Artist", session_key="sk", album=None
    )


@pytest.mark.asyncio
async def test_service_error_is_wrapped_as_listening_error(provider, lastfm_service):
    from app.services.lastfm_service import LastfmError

    lastfm_service.scrobble.side_effect = LastfmError("boom")
    creds = ProviderCredentials(provider="lastfm", username="lfm", secret="sk")

    with pytest.raises(ListeningError):
        await provider.scrobble(creds, "T", "A", timestamp=1)


@pytest.mark.asyncio
async def test_get_profile_combines_info_and_friends(provider, lastfm_service):
    lastfm_service.get_user_info.return_value = {"name": "lfm", "playcount": 10}
    lastfm_service.get_user_friends.return_value = [{"name": "friendA"}]
    creds = ProviderCredentials(provider="lastfm", username="lfm", secret="sk")

    profile = await provider.get_profile(creds)

    assert profile["user"]["name"] == "lfm"
    assert profile["friends"] == [{"name": "friendA"}]


@pytest.mark.asyncio
async def test_get_profile_degrades_when_friends_fail(provider, lastfm_service):
    lastfm_service.get_user_info.return_value = {"name": "lfm"}
    lastfm_service.get_user_friends.side_effect = RuntimeError("friends down")
    creds = ProviderCredentials(provider="lastfm", username="lfm", secret="sk")

    profile = await provider.get_profile(creds)

    assert profile["user"]["name"] == "lfm"
    assert profile["friends"] == []


@pytest.mark.asyncio
async def test_validate_credentials_unsupported_for_lastfm(provider):
    with pytest.raises(ListeningError):
        await provider.validate_credentials("whatever")
