from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.lyrics_service import LyricsService


@pytest.fixture
def lyrics_service():
    return LyricsService()


@pytest.mark.asyncio
async def test_get_lyrics_cache_hit(lyrics_service):
    with (
        patch("app.services.lyrics_service.cache_manager.redis", True),
        patch("app.services.lyrics_service.cache_manager.get", new_callable=AsyncMock) as mock_get,
    ):
        mock_get.return_value = {"found": True, "lyrics": "Test Lyrics"}
        res = await lyrics_service.get_lyrics("Artist", "Title")
        assert res["lyrics"] == "Test Lyrics"
        assert mock_get.called


@pytest.mark.asyncio
async def test_get_lyrics_cache_miss_genius_hit(lyrics_service):
    with (
        patch("app.services.lyrics_service.cache_manager.redis", True),
        patch("app.services.lyrics_service.cache_manager.get", new_callable=AsyncMock, return_value=None),
        patch("app.services.lyrics_service.LyricsService._get_genius_client") as mock_client,
    ):
        mock_genius = MagicMock()
        mock_song = MagicMock()
        mock_song.lyrics = "Genius Lyrics"
        mock_song.title = "Title"
        mock_song.artist = "Artist"
        mock_song.url = "http://genius.com"
        mock_genius.search_song.return_value = mock_song
        mock_client.return_value = mock_genius

        with patch("app.services.lyrics_service.cache_manager.set", new_callable=AsyncMock) as mock_set:
            res = await lyrics_service.get_lyrics("Artist", "Title")
            assert res["lyrics"] == "Genius Lyrics"
            assert mock_set.called


@pytest.mark.asyncio
async def test_get_lyrics_not_found(lyrics_service):
    with (
        patch("app.services.lyrics_service.cache_manager.redis", True),
        patch("app.services.lyrics_service.cache_manager.get", new_callable=AsyncMock, return_value=None),
        patch("app.services.lyrics_service.LyricsService._get_genius_client") as mock_client,
    ):
        mock_genius = MagicMock()
        mock_genius.search_song.return_value = None
        mock_client.return_value = mock_genius

        with patch("app.services.lyrics_service.cache_manager.set", new_callable=AsyncMock) as mock_set:
            res = await lyrics_service.get_lyrics("Artist", "Title")
            assert res["found"] is False
            assert mock_set.called


@pytest.mark.asyncio
async def test_get_lyrics_no_client(lyrics_service):
    with patch("app.services.lyrics_service.LyricsService._get_genius_client", return_value=None):
        res = await lyrics_service.get_lyrics("Artist", "Title")
        assert res is None


@pytest.mark.asyncio
async def test_clear_cache(lyrics_service):
    with patch("app.services.lyrics_service.cache_manager.redis") as mock_redis:
        mock_redis.delete = AsyncMock(return_value=1)
        res = await lyrics_service.clear_cache("Artist", "Title")
        assert res is True
        assert mock_redis.delete.called
