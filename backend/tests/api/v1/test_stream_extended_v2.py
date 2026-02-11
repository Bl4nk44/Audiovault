import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_track_cover_local_file(client: AsyncClient, admin_token_headers, db_session):
    track_id = str(uuid.uuid4())

    with patch("app.api.v1.stream._resolve_track_path", new_callable=AsyncMock) as mock_resolve:
        mock_track = MagicMock()
        mock_resolve.return_value = (mock_track, "C:\\fake\\track.mp3")

        with patch("app.api.v1.stream._resolve_local_cover_file", new_callable=AsyncMock) as mock_local:
            mock_local.return_value = (b"fake_image_data", "image/jpeg")

            response = await client.get(f"/api/v1/stream/{track_id}/cover", headers=admin_token_headers)

            assert response.status_code == 200
            assert response.content == b"fake_image_data"
            assert response.headers["content-type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_get_track_cover_embedded(client: AsyncClient, admin_token_headers, db_session):
    track_id = str(uuid.uuid4())

    with patch("app.api.v1.stream._resolve_track_path", new_callable=AsyncMock) as mock_resolve:
        mock_track = MagicMock()
        mock_resolve.return_value = (mock_track, "C:\\fake\\track.mp3")

        with patch("app.api.v1.stream._resolve_local_cover_file", new_callable=AsyncMock) as mock_local:
            mock_local.return_value = (None, None)

            with patch("app.api.v1.stream._extract_embedded_cover_art", new_callable=AsyncMock) as mock_emb:
                mock_emb.return_value = (b"embedded_data", "image/png")

                response = await client.get(f"/api/v1/stream/{track_id}/cover", headers=admin_token_headers)

                assert response.status_code == 200
                assert response.content == b"embedded_data"
                assert response.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_stream_track_success(client: AsyncClient, admin_token_headers):
    track_id = "spotify_track_id"

    with patch("app.api.v1.stream._resolve_stream_url", new_callable=AsyncMock) as mock_res_url:
        mock_res_url.return_value = "https://youtube.com/watch?v=123"

        with patch("app.api.v1.stream._extract_direct_url", new_callable=AsyncMock) as mock_ext:
            mock_ext.return_value = ("https://googlevideo.com/stream", {"User-Agent": "test"})

            # Mock httpx.AsyncClient to avoid real HTTP request
            mock_upstream_response = MagicMock()
            mock_upstream_response.status_code = 200
            mock_upstream_response.content = b"fake_audio_data"
            mock_upstream_response.headers = {"content-length": "14"}

            mock_http_client = AsyncMock()
            mock_http_client.get.return_value = mock_upstream_response
            mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_http_client.__aexit__ = AsyncMock(return_value=False)

            with patch("app.api.v1.stream.httpx.AsyncClient", return_value=mock_http_client):
                response = await client.get(
                    f"/api/v1/stream/{track_id}.mp3",
                    headers=admin_token_headers,
                    follow_redirects=False,
                )

                assert response.status_code == 200
                assert response.headers["content-type"] == "audio/mpeg"


@pytest.mark.asyncio
async def test_get_track_cover_not_found(client: AsyncClient, admin_token_headers, db_session):
    track_id = str(uuid.uuid4())
    with patch("app.api.v1.stream._resolve_track_path", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = (None, None)
        response = await client.get(f"/api/v1/stream/{track_id}/cover", headers=admin_token_headers)
        assert response.status_code == 404
