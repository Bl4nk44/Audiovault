from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from app.config.lastfm_config import LastfmConfig
from app.services.lastfm_service import LastfmAPIError, LastfmRateLimitError, LastfmService


@pytest.fixture
def lastfm_config():
    return LastfmConfig(API_KEY="test", API_SECRET="test", CALLBACK_URL="http://test")


@pytest.fixture
def lastfm_service(lastfm_config):
    service = LastfmService(lastfm_config)
    # Mock the client instance directly
    service.client = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_get_user_top_artists(lastfm_service):
    # Setup mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "topartists": {"artist": [{"name": "Radiohead", "playcount": "100"}, {"name": "Coldplay", "playcount": "80"}]}
    }
    mock_response.raise_for_status = Mock()

    # Configure client.get to return this response
    lastfm_service.client.get.return_value = mock_response

    artists = await lastfm_service.get_user_top_artists("testuser")

    assert len(artists) == 2
    assert artists[0]["name"] == "Radiohead"

    # Verify call
    lastfm_service.client.get.assert_called_once()
    kwargs = lastfm_service.client.get.call_args[1]
    assert kwargs["params"]["method"] == "user.getTopArtists"
    assert kwargs["params"]["user"] == "testuser"


@pytest.mark.asyncio
async def test_get_user_top_tracks(lastfm_service):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"toptracks": {"track": [{"name": "Song1", "artist": {"name": "Artist1"}}]}}
    mock_response.raise_for_status = Mock()
    lastfm_service.client.get.return_value = mock_response

    tracks = await lastfm_service.get_user_top_tracks("testuser")
    assert len(tracks) == 1
    assert tracks[0]["name"] == "Song1"


@pytest.mark.asyncio
async def test_get_similar_tracks(lastfm_service):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"similartracks": {"track": [{"name": "Similar1", "match": "0.9"}]}}
    mock_response.raise_for_status = Mock()
    lastfm_service.client.get.return_value = mock_response

    similar = await lastfm_service.get_similar_tracks("Artist", "Song")
    assert len(similar) == 1
    assert similar[0]["match"] == "0.9"


@pytest.mark.asyncio
async def test_get_similar_artists(lastfm_service):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"similarartists": {"artist": [{"name": "Similar Artist", "match": "0.85"}]}}
    mock_response.raise_for_status = Mock()
    lastfm_service.client.get.return_value = mock_response

    similar = await lastfm_service.get_similar_artists("Radiohead")
    assert len(similar) == 1


@pytest.mark.asyncio
async def test_api_error_handling(lastfm_service):
    # Simulate HTTP error
    lastfm_service.client.get.side_effect = httpx.HTTPError("API Error")

    with pytest.raises(LastfmAPIError):
        await lastfm_service.get_user_top_artists("testuser")


@pytest.mark.asyncio
async def test_rate_limiting_handling(lastfm_service):
    mock_response = Mock()
    mock_response.status_code = 429
    lastfm_service.client.get.return_value = mock_response

    with pytest.raises(LastfmRateLimitError):
        await lastfm_service.get_user_top_artists("testuser")


@pytest.mark.asyncio
async def test_get_recommendations_integration_logic(lastfm_service):
    # Mock calls logic
    async def side_effect(*args, **kwargs):
        params = kwargs.get("params", {})
        method = params.get("method")

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = Mock()

        if method == "user.getTopArtists":
            mock_resp.json.return_value = {"topartists": {"artist": [{"name": "Artist1"}]}}
        elif method == "user.getTopTracks":
            mock_resp.json.return_value = {
                "toptracks": {"track": [{"name": "Track1", "artist": {"name": "Artist1"}, "playcount": "100"}]}
            }
        elif method == "track.getSimilar":
            mock_resp.json.return_value = {
                "similartracks": {
                    "track": [
                        {
                            "name": "Rec1",
                            "artist": {"name": "RecArtist1"},
                            "match": "0.9",
                            "url": "http://last.fm/rec1",
                            "image": [{"#text": "img.jpg", "size": "large"}],
                        }
                    ]
                }
            }
        else:
            mock_resp.json.return_value = {}

        return mock_resp

    lastfm_service.client.get.side_effect = side_effect

    recs = await lastfm_service.get_recommendations("testuser")

    assert len(recs) >= 1
    assert recs[0].name == "Rec1"
    assert recs[0].score > 0
