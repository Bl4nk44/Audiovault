import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.lastfm_service import LastfmAPIError, LastfmService


@pytest.fixture
async def lastfm_service():
    service = LastfmService()
    yield service
    await service.close()


@pytest.mark.asyncio
async def test_lastfm_sign_params(lastfm_service):
    params = {"method": "auth.getSession", "api_key": "test_key", "token": "test_token"}
    # Signature is MD5 of sorted params + secret
    with patch("app.services.lastfm_service.settings") as mock_settings:
        mock_settings.LASTFM_API_SECRET = "secret"
        sig = lastfm_service._sign_params(params)

        expected_str = "api_keytest_keymethodauth.getSessiontokentest_tokensecret"
        expected_sig = hashlib.md5(expected_str.encode("utf-8")).hexdigest()
        assert sig == expected_sig


@pytest.mark.asyncio
async def test_lastfm_rate_limit(lastfm_service):
    # Simulate rapid requests
    now = 1000.0
    # Mocking the class-level attribute via patch.object on the instance/class
    with patch.object(LastfmService, "_request_times", [now - 0.1] * 5):
        with patch("time.monotonic", return_value=now):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await lastfm_service._rate_limit()
                assert mock_sleep.called


@pytest.mark.asyncio
async def test_lastfm_request_success(lastfm_service):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"session": {"key": "sess_key"}}

    with patch.object(lastfm_service.client, "get", new_callable=AsyncMock, return_value=mock_resp):
        res = await lastfm_service._request("auth.getSession", {"token": "t"})
        assert res["session"]["key"] == "sess_key"


@pytest.mark.asyncio
async def test_lastfm_request_error(lastfm_service):
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"error": 6, "message": "Invalid parameters"}

    with patch.object(lastfm_service.client, "get", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(LastfmAPIError):
            await lastfm_service._request("any", {})


@pytest.mark.asyncio
async def test_lastfm_get_session(lastfm_service):
    with patch.object(lastfm_service, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"session": {"key": "new_key", "name": "user"}}
        sess = await lastfm_service.get_session("token")
        assert sess == {"key": "new_key", "name": "user"}


@pytest.mark.asyncio
async def test_lastfm_scrobble(lastfm_service):
    with patch.object(lastfm_service, "_post_request", new_callable=AsyncMock) as mock_post:
        await lastfm_service.scrobble("Track", "Artist", "key", 12345678, album="Album")
        mock_post.assert_called_once()
        args = mock_post.call_args[0][1]
        assert args["track"] == "Track"
        assert args["timestamp"] == 12345678


@pytest.mark.asyncio
async def test_lastfm_extract_best_image(lastfm_service):
    images = [
        {"#text": "url1", "size": "small"},
        {"#text": "url2", "size": "extralarge"},
        {"#text": "url3", "size": "medium"},
    ]
    assert lastfm_service._extract_best_image(images) == "url2"
    assert lastfm_service._extract_best_image([]) is None


@pytest.mark.asyncio
async def test_lastfm_get_recommendations_basic(lastfm_service):
    # This is a complex method, testing the higher level logic
    with patch.object(lastfm_service, "_gather_seeds", new_callable=AsyncMock) as mock_seeds:
        mock_seeds.return_value = ([("Track1", "Art1")], {"Art1"})

        with patch.object(lastfm_service, "get_similar_tracks", new_callable=AsyncMock) as mock_sim:
            # item.get("artist") in _add_to_candidates expects a certain structure
            mock_sim.return_value = [{"name": "Rec1", "artist": {"name": "Art1"}, "url": "http://url", "match": 0.9}]

            recs = await lastfm_service.get_recommendations("user_id", "sess_key")
            assert len(recs) > 0
            assert recs[0].name == "Rec1"
