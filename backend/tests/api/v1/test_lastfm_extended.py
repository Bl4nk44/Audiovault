"""Extended Last.fm API route tests covering disconnect, scrobble, profile, recommendations."""

from unittest.mock import AsyncMock, patch

import pytest
from app.api.v1.lastfm import get_lastfm_service
from app.main import app
from app.services.lastfm_service import LastfmError, LastfmService


@pytest.fixture
def mock_lastfm_service():
    with patch("app.services.lastfm_service.settings") as mock_settings:
        mock_settings.LASTFM_API_KEY = "test_key"
        mock_settings.LASTFM_API_SECRET = "test_secret"
        mock_settings.CALLBACK_URL = "http://test.com"
        service = LastfmService()
        service.get_session = AsyncMock()
        service.get_user_info = AsyncMock()
        service.get_user_friends = AsyncMock(return_value=[])
        yield service


@pytest.fixture(autouse=True)
def override_lastfm_dep(mock_lastfm_service):
    app.dependency_overrides[get_lastfm_service] = lambda: mock_lastfm_service
    yield
    app.dependency_overrides.pop(get_lastfm_service, None)


@pytest.mark.asyncio
async def test_disconnect_clears_session(client, admin_token_headers):
    response = await client.post("/api/v1/lastfm/disconnect", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "disconnected"


@pytest.mark.asyncio
async def test_callback_no_key_raises_400(client, admin_token_headers, mock_lastfm_service):
    mock_lastfm_service.get_session = AsyncMock(return_value={"name": "user", "key": None})
    response = await client.get("/api/v1/lastfm/callback?token=bad_token", headers=admin_token_headers)
    assert response.status_code == 400
    assert "session key" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_callback_lastfm_error_raises_400(client, admin_token_headers, mock_lastfm_service):
    mock_lastfm_service.get_session = AsyncMock(side_effect=LastfmError("Invalid token"))
    response = await client.get("/api/v1/lastfm/callback?token=bad_token", headers=admin_token_headers)
    assert response.status_code == 400
    assert "Last.fm authentication failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_connect_with_origin_header(client, admin_token_headers):
    response = await client.get(
        "/api/v1/lastfm/connect",
        headers={**admin_token_headers, "origin": "http://localhost:2137"},
    )
    assert response.status_code == 200
    assert "auth_url" in response.json()


@pytest.mark.asyncio
async def test_now_playing_ok(client, admin_token_headers, mock_lastfm_service):
    with patch("app.services.scrobbler.AudiovaultScrobbler") as mock_scrobbler_cls:
        mock_scrobbler = mock_scrobbler_cls.return_value
        mock_scrobbler.update_now_playing = AsyncMock()
        response = await client.post(
            "/api/v1/lastfm/scrobble/now_playing",
            json={"track": "Test Track", "artist": "Test Artist", "album": "Test Album"},
            headers=admin_token_headers,
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_scrobble_success(client, admin_token_headers, mock_lastfm_service):
    with patch("app.services.scrobbler.AudiovaultScrobbler") as mock_scrobbler_cls:
        mock_scrobbler = mock_scrobbler_cls.return_value
        mock_scrobbler.scrobble_track = AsyncMock(return_value=True)
        response = await client.post(
            "/api/v1/lastfm/scrobble",
            json={"track": "Test Track", "artist": "Test Artist", "timestamp": 1234567890},
            headers=admin_token_headers,
        )
    assert response.status_code == 200
    assert response.json()["status"] == "scrobbled"


@pytest.mark.asyncio
async def test_scrobble_ignored(client, admin_token_headers, mock_lastfm_service):
    with patch("app.services.scrobbler.AudiovaultScrobbler") as mock_scrobbler_cls:
        mock_scrobbler = mock_scrobbler_cls.return_value
        mock_scrobbler.scrobble_track = AsyncMock(return_value=False)
        response = await client.post(
            "/api/v1/lastfm/scrobble",
            json={"track": "Track", "artist": "Artist", "timestamp": 1234567890},
            headers=admin_token_headers,
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored_or_failed"


@pytest.mark.asyncio
async def test_profile_not_connected_returns_400(client, admin_token_headers):
    response = await client.get("/api/v1/lastfm/profile", headers=admin_token_headers)
    assert response.status_code == 400
    assert "not connected" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_profile_connected(client, admin_token_headers, db_session, admin_user, mock_lastfm_service):
    admin_user.lastfm_username = "lfm_user"
    admin_user.lastfm_session_key = "session_key_xyz"
    db_session.add(admin_user)
    await db_session.commit()

    mock_lastfm_service.get_user_info = AsyncMock(return_value={"name": "lfm_user", "playcount": "100"})
    mock_lastfm_service.get_user_friends = AsyncMock(return_value=[{"name": "friend1"}])

    response = await client.get("/api/v1/lastfm/profile", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert "friends" in data


@pytest.mark.asyncio
async def test_profile_user_info_fails_returns_500(
    client, admin_token_headers, db_session, admin_user, mock_lastfm_service
):
    admin_user.lastfm_username = "lfm_user"
    admin_user.lastfm_session_key = "key"
    db_session.add(admin_user)
    await db_session.commit()

    mock_lastfm_service.get_user_info = AsyncMock(side_effect=RuntimeError("API down"))
    mock_lastfm_service.get_user_friends = AsyncMock(return_value=[])

    response = await client.get("/api/v1/lastfm/profile", headers=admin_token_headers)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_profile_friends_fail_graceful(client, admin_token_headers, db_session, admin_user, mock_lastfm_service):
    admin_user.lastfm_username = "lfm_user"
    admin_user.lastfm_session_key = "key"
    db_session.add(admin_user)
    await db_session.commit()

    mock_lastfm_service.get_user_info = AsyncMock(return_value={"name": "lfm_user"})
    mock_lastfm_service.get_user_friends = AsyncMock(side_effect=RuntimeError("Friends API down"))

    response = await client.get("/api/v1/lastfm/profile", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["friends"] == []


@pytest.mark.asyncio
async def test_recommendations_endpoint(client, admin_token_headers, mock_lastfm_service):
    with patch("app.services.recommendation_engine.HybridRecommendationEngine") as mock_engine_cls:
        mock_engine = mock_engine_cls.return_value
        mock_engine.get_recommendations = AsyncMock(
            return_value={"tracks": [], "source": "auto", "generated_at": "2024-01-01T00:00:00"}
        )
        response = await client.get("/api/v1/lastfm/recommendations", headers=admin_token_headers)
    assert response.status_code == 200
