"""Tests for spotify_partner.py — module-level helpers and SpotifyPartnerClient."""

import base64
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.spotify_partner import (
    SpotifyPartnerClient,
    _browser_headers,
    _derive_totp_secret,
    _jitter,
    _totp,
    _ua,
)

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def test_ua_returns_string():
    result = _ua()
    assert isinstance(result, str)
    assert "Mozilla" in result


def test_browser_headers_keys():
    headers = _browser_headers("Mozilla/5.0 Test")
    assert "User-Agent" in headers
    assert "Origin" in headers
    assert "Referer" in headers
    assert "Accept" in headers
    assert headers["User-Agent"] == "Mozilla/5.0 Test"


def test_browser_headers_custom_origin():
    headers = _browser_headers("UA", origin="https://example.com")
    assert headers["Origin"] == "https://example.com"
    assert headers["Referer"] == "https://example.com/"


def test_totp_returns_six_digits():
    secret = base64.b32encode(b"testsecretkey123").decode().rstrip("=")
    code = _totp(secret)
    assert len(code) == 6
    assert code.isdigit()


def test_derive_totp_secret_returns_string():
    raw = bytearray([1, 2, 3, 4, 5, 6, 7, 8])
    result = _derive_totp_secret(raw)
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_jitter_completes():
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await _jitter()
    mock_sleep.assert_called_once()
    delay = mock_sleep.call_args[0][0]
    assert 0.15 <= delay <= 0.6


# ---------------------------------------------------------------------------
# SpotifyPartnerClient init
# ---------------------------------------------------------------------------


def test_client_init():
    client = SpotifyPartnerClient()
    assert client._access_token == ""
    assert client._client_token == ""
    assert isinstance(client._graphql_hashes, dict)
    assert "fetchPlaylist" in client._graphql_hashes


# ---------------------------------------------------------------------------
# _refresh_totp_secret
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_totp_secret():
    client = SpotifyPartnerClient()
    secrets_data = {"1": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = secrets_data

    mock_http = MagicMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_http):
        await client._refresh_totp_secret()

    assert client._totp_secret != ""
    assert client._totp_version == "1"
    assert client._totp_secret_expires > time.time()


# ---------------------------------------------------------------------------
# _refresh_access_token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_access_token():
    client = SpotifyPartnerClient()
    client._totp_secret = base64.b32encode(b"testsecret12345").decode().rstrip("=")
    client._totp_secret_expires = time.time() + 3600
    client._totp_version = "1"

    token_data = {
        "accessToken": "test_access_token",
        "clientId": "test_client_id",
        "accessTokenExpirationTimestampMs": (time.time() + 3600) * 1000,
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = token_data

    mock_http = MagicMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_http):
        await client._refresh_access_token()

    assert client._access_token == "test_access_token"
    assert client._client_id == "test_client_id"


@pytest.mark.asyncio
async def test_refresh_access_token_calls_totp_refresh_when_stale():
    client = SpotifyPartnerClient()
    client._totp_secret = ""  # stale

    with patch.object(client, "_refresh_totp_secret", new_callable=AsyncMock) as mock_totp:
        mock_totp.side_effect = Exception("TOTP refresh called")
        with pytest.raises(Exception, match="TOTP refresh called"):
            await client._refresh_access_token()

    mock_totp.assert_called_once()


# ---------------------------------------------------------------------------
# _refresh_client_token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_client_token():
    import secrets as _secrets

    client = SpotifyPartnerClient()
    client._client_id = "test_id"

    expected = _secrets.token_urlsafe(16)
    token_data = {"granted_token": {"token": expected}}

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = token_data

    mock_http = MagicMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_http):
        await client._refresh_client_token()

    assert client._client_token == expected
    assert client._client_token_expires > time.time()


# ---------------------------------------------------------------------------
# _ensure_auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_auth_refreshes_when_expired():
    client = SpotifyPartnerClient()
    client._access_token = ""
    client._client_token = ""

    with (
        patch.object(client, "_refresh_access_token", new_callable=AsyncMock) as mock_at,
        patch.object(client, "_refresh_client_token", new_callable=AsyncMock) as mock_ct,
    ):
        await client._ensure_auth()

    mock_at.assert_called_once()
    mock_ct.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_auth_skips_when_valid():
    client = SpotifyPartnerClient()
    client._access_token = "valid_token"
    client._access_token_expires = time.time() + 3600
    client._client_token = "valid_client_token"
    client._client_token_expires = time.time() + 3600

    with (
        patch.object(client, "_refresh_access_token", new_callable=AsyncMock) as mock_at,
        patch.object(client, "_refresh_client_token", new_callable=AsyncMock) as mock_ct,
    ):
        await client._ensure_auth()

    mock_at.assert_not_called()
    mock_ct.assert_not_called()


# ---------------------------------------------------------------------------
# _get_hash / _find_hash_in_js
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_hash_known_operation():
    client = SpotifyPartnerClient()
    h = await client._get_hash("fetchPlaylist")
    assert len(h) == 64  # known hash present in _KNOWN_HASHES


@pytest.mark.asyncio
async def test_get_hash_unknown_operation():
    client = SpotifyPartnerClient()
    with patch.object(client, "_find_hash_in_js", new_callable=AsyncMock, return_value="abc123") as mock_find:
        result = await client._get_hash("unknownOperation")
    mock_find.assert_called_once_with("unknownOperation")
    assert result == "abc123"


@pytest.mark.asyncio
async def test_find_hash_in_js_returns_empty_on_failure():
    client = SpotifyPartnerClient()

    mock_resp = MagicMock()
    mock_resp.text = "<html>no js urls here</html>"

    mock_http = MagicMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_http):
        result = await client._find_hash_in_js("fetchPlaylist")

    assert result == ""


# ---------------------------------------------------------------------------
# _query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_success():
    client = SpotifyPartnerClient()
    client._access_token = "tok"
    client._access_token_expires = time.time() + 3600
    client._client_token = "ctok"
    client._client_token_expires = time.time() + 3600

    expected: dict = {"data": {"playlistV2": {}}}

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = expected

    mock_http = MagicMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_http):
        result = await client._query("fetchPlaylist", {"uri": "spotify:playlist:abc"})

    assert result == expected


@pytest.mark.asyncio
async def test_query_returns_none_when_no_hash():
    client = SpotifyPartnerClient()
    client._graphql_hashes = {}
    client._access_token = "tok"
    client._access_token_expires = time.time() + 3600
    client._client_token = "ctok"
    client._client_token_expires = time.time() + 3600

    with patch.object(client, "_find_hash_in_js", new_callable=AsyncMock, return_value=""):
        result = await client._query("unknownOp", {})

    assert result is None


@pytest.mark.asyncio
async def test_query_401_clears_token():
    client = SpotifyPartnerClient()
    client._access_token = "expired_tok"
    client._access_token_expires = time.time() + 3600
    client._client_token = "ctok"
    client._client_token_expires = time.time() + 3600

    mock_resp = MagicMock()
    mock_resp.status_code = 401

    mock_http = MagicMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_http):
        result = await client._query("fetchPlaylist", {})

    assert result is None
    assert client._access_token == ""
    assert client._access_token_expires == 0


@pytest.mark.asyncio
async def test_query_request_exception_returns_none():
    client = SpotifyPartnerClient()
    client._access_token = "tok"
    client._access_token_expires = time.time() + 3600
    client._client_token = "ctok"
    client._client_token_expires = time.time() + 3600

    mock_http = MagicMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.get = AsyncMock(side_effect=Exception("Network error"))

    with patch("httpx.AsyncClient", return_value=mock_http):
        result = await client._query("fetchPlaylist", {})

    assert result is None


# ---------------------------------------------------------------------------
# _fmt_track_from_item
# ---------------------------------------------------------------------------


def test_fmt_track_valid():
    client = SpotifyPartnerClient()
    item = {
        "itemV2": {
            "__typename": "TrackResponseWrapper",
            "data": {
                "uri": "spotify:track:abc123",
                "name": "Test Song",
                "artists": {"items": [{"profile": {"name": "Test Artist"}, "uri": "spotify:artist:x1"}]},
                "albumOfTrack": {
                    "name": "Test Album",
                    "coverArt": {"sources": [{"url": "http://img", "width": 300}]},
                },
                "trackDuration": {"totalMilliseconds": 210000},
            },
        }
    }
    result = client._fmt_track_from_item(item)
    assert result is not None
    assert result["id"] == "abc123"
    assert result["title"] == "Test Song"
    assert result["artist"] == "Test Artist"
    assert result["album"] == "Test Album"
    assert result["duration_ms"] == 210000
    assert result["source"] == "spotify"


def test_fmt_track_wrong_typename():
    client = SpotifyPartnerClient()
    item = {"itemV2": {"__typename": "EpisodeResponseWrapper", "data": {}}}
    result = client._fmt_track_from_item(item)
    assert result is None


def test_fmt_track_empty_item():
    client = SpotifyPartnerClient()
    result = client._fmt_track_from_item({})
    assert result is None


def test_fmt_track_no_artists():
    client = SpotifyPartnerClient()
    item = {
        "itemV2": {
            "__typename": "TrackResponseWrapper",
            "data": {
                "uri": "spotify:track:xyz",
                "name": "Solo",
                "artists": {"items": []},
                "albumOfTrack": {"name": "Album"},
                "trackDuration": {"totalMilliseconds": 60000},
            },
        }
    }
    result = client._fmt_track_from_item(item)
    assert result is not None
    assert result["artist"] == "Unknown Artist"
    assert result["artist_id"] is None


# ---------------------------------------------------------------------------
# get_playlist — cache hit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_playlist_cache_hit():
    client = SpotifyPartnerClient()
    cached_payload = json.dumps({"id": "pl1", "tracks": [], "title": "Cached"})

    with patch("app.core.cache.cache_manager") as mock_cache:
        mock_cache.get = AsyncMock(return_value=cached_payload)
        result = await client.get_playlist("pl1")

    assert result is not None
    assert result["title"] == "Cached"


@pytest.mark.asyncio
async def test_get_playlist_returns_none_on_no_data():
    client = SpotifyPartnerClient()

    with patch("app.core.cache.cache_manager") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        with patch.object(client, "_query", new_callable=AsyncMock, return_value=None):
            result = await client.get_playlist("pl1")

    assert result is None


@pytest.mark.asyncio
async def test_get_playlist_single_page():
    client = SpotifyPartnerClient()

    pl_data = {
        "data": {
            "playlistV2": {
                "name": "My Playlist",
                "images": {"items": [{"sources": [{"url": "http://cover.jpg"}]}]},
                "content": {
                    "totalCount": 2,
                    "items": [
                        {
                            "itemV2": {
                                "__typename": "TrackResponseWrapper",
                                "data": {
                                    "uri": "spotify:track:t1",
                                    "name": "Track 1",
                                    "artists": {"items": [{"profile": {"name": "A"}, "uri": "spotify:artist:a1"}]},
                                    "albumOfTrack": {"name": "Alb"},
                                    "trackDuration": {"totalMilliseconds": 180000},
                                },
                            }
                        },
                        {
                            "itemV2": {
                                "__typename": "TrackResponseWrapper",
                                "data": {
                                    "uri": "spotify:track:t2",
                                    "name": "Track 2",
                                    "artists": {"items": [{"profile": {"name": "B"}, "uri": "spotify:artist:b1"}]},
                                    "albumOfTrack": {"name": "Alb2"},
                                    "trackDuration": {"totalMilliseconds": 200000},
                                },
                            }
                        },
                    ],
                },
            }
        }
    }

    with patch("app.core.cache.cache_manager") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        with patch.object(client, "_query", new_callable=AsyncMock, return_value=pl_data):
            result = await client.get_playlist("pl1")

    assert result is not None
    assert result["title"] == "My Playlist"
    assert len(result["tracks"]) == 2
    assert result["tracks"][0]["title"] == "Track 1"
    assert result["image_url"] == "http://cover.jpg"
    mock_cache.set.assert_called_once()


# ---------------------------------------------------------------------------
# invalidate_playlist_cache
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalidate_playlist_cache():
    client = SpotifyPartnerClient()
    with patch("app.core.cache.cache_manager") as mock_cache:
        mock_cache.delete = AsyncMock()
        await client.invalidate_playlist_cache("pl1")
    mock_cache.delete.assert_called_once_with("sp:pl:pl1")


@pytest.mark.asyncio
async def test_invalidate_playlist_cache_swallows_error():
    client = SpotifyPartnerClient()
    with patch("app.core.cache.cache_manager") as mock_cache:
        mock_cache.delete = AsyncMock(side_effect=Exception("Redis down"))
        # Should not raise
        await client.invalidate_playlist_cache("pl1")
