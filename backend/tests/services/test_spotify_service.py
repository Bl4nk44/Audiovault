from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.spotify_service import SpotifyService


@pytest.fixture
def spotify_service():
    return SpotifyService()


@pytest.mark.asyncio
async def test_get_anonymous_token(spotify_service):
    with patch.object(spotify_service, "_ensure_token", new_callable=AsyncMock, return_value="BQA_mock_token"):
        token = await spotify_service.get_anonymous_token()
        assert token == "BQA_mock_token"


@pytest.mark.asyncio
async def test_spotify_get_track(spotify_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "t1",
        "name": "T1",
        "artists": [{"name": "A1", "id": "a1"}],
        "album": {"name": "AL1", "images": [{"url": "http://img"}]},
        "duration_ms": 100,
        "external_ids": {"isrc": "ISRC123"},
        "popularity": 80,
    }

    with (
        patch.object(spotify_service, "_ensure_token", new_callable=AsyncMock, return_value="mock_token"),
        patch.object(spotify_service, "_proxy_get", new_callable=AsyncMock, return_value=None),
        patch("httpx.AsyncClient.get", return_value=mock_response),
    ):
        track = await spotify_service.get_track("t1")

    assert track is not None
    assert track["title"] == "T1"
    assert track["source"] == "spotify"
    assert track["image_url"] == "http://img"


@pytest.mark.asyncio
async def test_spotify_get_playlist_details(spotify_service):
    mock_playlist_response = MagicMock()
    mock_playlist_response.status_code = 200
    mock_playlist_response.json.return_value = {
        "id": "pl1",
        "name": "My Playlist",
        "images": [{"url": "http://pl-img"}],
        "tracks": {
            "total": 1,
            "items": [
                {
                    "track": {
                        "id": "t1",
                        "name": "T1",
                        "artists": [{"name": "A1", "id": "a1"}],
                        "album": {"name": "AL1", "images": [{"url": "http://img"}]},
                        "duration_ms": 100,
                    }
                }
            ],
            "next": None,
        },
    }

    with (
        patch.object(spotify_service, "_ensure_token", new_callable=AsyncMock, return_value="mock_token"),
        patch.object(spotify_service, "_proxy_get", new_callable=AsyncMock, return_value=None),
        patch("app.services.spotify_service.partner_client") as mock_partner,
        patch("httpx.AsyncClient.get", return_value=mock_playlist_response),
    ):
        mock_partner.get_playlist = AsyncMock(return_value=None)
        playlist = await spotify_service.get_playlist_details("pl1")

    assert playlist is not None
    assert playlist["title"] == "My Playlist"
    assert playlist["track_count"] == 1
    assert len(playlist["tracks"]) == 1
    assert playlist["tracks"][0]["title"] == "T1"


@pytest.mark.asyncio
async def test_search_links_only(spotify_service):
    # Text search should return empty
    text_results = await spotify_service.search("some random text")
    assert text_results == []

    # Link should still function (this will call get_track or other underlying methods)
    with patch.object(SpotifyService, "get_track") as mock_get_track:
        mock_get_track.return_value = {"id": "t1", "title": "T1", "source": "spotify"}
        link_results = await spotify_service.search("https://open.spotify.com/track/t1")
        assert len(link_results) == 1
        assert link_results[0]["title"] == "T1"
