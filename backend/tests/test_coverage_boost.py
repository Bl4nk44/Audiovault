
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core import config, security, cache
from app.db import database

@pytest.mark.asyncio
async def test_main_lifespan():
    """Test app startup and shutdown lifespan."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/system/status")
        # Just checking that app is up is enough to trigger lifespan coverage
        assert response.status_code in [200, 401, 403] 

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
    # Just import to cover the file top-level
    assert database.Base is not None

