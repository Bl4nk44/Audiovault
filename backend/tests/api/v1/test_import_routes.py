"""Tests for playlist import route."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_provider_manager():
    with patch("app.api.v1.import_routes.provider_manager") as mock:
        mock.extract_playlist = AsyncMock()
        yield mock


@pytest.mark.asyncio
async def test_import_playlist_success(client, mock_provider_manager):
    from app.schemas.metadata import PlaylistMetadata, TrackMetadata

    mock_provider_manager.extract_playlist.return_value = PlaylistMetadata(
        title="My Playlist",
        tracks=[
            TrackMetadata(title="T1", artist="A1"),
            TrackMetadata(title="T2", artist="A2"),
        ],
    )

    response = await client.post(
        "/api/v1/import/playlist",
        json={"url": "https://open.spotify.com/playlist/abc123"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_import_playlist_not_found(client, mock_provider_manager):
    mock_provider_manager.extract_playlist.return_value = None

    response = await client.post(
        "/api/v1/import/playlist",
        json={"url": "https://open.spotify.com/playlist/empty"},
    )
    assert response.status_code == 404
    assert "no data" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_import_playlist_server_error(client, mock_provider_manager):
    mock_provider_manager.extract_playlist.side_effect = RuntimeError("Provider crashed")

    response = await client.post(
        "/api/v1/import/playlist",
        json={"url": "https://open.spotify.com/playlist/crash"},
    )
    assert response.status_code == 500
    assert "Provider crashed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_import_playlist_invalid_domain(client):
    response = await client.post(
        "/api/v1/import/playlist",
        json={"url": "https://evil.com/playlist/abc"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_import_playlist_invalid_scheme(client):
    response = await client.post(
        "/api/v1/import/playlist",
        json={"url": "ftp://open.spotify.com/playlist/abc"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_import_playlist_tidal_url(client, mock_provider_manager):
    from app.schemas.metadata import PlaylistMetadata

    mock_provider_manager.extract_playlist.return_value = PlaylistMetadata(title="Tidal PL", tracks=[])
    response = await client.post(
        "/api/v1/import/playlist",
        json={"url": "https://listen.tidal.com/playlist/xyz"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_import_playlist_soundcloud_url(client, mock_provider_manager):
    from app.schemas.metadata import PlaylistMetadata

    mock_provider_manager.extract_playlist.return_value = PlaylistMetadata(title="SC Set", tracks=[])
    response = await client.post(
        "/api/v1/import/playlist",
        json={"url": "https://soundcloud.com/artist/sets/my-set"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_import_playlist_youtube_url(client, mock_provider_manager):
    from app.schemas.metadata import PlaylistMetadata

    mock_provider_manager.extract_playlist.return_value = PlaylistMetadata(title="YT List", tracks=[])
    response = await client.post(
        "/api/v1/import/playlist",
        json={"url": "https://www.youtube.com/playlist?list=PLabc"},
    )
    assert response.status_code == 200
