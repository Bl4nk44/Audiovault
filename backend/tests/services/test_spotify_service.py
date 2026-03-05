import pytest
import httpx
from unittest.mock import patch, MagicMock
from app.services.spotify_service import SpotifyService

@pytest.fixture
def spotify_service():
    return SpotifyService()

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_get_anonymous_token(mock_get, spotify_service):
    # Mocking the HTML response containing the token
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"clientId":"client_123","accessToken":"BQA_mock_token","isAnonymous":True}
    mock_get.return_value = mock_response

    token = await spotify_service.get_anonymous_token()
    assert token == "BQA_mock_token"
    mock_get.assert_called_once()

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
@patch.object(SpotifyService, "get_anonymous_token")
async def test_spotify_get_track(mock_token, mock_get, spotify_service):
    mock_token.return_value = "mock_token"
    
    # Mocking track API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "t1",
        "name": "T1",
        "artists": [{"name": "A1", "id": "a1"}],
        "album": {"name": "AL1", "images": [{"url": "http://img"}]},
        "duration_ms": 100,
        "external_ids": {"isrc": "ISRC123"},
        "popularity": 80
    }
    mock_get.return_value = mock_response

    track = await spotify_service.get_track("t1")
    
    assert track is not None
    assert track["title"] == "T1"
    assert track["source"] == "spotify"
    assert track["image_url"] == "http://img"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
@patch.object(SpotifyService, "get_anonymous_token")
async def test_spotify_get_playlist_details(mock_token, mock_get, spotify_service):
    mock_token.return_value = "mock_token"
    
    # Needs two API calls typically: one for playlist, one for tracks
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
                        "duration_ms": 100
                    }
                }
            ],
            "next": None
        }
    }
    
    mock_get.return_value = mock_playlist_response
    
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
