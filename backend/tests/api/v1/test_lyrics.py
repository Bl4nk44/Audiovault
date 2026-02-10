import uuid
from unittest.mock import AsyncMock, patch

import pytest
from app.core.dependencies import get_current_active_user
from app.main import app
from app.models.user import User
from httpx import AsyncClient


@pytest.fixture
def mock_user():
    return User(id=uuid.uuid4(), username="testuser", is_active=True)


@pytest.mark.asyncio
async def test_get_lyrics_success(client: AsyncClient, mock_user):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user

    mock_lyrics = {
        "found": True,
        "lyrics": "La la la",
        "title": "Song",
        "artist": "Artist",
        "url": "http://genius.com/song",
    }

    with patch("app.services.lyrics_service.lyrics_service.get_lyrics", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_lyrics

        response = await client.get("/api/v1/lyrics/search?artist=Artist&title=Song")

        assert response.status_code == 200
        assert response.json()["found"] is True
        assert response.json()["lyrics"] == "La la la"

        # Check call args (artist, title, use_cache=True)
        # Note: it's called as positional args or kwargs depending on how Service is called
        # Our API calls it with keyword use_cache=use_cache
        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        assert kwargs["use_cache"] is True


@pytest.mark.asyncio
async def test_get_lyrics_not_found(client: AsyncClient, mock_user):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user

    with patch("app.services.lyrics_service.lyrics_service.get_lyrics", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"found": False, "lyrics": None}

        response = await client.get("/api/v1/lyrics/search?artist=Unknown&title=Song")

        assert response.status_code == 200
        assert response.json()["found"] is False
