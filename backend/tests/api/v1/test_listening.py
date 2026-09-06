"""Tests for the provider-agnostic /api/v1/listening/* routes."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.listenbrainz_service import ListenBrainzError, ListenBrainzService


@pytest.mark.asyncio
async def test_list_providers_shows_both(client, admin_token_headers):
    response = await client.get("/api/v1/listening/providers", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    names = {p["name"] for p in data["providers"]}
    assert {"lastfm", "listenbrainz"} <= names
    lb = next(p for p in data["providers"] if p["name"] == "listenbrainz")
    assert lb["connects_with_token"] is True
    assert lb["connected"] is False
    assert data["preference"] == "auto"


@pytest.mark.asyncio
async def test_connect_listenbrainz_stores_token(client, admin_token_headers):
    with (
        patch.object(ListenBrainzService, "validate_token", new_callable=AsyncMock, return_value="alice"),
        patch("app.api.v1.listening.credentials_service.store_tokens", new_callable=AsyncMock) as mock_store,
    ):
        response = await client.post(
            "/api/v1/listening/connect/listenbrainz",
            json={"token": "lb-secret-token"},
            headers=admin_token_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "connected", "provider": "listenbrainz", "username": "alice"}
    mock_store.assert_awaited_once()
    assert mock_store.await_args is not None
    kwargs = mock_store.await_args.kwargs
    assert kwargs["access_token"] == "lb-secret-token"
    assert kwargs["extra_data"]["username"] == "alice"


@pytest.mark.asyncio
async def test_connect_listenbrainz_missing_token_400(client, admin_token_headers):
    response = await client.post(
        "/api/v1/listening/connect/listenbrainz", json={"token": "   "}, headers=admin_token_headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_connect_listenbrainz_invalid_token_400(client, admin_token_headers):
    with patch.object(
        ListenBrainzService, "validate_token", new_callable=AsyncMock, side_effect=ListenBrainzError("bad")
    ):
        response = await client.post(
            "/api/v1/listening/connect/listenbrainz",
            json={"token": "nope"},
            headers=admin_token_headers,
        )
    assert response.status_code == 400
    assert "authentication failed" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_connect_lastfm_returns_auth_url(client, admin_token_headers):
    response = await client.post(
        "/api/v1/listening/connect/lastfm",
        headers={**admin_token_headers, "origin": "http://localhost:2137"},
    )
    assert response.status_code == 200
    assert "auth_url" in response.json()


@pytest.mark.asyncio
async def test_connect_unknown_provider_404(client, admin_token_headers):
    response = await client.post("/api/v1/listening/connect/bandcamp", json={"token": "x"}, headers=admin_token_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_disconnect_listenbrainz(client, admin_token_headers):
    with patch("app.api.v1.listening.credentials_service.delete_credentials", new_callable=AsyncMock) as mock_del:
        response = await client.post("/api/v1/listening/disconnect/listenbrainz", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["provider"] == "listenbrainz"
    mock_del.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_preference_valid(client, admin_token_headers):
    response = await client.put(
        "/api/v1/listening/preference",
        json={"listening_provider": "listenbrainz"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["listening_provider"] == "listenbrainz"

    # and it shows up in /providers
    providers = await client.get("/api/v1/listening/providers", headers=admin_token_headers)
    assert providers.json()["preference"] == "listenbrainz"


@pytest.mark.asyncio
async def test_set_preference_invalid_400(client, admin_token_headers):
    response = await client.put(
        "/api/v1/listening/preference",
        json={"listening_provider": "spotify"},
        headers=admin_token_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_profile_not_connected_400(client, admin_token_headers):
    response = await client.get("/api/v1/listening/profile/listenbrainz", headers=admin_token_headers)
    assert response.status_code == 400
    assert "not connected" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_scrobble_fans_out(client, admin_token_headers):
    fake = AsyncMock()
    fake.scrobble_track = AsyncMock(return_value=True)
    with patch("app.api.v1.listening.AudiovaultScrobbler.for_user", new_callable=AsyncMock, return_value=fake):
        response = await client.post(
            "/api/v1/listening/scrobble",
            json={"track": "T", "artist": "A", "timestamp": 1},
            headers=admin_token_headers,
        )
    assert response.status_code == 200
    assert response.json()["status"] == "scrobbled"
    fake.scrobble_track.assert_awaited_once()


@pytest.mark.asyncio
async def test_unauthenticated_rejected(client):
    assert (await client.get("/api/v1/listening/providers")).status_code == 401


@pytest.mark.asyncio
async def test_disconnect_lastfm_clears_columns(client, admin_token_headers, db_session, admin_user):
    admin_user.lastfm_session_key = "sk"
    admin_user.lastfm_username = "lfm"
    db_session.add(admin_user)
    await db_session.commit()

    response = await client.post("/api/v1/listening/disconnect/lastfm", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["provider"] == "lastfm"

    await db_session.refresh(admin_user)
    assert admin_user.lastfm_session_key is None
    assert admin_user.lastfm_username is None


@pytest.mark.asyncio
async def test_disconnect_unknown_provider_404(client, admin_token_headers):
    response = await client.post("/api/v1/listening/disconnect/bandcamp", headers=admin_token_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_profile_success(client, admin_token_headers):
    from app.services.listening.registry import PROVIDERS

    lb = PROVIDERS["listenbrainz"]
    with (
        patch.object(
            lb,
            "get_credentials",
            new_callable=AsyncMock,
            return_value=type("C", (), {"provider": "listenbrainz", "username": "alice", "secret": "t"})(),
        ),
        patch.object(lb, "get_profile", new_callable=AsyncMock, return_value={"user": {"name": "alice"}}),
    ):
        response = await client.get("/api/v1/listening/profile/listenbrainz", headers=admin_token_headers)

    assert response.status_code == 200
    assert response.json()["user"]["name"] == "alice"


@pytest.mark.asyncio
async def test_profile_unknown_provider_404(client, admin_token_headers):
    response = await client.get("/api/v1/listening/profile/bandcamp", headers=admin_token_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_now_playing_fans_out(client, admin_token_headers):
    fake = AsyncMock()
    fake.update_now_playing = AsyncMock()
    with patch("app.api.v1.listening.AudiovaultScrobbler.for_user", new_callable=AsyncMock, return_value=fake):
        response = await client.post(
            "/api/v1/listening/scrobble/now_playing",
            json={"track": "T", "artist": "A"},
            headers=admin_token_headers,
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    fake.update_now_playing.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrobble_ignored_when_no_targets(client, admin_token_headers):
    fake = AsyncMock()
    fake.scrobble_track = AsyncMock(return_value=False)
    with patch("app.api.v1.listening.AudiovaultScrobbler.for_user", new_callable=AsyncMock, return_value=fake):
        response = await client.post(
            "/api/v1/listening/scrobble",
            json={"track": "T", "artist": "A", "timestamp": 1},
            headers=admin_token_headers,
        )
    assert response.json()["status"] == "ignored_or_failed"
