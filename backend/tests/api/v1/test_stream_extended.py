"""Extended tests for stream.py API."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.api.v1 import stream
from httpx import AsyncClient


class TestStreamTrack:
    @pytest.mark.asyncio
    async def test_stream_track_not_found(self, client: AsyncClient):
        """Test streaming non-existent track."""
        response = await client.get(f"/api/v1/stream/{uuid4()}")
        assert response.status_code == 404


class TestTrackCover:
    @pytest.mark.asyncio
    async def test_cover_track_not_found(self, client: AsyncClient):
        """Test getting cover for non-existent track."""
        response = await client.get(f"/api/v1/stream/{uuid4()}/cover")
        assert response.status_code == 404


class TestResolveStreamUrl:
    def test_resolve_stream_url_sync_no_match(self):
        """Test sync URL resolution when no match found."""
        with patch("app.api.v1.stream.YouTubeService") as mock_yt:
            mock_service = MagicMock()
            mock_service.search.return_value = []
            mock_yt.return_value = mock_service

            result = stream._resolve_stream_url_sync({"title": "NonExistent", "artist": "Nobody"})
            assert result is None


class TestExtractArtSync:
    def test_extract_art_sync_flac(self):
        """Test sync art extraction for FLAC file."""
        with patch("mutagen.File", return_value=None):
            result = stream._extract_art_sync("/nonexistent/file.flac")
            assert result == (None, None)

    def test_extract_art_sync_mp3(self):
        """Test sync art extraction for MP3 file."""
        with patch("mutagen.File", return_value=None):
            result = stream._extract_art_sync("/nonexistent/file.mp3")
            assert result == (None, None)


class TestResolveLocalCover:
    @pytest.mark.asyncio
    async def test_resolve_local_cover_exists(self):
        """Test finding local cover file."""
        with patch("os.path.exists", return_value=True), patch("aiofiles.open", new_callable=MagicMock) as mock_open:
            mock_file = AsyncMock()
            mock_file.__aenter__.return_value = mock_file
            mock_file.read.return_value = b"fake_jpg_data"
            mock_open.return_value = mock_file

            result = await stream._resolve_local_cover_file("/fake/path")
            assert result is not None
            data, mime = result
            assert data == b"fake_jpg_data"
            assert mime == "image/jpeg"

    @pytest.mark.asyncio
    async def test_resolve_local_cover_not_found(self):
        """Test when no local cover file exists."""
        with patch("os.path.exists", return_value=False):
            result = await stream._resolve_local_cover_file("/fake/path")
            assert result == (None, None)
