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
