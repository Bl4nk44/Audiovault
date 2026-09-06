"""Tests for the listening-provider abstraction (Last.fm adapter + registry)."""

from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.listening import connected_providers, get_provider
from app.services.listening.base import ListeningError, ProviderCredentials
from app.services.listening.lastfm import LastfmProvider

NO_DB = cast(AsyncSession, None)  # db is unused on the paths under test


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
    assert await connected_providers(user, db=NO_DB) == []


@pytest.mark.asyncio
async def test_connected_providers_returns_lastfm_when_session_key_present():
    user = User(username="u", lastfm_session_key="sk", lastfm_username="lfm")
    pairs = await connected_providers(user, db=NO_DB)
    assert len(pairs) == 1
    prov, creds = pairs[0]
    assert prov.name == "lastfm"
    assert creds.secret == "sk"
    assert creds.username == "lfm"


# --- LastfmProvider adapter ---


@pytest.mark.asyncio
async def test_get_credentials_none_without_session_key(provider):
    assert await provider.get_credentials(User(username="u"), db=NO_DB) is None


@pytest.mark.asyncio
async def test_get_credentials_falls_back_to_username(provider):
    user = User(username="fallback", lastfm_session_key="sk")  # no lastfm_username
    creds = await provider.get_credentials(user, db=NO_DB)
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


# --- ListenBrainzProvider adapter ---


@pytest.fixture
def lb_service():
    return AsyncMock()


@pytest.fixture
def lb_provider(lb_service):
    from app.services.listening.listenbrainz import ListenBrainzProvider

    return ListenBrainzProvider(service=lb_service)


def test_registry_exposes_listenbrainz():
    p = get_provider("listenbrainz")
    assert p is not None
    assert p.display_name == "ListenBrainz"
    assert p.connects_with_token is True


@pytest.mark.asyncio
async def test_lb_validate_credentials_returns_identity(lb_provider, lb_service):
    lb_service.validate_token.return_value = "alice"
    identity = await lb_provider.validate_credentials("  tok  ")
    assert identity.username == "alice"
    lb_service.validate_token.assert_awaited_once_with("tok")


@pytest.mark.asyncio
async def test_lb_validate_credentials_wraps_error(lb_provider, lb_service):
    from app.services.listenbrainz_service import ListenBrainzError

    lb_service.validate_token.side_effect = ListenBrainzError("nope")
    with pytest.raises(ListeningError):
        await lb_provider.validate_credentials("bad")


@pytest.mark.asyncio
async def test_lb_get_credentials_none_when_not_stored(lb_provider):
    with patch(
        "app.services.listening.listenbrainz.credentials_service.get_tokens",
        new_callable=AsyncMock,
        return_value=None,
    ):
        assert await lb_provider.get_credentials(User(username="u"), db=NO_DB) is None


@pytest.mark.asyncio
async def test_lb_get_credentials_reads_encrypted_store(lb_provider):
    with patch(
        "app.services.listening.listenbrainz.credentials_service.get_tokens",
        new_callable=AsyncMock,
        return_value={"access_token": "secret-tok", "extra_data": {"username": "alice"}},
    ):
        creds = await lb_provider.get_credentials(User(username="u"), db=NO_DB)
    assert creds.secret == "secret-tok"
    assert creds.username == "alice"
    assert creds.provider == "listenbrainz"


@pytest.mark.asyncio
async def test_lb_scrobble_delegates(lb_provider, lb_service):
    creds = ProviderCredentials(provider="listenbrainz", username="alice", secret="tok")
    await lb_provider.scrobble(creds, "Track", "Artist", timestamp=99, album="Alb")
    lb_service.submit_listen.assert_awaited_once_with(
        "tok", track="Track", artist="Artist", listened_at=99, album="Alb"
    )


@pytest.mark.asyncio
async def test_lb_now_playing_delegates(lb_provider, lb_service):
    creds = ProviderCredentials(provider="listenbrainz", username="alice", secret="tok")
    await lb_provider.update_now_playing(creds, "Track", "Artist")
    lb_service.submit_now_playing.assert_awaited_once_with("tok", track="Track", artist="Artist", album=None)


@pytest.mark.asyncio
async def test_lb_connected_providers_includes_lb_when_stored():
    user = User(username="u")
    with patch(
        "app.services.listening.listenbrainz.credentials_service.get_tokens",
        new_callable=AsyncMock,
        return_value={"access_token": "tok", "extra_data": {"username": "alice"}},
    ):
        pairs = await connected_providers(user, db=NO_DB)
    names = {p.name for p, _ in pairs}
    assert "listenbrainz" in names


# --- get_seeds / get_recommended_artists coverage ---


@pytest.mark.asyncio
async def test_lastfm_get_seeds_delegates_and_listifies(provider, lastfm_service):
    lastfm_service._gather_seeds = AsyncMock(return_value=([("Song", "Artist")], {"Artist", "Other"}))
    creds = ProviderCredentials(provider="lastfm", username="lfm", secret="sk")

    seed_tracks, seed_artists = await provider.get_seeds(creds, variety=True)

    lastfm_service._gather_seeds.assert_awaited_once_with("lfm", "sk", variety=True)
    assert seed_tracks == [("Song", "Artist")]
    assert sorted(seed_artists) == ["Artist", "Other"]


@pytest.mark.asyncio
async def test_lastfm_get_seeds_wraps_error(provider, lastfm_service):
    from app.services.lastfm_service import LastfmError

    lastfm_service._gather_seeds = AsyncMock(side_effect=LastfmError("down"))
    with pytest.raises(ListeningError):
        await provider.get_seeds(ProviderCredentials(provider="lastfm", username="l", secret="s"))


@pytest.mark.asyncio
async def test_lastfm_get_recommended_artists_delegates(provider, lastfm_service):
    lastfm_service.get_recommended_artists = AsyncMock(return_value=["x"])
    creds = ProviderCredentials(provider="lastfm", username="lfm", secret="sk")

    out = await provider.get_recommended_artists(creds, limit=7)

    lastfm_service.get_recommended_artists.assert_awaited_once_with("sk", limit=7, user_name="lfm")
    assert out == ["x"]


@pytest.mark.asyncio
async def test_lastfm_update_now_playing_wraps_error(provider, lastfm_service):
    from app.services.lastfm_service import LastfmError

    lastfm_service.update_now_playing.side_effect = LastfmError("boom")
    with pytest.raises(ListeningError):
        await provider.update_now_playing(ProviderCredentials(provider="lastfm", username="l", secret="s"), "T", "A")


@pytest.mark.asyncio
async def test_lb_get_seeds_maps_stats(lb_provider, lb_service):
    lb_service.get_top_tracks.return_value = [{"name": "T1", "artist": "A1"}, {"name": "no artist"}]
    lb_service.get_recent_tracks.return_value = [{"name": "T2", "artist": "A2"}]
    lb_service.get_top_artists.return_value = [{"name": "A1"}, {"name": "A3"}, {"nope": 1}]
    creds = ProviderCredentials(provider="listenbrainz", username="alice", secret="tok")

    seed_tracks, seed_artists = await lb_provider.get_seeds(creds, variety=False)

    assert ("T1", "A1") in seed_tracks and ("T2", "A2") in seed_tracks
    assert len(seed_tracks) == 2
    assert seed_artists == ["A1", "A3"]


@pytest.mark.asyncio
async def test_lb_get_seeds_tolerates_partial_failure(lb_provider, lb_service):
    from app.services.listenbrainz_service import ListenBrainzError

    lb_service.get_top_tracks.side_effect = ListenBrainzError("stats not ready")
    lb_service.get_recent_tracks.return_value = [{"name": "T", "artist": "A"}]
    lb_service.get_top_artists.return_value = []
    creds = ProviderCredentials(provider="listenbrainz", username="alice", secret="tok")

    seed_tracks, seed_artists = await lb_provider.get_seeds(creds)

    assert seed_tracks == [("T", "A")]
    assert seed_artists == []


@pytest.mark.asyncio
async def test_lb_get_profile_delegates(lb_provider, lb_service):
    lb_service.get_profile.return_value = {"user": {"name": "alice"}}
    creds = ProviderCredentials(provider="listenbrainz", username="alice", secret="tok")
    assert await lb_provider.get_profile(creds) == {"user": {"name": "alice"}}


@pytest.mark.asyncio
async def test_lb_get_profile_wraps_error(lb_provider, lb_service):
    from app.services.listenbrainz_service import ListenBrainzError

    lb_service.get_profile.side_effect = ListenBrainzError("down")
    with pytest.raises(ListeningError):
        await lb_provider.get_profile(ProviderCredentials(provider="listenbrainz", username="a", secret="t"))
