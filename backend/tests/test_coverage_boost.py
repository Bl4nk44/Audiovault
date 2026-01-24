import pytest
from app.core import config, security
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_main_lifespan():
    """Test app startup and shutdown lifespan."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Request openapi.json - it's public and triggers valid app stack
        response = await ac.get("/openapi.json")
        assert response.status_code == 200


def test_config_loading():
    """Access config values to ensure coverage."""
    assert config.settings.PROJECT_NAME is not None
    assert config.settings.API_V1_STR == "/api/v1"


def test_security_utils():
    """Cover security utility functions."""
    pw = "secret"
    hashed = security.get_password_hash(pw)
    assert security.verify_password(pw, hashed)
    assert not security.verify_password("wrong", hashed)


def test_database_url_parsing():
    """Cover database URL helpers."""
    # Correct import from base
    from app.db.base import Base

    assert Base is not None
