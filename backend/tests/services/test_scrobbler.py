from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.listening.base import ListeningError, ProviderCredentials
from app.services.scrobbler import AudiovaultScrobbler, scrobbling_enabled

NO_DB = cast(AsyncSession, None)  # db is unused on the paths under test


def _creds(name: str) -> ProviderCredentials:
    return ProviderCredentials(provider=name, username=f"{name}_user", secret="secret")


def _fake_provider(name: str):
    p = AsyncMock()
    p.name = name
    return p


@pytest.fixture
def user():
    u = User(username="test")
    u.preferences = {"scrobble_enabled": True}
    return u


@pytest.mark.asyncio
async def test_scrobble_fans_out_to_every_provider(user):
    lfm, lbz = _fake_provider("lastfm"), _fake_provider("listenbrainz")
    scrobbler = AudiovaultScrobbler([(lfm, _creds("lastfm")), (lbz, _creds("listenbrainz"))])

    result = await scrobbler.scrobble_track(user, "Track", "Artist", timestamp=111)

    assert result is True
    lfm.scrobble.assert_awaited_once()
    lbz.scrobble.assert_awaited_once()


@pytest.mark.asyncio
async def test_now_playing_fans_out(user):
    lfm, lbz = _fake_provider("lastfm"), _fake_provider("listenbrainz")
    scrobbler = AudiovaultScrobbler([(lfm, _creds("lastfm")), (lbz, _creds("listenbrainz"))])

    await scrobbler.update_now_playing(user, "Track", "Artist")

    lfm.update_now_playing.assert_awaited_once()
    lbz.update_now_playing.assert_awaited_once()


@pytest.mark.asyncio
async def test_one_provider_failure_does_not_block_the_other(user):
    lfm, lbz = _fake_provider("lastfm"), _fake_provider("listenbrainz")
    lfm.scrobble.side_effect = ListeningError("lastfm down")
    scrobbler = AudiovaultScrobbler([(lfm, _creds("lastfm")), (lbz, _creds("listenbrainz"))])

    result = await scrobbler.scrobble_track(user, "Track", "Artist")

    assert result is True  # listenbrainz still accepted it
    lbz.scrobble.assert_awaited_once()


@pytest.mark.asyncio
async def test_all_providers_fail_returns_false(user):
    lfm = _fake_provider("lastfm")
    lfm.scrobble.side_effect = ListeningError("down")
    scrobbler = AudiovaultScrobbler([(lfm, _creds("lastfm"))])

    assert await scrobbler.scrobble_track(user, "Track", "Artist") is False


@pytest.mark.asyncio
async def test_no_providers_is_a_noop(user):
    scrobbler = AudiovaultScrobbler([])
    assert scrobbler.has_targets is False
    assert await scrobbler.scrobble_track(user, "Track", "Artist") is False
    await scrobbler.update_now_playing(user, "Track", "Artist")  # no raise


@pytest.mark.asyncio
async def test_for_user_skips_everything_when_scrobbling_disabled():
    u = User(username="test")
    u.preferences = {"scrobble_enabled": False}

    with patch("app.services.scrobbler.connected_providers", new_callable=AsyncMock) as mock_conn:
        scrobbler = await AudiovaultScrobbler.for_user(u, db=NO_DB)

    mock_conn.assert_not_awaited()
    assert scrobbler.has_targets is False


@pytest.mark.asyncio
async def test_for_user_builds_from_connected_providers(user):
    lfm = _fake_provider("lastfm")
    with patch(
        "app.services.scrobbler.connected_providers",
        new_callable=AsyncMock,
        return_value=[(lfm, _creds("lastfm"))],
    ):
        scrobbler = await AudiovaultScrobbler.for_user(user, db=NO_DB)

    assert scrobbler.has_targets is True


def test_scrobbling_enabled_defaults_true():
    u = User(username="test")
    u.preferences = {}
    assert scrobbling_enabled(u) is True


def test_scrobbling_enabled_respects_pref():
    u = User(username="test")
    u.preferences = {"scrobble_enabled": False}
    assert scrobbling_enabled(u) is False
