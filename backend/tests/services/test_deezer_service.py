from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.deezer_service import DeezerService


@pytest.fixture
def deezer_service():
    return DeezerService()


@pytest.mark.asyncio
async def test_deezer_search_basic(deezer_service):
    mock_response_data = {
        "data": [
            {
                "id": 123,
                "title": "Song Title",
                "artist": {"name": "Artist Name"},
                "album": {"title": "Album Title", "cover_medium": "http://img.url"},
                "duration": 180,
                "rank": 1000,
                "isrc": "ISRC123",
            }
        ]
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)

        mock_get.return_value.__aenter__.return_value = mock_response

        results = await deezer_service.search("test query")

        assert len(results) == 1
        assert results[0]["title"] == "Song Title"
        assert results[0]["artist"] == "Artist Name"
        assert results[0]["duration_ms"] == 180000


@pytest.mark.asyncio
async def test_deezer_search_track_url(deezer_service):
    mock_track_data = {
        "id": 123,
        "title": "Song Title",
        "artist": {"name": "Artist Name"},
        "album": {"title": "Album Title", "cover_medium": "http://img.url"},
        "duration": 180,
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_track_data)
        mock_get.return_value.__aenter__.return_value = mock_response

        results = await deezer_service.search("https://www.deezer.com/track/123")

        assert len(results) == 1
        assert results[0]["id"] == "123"


@pytest.mark.asyncio
async def test_deezer_get_playlist_details(deezer_service):
    mock_pl_data = {
        "id": 456,
        "title": "My Playlist",
        "description": "Desc",
        "picture_medium": "http://pl.img",
        "creator": {"name": "Author"},
        "tracks": {
            "data": [
                {"id": 123, "title": "Song", "artist": {"name": "Artist"}, "album": {"title": "Album"}, "duration": 100}
            ]
        },
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_pl_data)
        mock_get.return_value.__aenter__.return_value = mock_response

        details = await deezer_service.get_playlist_details("456")

        assert details["title"] == "My Playlist"
        assert len(details["tracks"]) == 1


@pytest.mark.asyncio
async def test_deezer_get_artist_details(deezer_service):
    mock_responses = [
        {"id": 789, "name": "Mega Artist", "picture_medium": "http://art.img"},  # artist
        {
            "data": [
                {"id": 1, "title": "Top 1", "artist": {"name": "Mega Artist"}, "album": {"title": "A"}, "duration": 60}
            ]
        },  # top tracks
        {
            "data": [{"id": 10, "title": "Album 1", "cover_medium": "http://cov.img", "release_date": "2024-01-01"}]
        },  # albums
    ]

    with patch("aiohttp.ClientSession.get") as mock_get:
        # Create separate mock responses for each call
        m1 = MagicMock()
        m1.status = 200
        m1.json = AsyncMock(return_value=mock_responses[0])

        m2 = MagicMock()
        m2.status = 200
        m2.json = AsyncMock(return_value=mock_responses[1])

        m3 = MagicMock()
        m3.status = 200
        m3.json = AsyncMock(return_value=mock_responses[2])

        # mock_get.return_value is a CM. Its __aenter__.return_value is what 'async with' gets.
        # We need each call to 'get' to return a NEW MagicMock that behaves as a CM.
        mock_get.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=m1)),
            MagicMock(__aenter__=AsyncMock(return_value=m2)),
            MagicMock(__aenter__=AsyncMock(return_value=m3)),
        ]

        details = await deezer_service.get_artist_details("789")

        assert details["name"] == "Mega Artist"
        assert len(details["top_tracks"]) == 1
        assert len(details["albums"]) == 1
