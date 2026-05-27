from unittest.mock import AsyncMock, Mock

import pytest

from app.models.user import User
from app.services.lastfm_service import LastfmError, LastfmService
from app.services.scrobbler import AudiovaultScrobbler


@pytest.fixture
def mock_lastfm_service():
    service = Mock(spec=LastfmService)
    service.update_now_playing = AsyncMock()
    service.scrobble = AsyncMock()
    return service


@pytest.fixture
def scrobbler(mock_lastfm_service):
    return AudiovaultScrobbler(mock_lastfm_service)


@pytest.fixture
def user_connected():
    user = User(username="test", lastfm_session_key="key")
    user.preferences = {"scrobble_enabled": True}
    return user


@pytest.fixture
def user_disconnected():
    user = User(username="test", lastfm_session_key=None)
    return user


@pytest.mark.asyncio
async def test_update_now_playing_success(scrobbler, mock_lastfm_service, user_connected):
    await scrobbler.update_now_playing(user_connected, "Track", "Artist")
    mock_lastfm_service.update_now_playing.assert_called_once()


@pytest.mark.asyncio
async def test_scrobble_track_success(scrobbler, mock_lastfm_service, user_connected):
    result = await scrobbler.scrobble_track(user_connected, "Track", "Artist")
    assert result is True
    mock_lastfm_service.scrobble.assert_called_once()


@pytest.mark.asyncio
async def test_disconnected_user_no_op(scrobbler, mock_lastfm_service, user_disconnected):
    await scrobbler.update_now_playing(user_disconnected, "Track", "Artist")
    await scrobbler.scrobble_track(user_disconnected, "Track", "Artist")

    mock_lastfm_service.update_now_playing.assert_not_called()
    mock_lastfm_service.scrobble.assert_not_called()


@pytest.mark.asyncio
async def test_scrobble_error_handling(scrobbler, mock_lastfm_service, user_connected):
    mock_lastfm_service.scrobble.side_effect = LastfmError("Fail")

    result = await scrobbler.scrobble_track(user_connected, "Track", "Artist")
    assert result is False


@pytest.mark.asyncio
async def test_update_now_playing_lastfm_error(scrobbler, mock_lastfm_service, user_connected):
    mock_lastfm_service.update_now_playing.side_effect = LastfmError("API error")
    # Should not raise, error is caught internally
    await scrobbler.update_now_playing(user_connected, "Track", "Artist")


def test_should_scrobble_connected_no_prefs(scrobbler):
    user = User(username="test", lastfm_session_key="key")
    user.preferences = {}
    assert scrobbler._should_scrobble(user) is True


def test_should_scrobble_disconnected(scrobbler):
    user = User(username="test", lastfm_session_key=None)
    assert scrobbler._should_scrobble(user) is False


def test_should_scrobble_disabled_in_prefs(scrobbler):
    user = User(username="test", lastfm_session_key="key")
    user.preferences = {"scrobble_enabled": False}
    assert scrobbler._should_scrobble(user) is False
