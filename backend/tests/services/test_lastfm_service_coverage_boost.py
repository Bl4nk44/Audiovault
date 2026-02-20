"""
Coverage boost for LastfmService.
Targets: user info, similar tracks/artists, and recommendation fallbacks.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.lastfm_service import LastfmService, LastfmAPIError

@pytest.fixture
async def service():
    srv = LastfmService()
    yield srv
    await srv.close()

@pytest.mark.asyncio
async def test_lastfm_get_user_info_success(service):
    mock_data = {
        "user": {
            "name": "testuser",
            "playcount": "100",
            "image": [{"#text": "img_url", "size": "extralarge"}]
        }
    }
    with patch.object(service, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_data
        res = await service.get_user_info("testuser")
        assert res["name"] == "testuser"
        assert res["playcount"] == 100
        assert res["image_url"] == "img_url"

@pytest.mark.asyncio
async def test_lastfm_get_similar_tracks_error(service):
    # Test that it returns empty list on API error
    with patch.object(service, "_request", side_effect=LastfmAPIError("Fail")):
        res = await service.get_similar_tracks("Artist", "Track")
        assert res == []

@pytest.mark.asyncio
async def test_lastfm_get_recommended_artists_fallback(service):
    """Test that it falls back to Top Artists if recommendations fail or are empty."""
    with patch.object(service, "_request", new_callable=AsyncMock) as mock_req:
        # First call (recommendations) returns empty
        # Second call (top artists) returns data
        mock_req.side_effect = [
            {"recommendations": {"artist": []}},
            {"topartists": {"artist": [{"name": "Queen", "url": "url"}]}}
        ]
        
        res = await service.get_recommended_artists(session_key="sk", user_name="user")
        assert len(res) == 1
        assert res[0].name == "Queen"
        assert mock_req.call_count == 2

@pytest.mark.asyncio
async def test_lastfm_scrobble_success(service):
    with patch.object(service, "_post_request", new_callable=AsyncMock) as mock_post:
        await service.scrobble("Track", "Artist", "sk", 123456789)
        assert mock_post.called
        args = mock_post.call_args[0][1]
        assert args["track"] == "Track"
        assert args["sk"] == "sk"

@pytest.mark.asyncio
async def test_lastfm_get_user_friends_dict_response(service):
    """Test get_user_friends when API returns a single dict instead of a list."""
    mock_data = {
        "friends": {
            "user": {"name": "friend1", "url": "url1"}
        }
    }
    with patch.object(service, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_data
        res = await service.get_user_friends("user")
        assert len(res) == 1
        assert res[0]["name"] == "friend1"
