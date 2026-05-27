from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.lastfm import get_lastfm_service
from app.main import app
from app.services.lastfm_service import LastfmService


@pytest.fixture
def mock_lastfm_service():
    """Create a service instance with dummy config to avoid validation errors."""
    with patch("app.services.lastfm_service.settings") as mock_settings:
        mock_settings.LASTFM_API_KEY = "test_key"
        mock_settings.LASTFM_API_SECRET = "test_secret"
        mock_settings.CALLBACK_URL = "http://test.com"  # ensure callback url is set if needed
        service = LastfmService()
        yield service


@pytest.fixture(autouse=True)
def override_lastfm_dependency(mock_lastfm_service):
    """Override the dependency for all tests in this module."""
    app.dependency_overrides[get_lastfm_service] = lambda: mock_lastfm_service
    yield
    # Cleanup is important so other tests aren't affected
    app.dependency_overrides.pop(get_lastfm_service, None)


@pytest.mark.asyncio
async def test_connect_generates_auth_url(client, admin_token_headers):
    """Test generowania URL autoryzacji"""
    response = await client.get("/api/v1/lastfm/connect", headers=admin_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert "auth_url" in data
    assert "last.fm/api/auth" in data["auth_url"]
    assert "api_key=test_key" in data["auth_url"]


@pytest.mark.asyncio
async def test_callback_exchanges_token(client, admin_token_headers, mock_lastfm_service):
    """Test wymiany tokena na session key"""

    # Configure mock on the injected service
    # We patch the instance method on our mock object
    mock_lastfm_service.get_session = AsyncMock(return_value={"name": "testuser", "key": "session_key_123"})

    response = await client.get("/api/v1/lastfm/callback?token=test_token", headers=admin_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert data["username"] == "testuser"

    mock_lastfm_service.get_session.assert_called_once_with("test_token")


@pytest.mark.asyncio
async def test_status_endpoint(client, admin_token_headers):
    """Test endpointu statusu"""
    response = await client.get("/api/v1/lastfm/status", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    # admin_user in tests/conftest.py has no lastfm fields set initially.
    # client fixture uses db_session which rolls back after each function,
    # so status should be False initially.
    assert "connected" in data
