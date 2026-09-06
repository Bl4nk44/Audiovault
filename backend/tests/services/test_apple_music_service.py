from unittest.mock import AsyncMock, patch

import pytest

from app.services.apple_music_service import AppleMusicService


@pytest.fixture
def service():
    return AppleMusicService()


def test_can_handle_full_url(service):
    assert service.can_handle("https://music.apple.com/us/album/123") is True


def test_can_handle_short_url(service):
    assert service.can_handle("https://apple.co/3xyz") is True


def test_can_handle_other_url(service):
    assert service.can_handle("https://spotify.com/track/abc") is False


@pytest.mark.asyncio
async def test_resolve_url_non_short_link_unchanged(service):
    url = "https://music.apple.com/us/album/abc"
    result = await service._resolve_url(url)
    assert result == url


@pytest.mark.asyncio
async def test_resolve_url_short_link_resolved(service):
    with patch("app.utils.url_helper.resolve_redirects", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = "https://music.apple.com/us/album/abc"
        result = await service._resolve_url("https://apple.co/3xyz")
    mock_resolve.assert_called_once_with("https://apple.co/3xyz")
    assert result == "https://music.apple.com/us/album/abc"


@pytest.mark.asyncio
async def test_get_tracks_resolves_short_link_then_delegates(service):
    resolved = "https://music.apple.com/us/playlist/my-list"
    mock_tracks = [{"id": "t1", "title": "Track", "artist": "Artist", "source": "apple_music"}]
    with (
        patch.object(service, "_resolve_url", new_callable=AsyncMock, return_value=resolved),
        patch(
            "app.services.base_music_service.BaseMusicService.get_tracks",
            new_callable=AsyncMock,
            return_value=mock_tracks,
        ),
    ):
        tracks = await service.get_tracks("https://apple.co/3xyz")

    assert tracks == mock_tracks


@pytest.mark.asyncio
async def test_get_tracks_full_url_skips_redirect(service):
    url = "https://music.apple.com/us/album/abc"
    mock_tracks = [{"id": "t1", "title": "T", "artist": "A", "source": "apple_music"}]
    with patch(
        "app.services.base_music_service.BaseMusicService.get_tracks",
        new_callable=AsyncMock,
        return_value=mock_tracks,
    ):
        tracks = await service.get_tracks(url)
    assert tracks == mock_tracks


@pytest.mark.asyncio
async def test_get_playlist_info_resolves_short_link(service):
    resolved = "https://music.apple.com/us/playlist/my-list"
    mock_info = {"id": resolved, "title": "My Playlist", "source": "apple_music"}
    with (
        patch.object(service, "_resolve_url", new_callable=AsyncMock, return_value=resolved),
        patch(
            "app.services.base_music_service.BaseMusicService.get_playlist_info",
            new_callable=AsyncMock,
            return_value=mock_info,
        ),
    ):
        result = await service.get_playlist_info("https://apple.co/3xyz")

    assert result == mock_info


@pytest.mark.asyncio
async def test_get_playlist_info_full_url(service):
    url = "https://music.apple.com/us/playlist/my-list"
    mock_info = {"id": url, "title": "PL", "source": "apple_music"}
    with patch(
        "app.services.base_music_service.BaseMusicService.get_playlist_info",
        new_callable=AsyncMock,
        return_value=mock_info,
    ):
        result = await service.get_playlist_info(url)
    assert result == mock_info


# --- Keyword search via iTunes Search API ---


def _itunes_cm(status, payload):
    from unittest.mock import AsyncMock, MagicMock

    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=payload)
    return MagicMock(__aenter__=AsyncMock(return_value=resp), __aexit__=AsyncMock(return_value=False))


@pytest.mark.asyncio
async def test_search_maps_itunes_results(service):
    payload = {
        "resultCount": 1,
        "results": [
            {
                "trackId": 111,
                "trackName": "Blinding Lights",
                "artistName": "The Weeknd",
                "collectionName": "After Hours",
                "trackTimeMillis": 200040,
                "artworkUrl100": "https://is1.mzstatic.com/image/100x100bb.jpg",
            }
        ],
    }
    with patch("aiohttp.ClientSession.get", return_value=_itunes_cm(200, payload)):
        results = await service.search("blinding lights", limit=5)

    assert len(results) == 1
    r = results[0]
    assert r["id"] == "111"
    assert r["title"] == "Blinding Lights"
    assert r["artist"] == "The Weeknd"
    assert r["source"] == "apple_music"
    assert r["type"] == "track"
    assert r["image_url"] == "https://is1.mzstatic.com/image/600x600bb.jpg"


@pytest.mark.asyncio
async def test_search_skips_entries_without_track_id(service):
    payload = {"results": [{"trackName": "No Id"}, {"trackId": 5, "trackName": "Ok", "artistName": "A"}]}
    with patch("aiohttp.ClientSession.get", return_value=_itunes_cm(200, payload)):
        results = await service.search("q")
    assert [r["id"] for r in results] == ["5"]


@pytest.mark.asyncio
async def test_search_non_200_returns_empty(service):
    with patch("aiohttp.ClientSession.get", return_value=_itunes_cm(503, {})):
        assert await service.search("q") == []


@pytest.mark.asyncio
async def test_search_exception_returns_empty(service):
    with patch("aiohttp.ClientSession.get", side_effect=RuntimeError("network down")):
        assert await service.search("q") == []


@pytest.mark.asyncio
async def test_search_sends_song_entity_params(service):
    captured = {}

    def _capture(url, params=None):
        captured["url"] = url
        captured["params"] = params
        return _itunes_cm(200, {"results": []})

    with patch("aiohttp.ClientSession.get", side_effect=_capture):
        await service.search("daft punk", limit=999)

    assert captured["url"] == service.ITUNES_SEARCH_URL
    assert captured["params"]["term"] == "daft punk"
    assert captured["params"]["entity"] == "song"
    assert captured["params"]["limit"] == 200
