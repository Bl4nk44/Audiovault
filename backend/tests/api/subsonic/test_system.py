import pytest
from httpx import AsyncClient


@pytest.fixture
def subsonic_auth_params(admin_user):
    return {
        "u": admin_user.username,
        "p": "admin",  # Default password in test fixtures
        "c": "pytest",
        "v": "1.16.1",
        "f": "json",
    }


@pytest.mark.asyncio
async def test_subsonic_ping(client: AsyncClient, subsonic_auth_params):
    response = await client.get("/rest/ping.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_subsonic_get_license(client: AsyncClient, subsonic_auth_params):
    response = await client.get("/rest/getLicense.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "license" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_subsonic_auth_failure(client: AsyncClient):
    params = {"u": "wrong_user", "p": "wrong_pass", "c": "pytest", "v": "1.16.1", "f": "json"}
    response = await client.get("/rest/ping.view", params=params)
    assert response.status_code == 401
    data = response.json()
    # FastAPI returns {"detail": {"subsonic-response": {...}}}
    assert "detail" in data
    assert "subsonic-response" in data["detail"]
    assert data["detail"]["subsonic-response"]["status"] == "failed"
    assert data["detail"]["subsonic-response"]["error"]["code"] == 40
