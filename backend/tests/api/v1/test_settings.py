import pytest

from app.models.credentials import ServiceCredentials


@pytest.fixture
async def setup_credentials(db_session, admin_user):
    creds = ServiceCredentials(
        user_id=admin_user.id, service="spotify", extra_data={"client_id": "old_id", "client_secret": "old_secret"}
    )
    db_session.add(creds)
    await db_session.commit()


@pytest.mark.asyncio
async def test_get_settings_defaults(client, admin_token_headers):
    response = await client.get("/api/v1/settings/", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["theme"] == "dark"  # default
    assert data["spotifyClientId"] == ""  # no creds yet


@pytest.mark.asyncio
async def test_get_settings_with_creds(client, admin_token_headers, setup_credentials):
    response = await client.get("/api/v1/settings/", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["spotifyClientId"] == "old_id"


@pytest.mark.asyncio
async def test_update_settings(client, admin_token_headers, db_session, admin_user):
    payload = {"spotifyClientId": "new_id", "theme": "light", "downloadPath": "/new/path"}
    response = await client.post("/api/v1/settings/", json=payload, headers=admin_token_headers)
    assert response.status_code == 200

    # Verify response or refetch
    response = await client.get("/api/v1/settings/", headers=admin_token_headers)
    data = response.json()
    assert data["spotifyClientId"] == "new_id"
    assert data["theme"] == "light"
    assert data["downloadPath"] == "/new/path"
