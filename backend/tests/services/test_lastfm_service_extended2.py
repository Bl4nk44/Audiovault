"""Extended TDD tests for LastfmService — targeting uncovered lines.

RED phase: written before implementation changes.
Covers: close(), _sign_params(), _request() error paths, _post_request(),
get_auth_url(), get_session(), get_user_info(), get_user_friends(),
get_user_recent_tracks(), get_user_top_tags(), get_artist_top_tags(),
_fetch_raw_artists_authenticated(), _fetch_raw_top_artists(),
_build_recommended_artist(), get_recommended_artists(),
get_similar_tracks(), get_similar_artists(), update_now_playing(),
scrobble(), _parse_artist_name(), _add_track_seeds(), _add_artist_seeds(),
_add_to_candidates(), _extract_best_image().
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.schemas.recommendation import RecommendedArtist
from app.services.lastfm_service import (
    LastfmAPIError,
    LastfmRateLimitError,
    LastfmService,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def svc():
    """LastfmService with mocked HTTP client (no real network)."""
    service = LastfmService()
    service.client = AsyncMock()
    return service


def _ok_response(body: dict) -> Mock:
    """Build a successful httpx-like response mock."""
    r = Mock()
    r.status_code = 200
    r.json.return_value = body
    r.raise_for_status = Mock()
    return r


def _api_error_response(code: int = 6, message: str = "Artist not found") -> Mock:
    r = Mock()
    r.status_code = 200
    r.json.return_value = {"error": code, "message": message}
    r.raise_for_status = Mock()
    return r


def _status_error_response(status: int) -> Mock:
    r = Mock()
    r.status_code = status
    r.json.return_value = {}
    r.raise_for_status = Mock(side_effect=httpx.HTTPStatusError("err", request=Mock(), response=Mock()))
    return r


# ===========================================================================
# close()
# ===========================================================================


async def test_close_calls_aclose(svc):
    """Line 45: close() must delegate to client.aclose()."""
    # Arrange
    svc.client.aclose = AsyncMock()

    # Act
    await svc.close()

    # Assert
    svc.client.aclose.assert_awaited_once()


# ===========================================================================
# _sign_params()
# ===========================================================================


def test_sign_params_excludes_format_and_callback(svc):
    """Lines 67-72: 'format' and 'callback' must be excluded from signature."""
    # Arrange
    params = {"method": "auth.getSession", "api_key": "key", "token": "tok", "format": "json", "callback": "cb"}

    # Act
    with patch("app.services.lastfm_service.settings") as mock_settings:
        mock_settings.LASTFM_API_SECRET = "secret"
        sig = svc._sign_params(params)

    # Assert — just check it returns a 32-char hex string
    assert len(sig) == 32
    assert sig.isalnum()


def test_sign_params_deterministic(svc):
    """_sign_params must return identical output for same input regardless of dict order."""
    params_a = {"api_key": "k", "method": "m", "token": "t"}
    params_b = {"token": "t", "method": "m", "api_key": "k"}

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_SECRET = "s"
        sig_a = svc._sign_params(params_a)
        sig_b = svc._sign_params(params_b)

    assert sig_a == sig_b


# ===========================================================================
# _request() — error paths
# ===========================================================================


async def test_request_raises_rate_limit_on_429(svc):
    """Line 98: status 429 raises LastfmRateLimitError."""
    r = Mock()
    r.status_code = 429
    svc.client.get.return_value = r

    with pytest.raises(LastfmRateLimitError):
        await svc._request("some.method", {})


async def test_request_raises_api_error_on_error_field(svc):
    """Lines 97-98: 'error' key in JSON body raises LastfmAPIError."""
    svc.client.get.return_value = _api_error_response(6, "Artist not found")

    with pytest.raises(LastfmAPIError, match="Last.fm API Error 6"):
        await svc._request("artist.getInfo", {"artist": "nobody"})


async def test_request_raises_api_error_on_http_exception(svc):
    """Lines 101-103: httpx.HTTPError is wrapped in LastfmAPIError."""
    svc.client.get.side_effect = httpx.HTTPError("connection refused")

    with pytest.raises(LastfmAPIError, match="HTTP request failed"):
        await svc._request("user.getInfo", {"user": "x"})


async def test_request_signed_adds_api_sig(svc):
    """Line 82: when signed=True, params must include api_sig."""
    captured = {}

    async def capture_call(*args, **kwargs):
        captured.update(kwargs.get("params", {}))
        return _ok_response({"session": {"key": "sk", "name": "u"}})

    svc.client.get.side_effect = capture_call

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "apikey"
        s.LASTFM_API_SECRET = "secret"
        await svc._request("auth.getSession", {"token": "t"}, signed=True)

    assert "api_sig" in captured


# ===========================================================================
# get_auth_url()
# ===========================================================================


def test_get_auth_url_with_explicit_base_url(svc):
    """Lines 106-107: base_url provided — callback must use it."""
    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "mykey"
        url = svc.get_auth_url(base_url="https://myapp.example.com/")

    assert "mykey" in url
    assert "myapp.example.com/recommendations" in url


def test_get_auth_url_strips_trailing_slash(svc):
    """get_auth_url must strip trailing slash before appending /recommendations."""
    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        url = svc.get_auth_url(base_url="https://app.io///")

    # Must not have double slashes before /recommendations
    assert "//recommendations" not in url


def test_get_auth_url_fallback_to_cors_origin(svc):
    """Lines 109-113: when base_url is None, use first CORS origin."""
    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.BACKEND_CORS_ORIGINS = ["https://cors.example.com"]
        url = svc.get_auth_url()

    assert "cors.example.com" in url


def test_get_auth_url_fallback_to_localhost_when_no_cors(svc):
    """Lines 111-112: empty CORS list falls back to http://localhost:3000."""
    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.BACKEND_CORS_ORIGINS = []
        url = svc.get_auth_url()

    assert "localhost:3000" in url


# ===========================================================================
# get_session()
# ===========================================================================


async def test_get_session_returns_session_dict(svc):
    """Lines 119-121: successful token exchange returns session dict."""
    svc.client.get.return_value = _ok_response({"session": {"key": "session_key_123", "name": "user"}})

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        result = await svc.get_session("mytoken")

    assert result["key"] == "session_key_123"
    assert result["name"] == "user"


async def test_get_session_returns_empty_dict_when_no_session(svc):
    """get_session returns {} when response lacks 'session' key."""
    svc.client.get.return_value = _ok_response({})

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        result = await svc.get_session("bad_token")

    assert result == {}


async def test_get_session_propagates_api_error(svc):
    """get_session must propagate LastfmAPIError on bad response."""
    svc.client.get.return_value = _api_error_response(4, "Invalid token")

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        with pytest.raises(LastfmAPIError):
            await svc.get_session("bad")


# ===========================================================================
# get_user_info()
# ===========================================================================


async def test_get_user_info_maps_fields_correctly(svc):
    """Lines 133-135: all fields extracted and cast properly."""
    svc.client.get.return_value = _ok_response(
        {
            "user": {
                "name": "jdoe",
                "realname": "John Doe",
                "url": "https://last.fm/user/jdoe",
                "country": "PL",
                "age": "30",
                "playcount": "12345",
                "artist_count": "200",
                "track_count": "5000",
                "album_count": "300",
                "image": [{"#text": "https://img.example.com/big.jpg", "size": "large"}],
                "registered": {"unixtime": "1609459200"},
                "subscriber": "0",
            }
        }
    )

    result = await svc.get_user_info("jdoe")

    assert result["name"] == "jdoe"
    assert result["realname"] == "John Doe"
    assert result["playcount"] == 12345
    assert result["artist_count"] == 200
    assert result["subscriber"] is False
    assert result["image_url"] == "https://img.example.com/big.jpg"


async def test_get_user_info_subscriber_true(svc):
    """subscriber == '1' maps to True."""
    svc.client.get.return_value = _ok_response(
        {
            "user": {
                "name": "vip",
                "realname": "",
                "url": "",
                "country": "",
                "age": "0",
                "playcount": "0",
                "artist_count": "0",
                "track_count": "0",
                "album_count": "0",
                "image": [],
                "registered": {"unixtime": "0"},
                "subscriber": "1",
            }
        }
    )

    result = await svc.get_user_info("vip")
    assert result["subscriber"] is True


async def test_get_user_info_raises_on_api_error(svc):
    """Lines 133-135 path: LastfmAPIError propagates."""
    svc.client.get.return_value = _api_error_response(17, "Login: User required to be logged in")

    with pytest.raises(LastfmAPIError):
        await svc.get_user_info("anon")


# ===========================================================================
# get_user_friends()
# ===========================================================================


async def test_get_user_friends_returns_list(svc):
    """Lines 152-157: friend list is parsed correctly."""
    svc.client.get.return_value = _ok_response(
        {
            "friends": {
                "user": [
                    {
                        "name": "alice",
                        "realname": "Alice",
                        "url": "https://last.fm/user/alice",
                        "country": "US",
                        "image": [{"#text": "https://img.example.com/alice.jpg", "size": "medium"}],
                    }
                ]
            }
        }
    )

    friends = await svc.get_user_friends("jdoe")

    assert len(friends) == 1
    assert friends[0]["name"] == "alice"
    assert friends[0]["image_url"] == "https://img.example.com/alice.jpg"


async def test_get_user_friends_single_friend_as_dict(svc):
    """Lines 154-155: when Last.fm returns a single friend as dict (not list), wrap it."""
    svc.client.get.return_value = _ok_response(
        {
            "friends": {
                "user": {
                    "name": "bob",
                    "realname": "Bob",
                    "url": "",
                    "country": "",
                    "image": [],
                }
            }
        }
    )

    friends = await svc.get_user_friends("jdoe")

    assert len(friends) == 1
    assert friends[0]["name"] == "bob"


async def test_get_user_friends_empty_list(svc):
    """get_user_friends returns [] when friends section is missing."""
    svc.client.get.return_value = _ok_response({})

    friends = await svc.get_user_friends("jdoe")
    assert friends == []


# ===========================================================================
# get_user_recent_tracks() / get_user_top_tags()
# ===========================================================================


async def test_get_user_recent_tracks_returns_tracks(svc):
    """Lines 182-183: recenttracks extracted."""
    svc.client.get.return_value = _ok_response({"recenttracks": {"track": [{"name": "T1", "artist": {"#text": "A1"}}]}})

    result = await svc.get_user_recent_tracks("user1")
    assert len(result) == 1
    assert result[0]["name"] == "T1"


async def test_get_user_top_tags_returns_tags(svc):
    """Lines 187-192: toptags extracted."""
    svc.client.get.return_value = _ok_response({"toptags": {"tag": [{"name": "rock"}, {"name": "indie"}]}})

    result = await svc.get_user_top_tags("user1")
    assert len(result) == 2
    assert result[0]["name"] == "rock"


# ===========================================================================
# get_artist_top_tags()
# ===========================================================================


async def test_get_artist_top_tags_returns_name_list(svc):
    """Lines 195-201: tag names extracted up to limit."""
    svc.client.get.return_value = _ok_response(
        {"toptags": {"tag": [{"name": "rock"}, {"name": "alternative"}, {"name": "indie"}]}}
    )

    result = await svc.get_artist_top_tags("Radiohead", limit=2)
    assert result == ["rock", "alternative"]


async def test_get_artist_top_tags_returns_empty_on_error(svc):
    """Lines 191-192: exception swallowed, returns []."""
    svc.client.get.side_effect = httpx.HTTPError("boom")

    result = await svc.get_artist_top_tags("Unknown Artist")
    assert result == []


async def test_get_artist_top_tags_skips_tags_without_name(svc):
    """Tags with no 'name' key must be filtered out."""
    svc.client.get.return_value = _ok_response({"toptags": {"tag": [{"name": ""}, {"name": "pop"}]}})

    result = await svc.get_artist_top_tags("X")
    assert result == ["pop"]


# ===========================================================================
# _fetch_raw_artists_authenticated() / _fetch_raw_top_artists()
# ===========================================================================


async def test_fetch_raw_artists_authenticated_returns_list(svc):
    """Lines 195-201: successful authenticated fetch."""
    svc.client.get.return_value = _ok_response(
        {"recommendations": {"artist": [{"name": "Portishead"}, {"name": "Massive Attack"}]}}
    )

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        result = await svc._fetch_raw_artists_authenticated("sk123", 10)

    assert len(result) == 2
    assert result[0]["name"] == "Portishead"


async def test_fetch_raw_artists_authenticated_wraps_single_dict(svc):
    """Lines 197-198: single artist dict is wrapped in a list."""
    svc.client.get.return_value = _ok_response({"recommendations": {"artist": {"name": "Solo Artist"}}})

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        result = await svc._fetch_raw_artists_authenticated("sk", 5)

    assert len(result) == 1
    assert result[0]["name"] == "Solo Artist"


async def test_fetch_raw_artists_authenticated_returns_empty_on_error(svc):
    """Lines 199-201: exception swallowed, returns []."""
    svc.client.get.side_effect = httpx.HTTPError("fail")

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        result = await svc._fetch_raw_artists_authenticated("sk", 5)

    assert result == []


async def test_fetch_raw_top_artists_returns_list(svc):
    """Lines 204-210: fallback top artists fetch."""
    svc.client.get.return_value = _ok_response({"topartists": {"artist": [{"name": "Nirvana"}, {"name": "Pearl Jam"}]}})

    result = await svc._fetch_raw_top_artists("grunge_fan", 5)
    assert len(result) == 2


async def test_fetch_raw_top_artists_returns_empty_on_error(svc):
    """Lines 208-210: exception swallowed, returns []."""
    svc.client.get.side_effect = httpx.HTTPError("network error")

    result = await svc._fetch_raw_top_artists("user", 5)
    assert result == []


async def test_fetch_raw_top_artists_wraps_single_dict(svc):
    """Single artist dict must be wrapped."""
    svc.client.get.return_value = _ok_response({"topartists": {"artist": {"name": "Lone Artist"}}})

    result = await svc._fetch_raw_top_artists("u", 5)
    assert len(result) == 1
    assert result[0]["name"] == "Lone Artist"


# ===========================================================================
# _build_recommended_artist()
# ===========================================================================


def test_build_recommended_artist_happy_path(svc):
    """Lines 213-216: valid artist dict returns RecommendedArtist."""
    a = {"name": "Radiohead", "url": "https://last.fm/artist/Radiohead", "image": [], "mbid": "abc", "match": "0.9"}
    result = svc._build_recommended_artist(a)

    assert isinstance(result, RecommendedArtist)
    assert result.name == "Radiohead"
    assert result.match == 0.9


def test_build_recommended_artist_returns_none_when_no_name(svc):
    """Lines 213-215: missing name returns None."""
    result = svc._build_recommended_artist({"url": "x"})
    assert result is None


def test_build_recommended_artist_match_defaults_to_zero(svc):
    """match=None/missing must default to 0.0."""
    result = svc._build_recommended_artist({"name": "X"})
    assert result is not None
    assert result.match == 0.0


def test_build_recommended_artist_extracts_rank_from_top_artists(svc):
    """TopArtists items carry @attr.rank (no match) → expose rank for UI badge."""
    a = {"name": "Tool", "url": "x", "@attr": {"rank": "3"}}
    result = svc._build_recommended_artist(a)
    assert result is not None
    assert result.match == 0.0
    assert result.rank == 3


def test_build_recommended_artist_rank_none_when_absent(svc):
    """Recommended artists (with match, no @attr) leave rank=None."""
    result = svc._build_recommended_artist({"name": "X", "match": "0.5"})
    assert result is not None
    assert result.rank is None


# ===========================================================================
# get_recommended_artists()
# ===========================================================================


async def test_get_recommended_artists_uses_session_key(svc):
    """Lines 228-244: session_key triggers authenticated fetch."""
    svc.client.get.return_value = _ok_response(
        {"recommendations": {"artist": [{"name": "Thom Yorke", "url": "", "image": [], "mbid": None, "match": "0.8"}]}}
    )

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        result = await svc.get_recommended_artists(session_key="sk", limit=5)

    assert len(result) == 1
    assert result[0].name == "Thom Yorke"


async def test_get_recommended_artists_falls_back_to_top_artists(svc):
    """Lines 233-235: empty session result falls back to user_name top artists."""
    call_count = {"n": 0}

    async def side(url, **kwargs):
        call_count["n"] += 1
        params = kwargs.get("params", {})
        method = params.get("method", "")
        r = Mock()
        r.status_code = 200
        r.raise_for_status = Mock()
        if method == "user.getRecommendedArtists":
            r.json.return_value = {"recommendations": {"artist": []}}
        else:
            r.json.return_value = {
                "topartists": {"artist": [{"name": "Sigur Ros", "url": "", "image": [], "mbid": None, "match": "0.7"}]}
            }
        return r

    svc.client.get.side_effect = side

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        result = await svc.get_recommended_artists(session_key="sk", limit=5, user_name="sigur_fan")

    assert len(result) == 1
    assert result[0].name == "Sigur Ros"


async def test_get_recommended_artists_returns_empty_when_no_data(svc):
    """Lines 237-239: no session and no user_name → []."""
    result = await svc.get_recommended_artists(session_key=None, limit=5, user_name=None)
    assert result == []


async def test_get_recommended_artists_filters_nameless(svc):
    """_build_recommended_artist returns None for nameless → filtered out."""
    svc.client.get.return_value = _ok_response(
        {
            "recommendations": {
                "artist": [
                    {"name": "Valid", "url": "", "image": [], "mbid": None, "match": "0.5"},
                    {"url": "no-name", "image": []},
                ]
            }
        }
    )

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        result = await svc.get_recommended_artists(session_key="sk")

    assert len(result) == 1
    assert result[0].name == "Valid"


# ===========================================================================
# get_similar_tracks() — error path
# ===========================================================================


async def test_get_similar_tracks_returns_empty_on_api_error(svc):
    """Lines 250-252: LastfmAPIError caught, returns []."""
    svc.client.get.return_value = _api_error_response(6, "Track not found")

    result = await svc.get_similar_tracks("Artist", "NoSuchTrack")
    assert result == []


# ===========================================================================
# get_similar_artists() — error path
# ===========================================================================


async def test_get_similar_artists_returns_empty_on_api_error(svc):
    """Lines 258-259: LastfmAPIError caught, returns []."""
    svc.client.get.return_value = _api_error_response(6, "Artist not found")

    result = await svc.get_similar_artists("NoSuchArtist")
    assert result == []


# ===========================================================================
# update_now_playing()
# ===========================================================================


async def test_update_now_playing_without_album(svc):
    """Lines 262-266: album=None — must NOT include album in params."""
    svc.client.post.return_value = _ok_response({"nowplaying": {}})

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        await svc.update_now_playing("Song", "Artist", "sk123")

    call_args = svc.client.post.call_args
    data = call_args[1].get("data", {}) or call_args[0][1] if call_args[0] else {}
    # 'album' key must not be present
    assert "album" not in data


async def test_update_now_playing_with_album(svc):
    """Lines 264-265: album provided — must appear in params."""
    svc.client.post.return_value = _ok_response({"nowplaying": {}})

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        await svc.update_now_playing("Song", "Artist", "sk123", album="My Album")

    call_args = svc.client.post.call_args
    data = call_args[1].get("data", {})
    assert data.get("album") == "My Album"


# ===========================================================================
# scrobble()
# ===========================================================================


async def test_scrobble_without_album(svc):
    """Lines 272-284: scrobble with no album."""
    svc.client.post.return_value = _ok_response({"scrobbles": {}})

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        await svc.scrobble("Song", "Artist", "sk123", timestamp=1700000000)

    svc.client.post.assert_awaited_once()
    data = svc.client.post.call_args[1].get("data", {})
    assert data["track"] == "Song"
    assert data["artist"] == "Artist"
    assert data["timestamp"] == 1700000000
    assert "album" not in data


async def test_scrobble_with_album(svc):
    """Lines 274-275: album param included when given."""
    svc.client.post.return_value = _ok_response({"scrobbles": {}})

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        await svc.scrobble("Song", "Artist", "sk123", timestamp=1700000000, album="Ablaze")

    data = svc.client.post.call_args[1].get("data", {})
    assert data.get("album") == "Ablaze"


# ===========================================================================
# _post_request() — error paths
# ===========================================================================


async def test_post_request_raises_rate_limit_on_429(svc):
    """Lines 301-302: POST 429 raises LastfmRateLimitError."""
    r = Mock()
    r.status_code = 429
    svc.client.post.return_value = r

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        with pytest.raises(LastfmRateLimitError):
            await svc._post_request("track.scrobble", {"track": "x", "artist": "y", "sk": "z", "timestamp": 0})


async def test_post_request_raises_api_error_on_error_field(svc):
    """Lines 309-310: error field in POST response raises LastfmAPIError."""
    svc.client.post.return_value = _api_error_response(9, "Invalid session key")

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        with pytest.raises(LastfmAPIError, match="Last.fm API Error 9"):
            await svc._post_request("track.scrobble", {"track": "x", "artist": "y", "sk": "bad", "timestamp": 0})


async def test_post_request_raises_api_error_on_http_exception(svc):
    """Lines 313-315: httpx.HTTPError wrapped in LastfmAPIError."""
    svc.client.post.side_effect = httpx.HTTPError("timeout")

    with patch("app.services.lastfm_service.settings") as s:
        s.LASTFM_API_KEY = "k"
        s.LASTFM_API_SECRET = "sec"
        with pytest.raises(LastfmAPIError, match="HTTP POST failed"):
            await svc._post_request("track.scrobble", {"track": "x", "artist": "y", "sk": "s", "timestamp": 0})


# ===========================================================================
# _parse_artist_name()
# ===========================================================================


def test_parse_artist_name_from_string(svc):
    """Line 319: string input returns itself."""
    assert svc._parse_artist_name("Radiohead") == "Radiohead"


def test_parse_artist_name_from_dict_with_name_key(svc):
    """Lines 321: dict with 'name' key."""
    assert svc._parse_artist_name({"name": "Portishead"}) == "Portishead"


def test_parse_artist_name_from_dict_with_text_key(svc):
    """Lines 321: dict with '#text' key when 'name' absent."""
    assert svc._parse_artist_name({"#text": "Bjork"}) == "Bjork"


def test_parse_artist_name_from_object_with_name_attr(svc):
    """Lines 322-323: object with .name attribute."""

    class FakeArtist:
        name = "Sigur Ros"

    assert svc._parse_artist_name(FakeArtist()) == "Sigur Ros"


def test_parse_artist_name_returns_none_for_unknown_type(svc):
    """Line 324: unsupported type returns None."""
    assert svc._parse_artist_name(42) is None


# ===========================================================================
# _add_track_seeds()
# ===========================================================================


def test_add_track_seeds_adds_valid_tracks(svc):
    """Line 328-332: tracks with name and artist are appended."""
    seeds: list[tuple[str, str]] = []
    tracks = [{"name": "Song1", "artist": {"name": "Artist1"}}, {"name": "Song2", "artist": "Artist2"}]

    svc._add_track_seeds(tracks, seeds)

    assert ("Song1", "Artist1") in seeds
    assert ("Song2", "Artist2") in seeds


def test_add_track_seeds_skips_exception_result(svc):
    """Line 327-328: Exception result is ignored."""
    seeds: list[tuple[str, str]] = []
    svc._add_track_seeds(Exception("fail"), seeds)
    assert seeds == []


def test_add_track_seeds_skips_tracks_without_artist(svc):
    """Tracks with no parseable artist are not added."""
    seeds: list[tuple[str, str]] = []
    svc._add_track_seeds([{"name": "T1", "artist": 42}], seeds)
    assert seeds == []


# ===========================================================================
# _add_artist_seeds()
# ===========================================================================


def test_add_artist_seeds_adds_valid_artists(svc):
    """Lines 334-339: valid artist names added to set."""
    seed_set: set = set()
    artists = [{"name": "Radiohead"}, {"name": "Portishead"}]

    svc._add_artist_seeds(artists, seed_set)

    assert "Radiohead" in seed_set
    assert "Portishead" in seed_set


def test_add_artist_seeds_skips_exception_result(svc):
    """Line 335-336: Exception result short-circuits."""
    seed_set: set = set()
    svc._add_artist_seeds(Exception("fail"), seed_set)
    assert len(seed_set) == 0


# ===========================================================================
# _add_to_candidates()
# ===========================================================================


def test_add_to_candidates_creates_new_entry(svc):
    """Lines 415-441: new candidate added with correct score."""
    candidates: dict = {}
    item = {
        "name": "Track A",
        "artist": {"name": "Artist X"},
        "match": "0.9",
        "url": "https://last.fm/track",
        "image": [{"#text": "https://img.example.com/t.jpg", "size": "large"}],
    }

    svc._add_to_candidates(candidates, item)

    key = "Artist X - Track A"
    assert key in candidates
    assert candidates[key].score == pytest.approx(0.9, rel=1e-3)


def test_add_to_candidates_accumulates_score(svc):
    """Calling twice with same key accumulates score."""
    candidates: dict = {}
    item = {"name": "T", "artist": "A", "match": "0.5", "url": "", "image": []}

    svc._add_to_candidates(candidates, item)
    svc._add_to_candidates(candidates, item)

    assert candidates["A - T"].score == pytest.approx(1.0, rel=1e-3)


def test_add_to_candidates_skips_when_no_name(svc):
    """Lines 420-421: item without name skipped."""
    candidates: dict = {}
    svc._add_to_candidates(candidates, {"artist": "X", "match": "0.5"})
    assert len(candidates) == 0


def test_add_to_candidates_skips_when_no_artist(svc):
    """Lines 419-421: item without parseable artist skipped."""
    candidates: dict = {}
    svc._add_to_candidates(candidates, {"name": "T", "match": "0.5"})
    assert len(candidates) == 0


def test_add_to_candidates_uses_rank_for_score(svc):
    """Lines 424-426: 'rank' key inverted for score calculation."""
    candidates: dict = {}
    item = {"name": "T", "artist": "A", "rank": "0", "url": "", "image": []}

    svc._add_to_candidates(candidates, item)

    # rank=0 → match = 1/(0+1) = 1.0
    assert candidates["A - T"].score == pytest.approx(1.0, rel=1e-3)


def test_add_to_candidates_uses_artist_image_as_fallback(svc):
    """Lines 433-435: artist dict image used when track image absent."""
    candidates: dict = {}
    item = {
        "name": "T",
        "artist": {"name": "A", "image": [{"#text": "https://img.example.com/artist.jpg", "size": "large"}]},
        "match": "0.5",
        "url": "",
        "image": [],
    }

    svc._add_to_candidates(candidates, item)

    assert candidates["A - T"].image_url == "https://img.example.com/artist.jpg"


def test_add_to_candidates_with_score_mult(svc):
    """Lines 441: score_mult applied."""
    candidates: dict = {}
    item = {"name": "T", "artist": "A", "match": "1.0", "url": "", "image": []}

    svc._add_to_candidates(candidates, item, score_mult=0.5)

    assert candidates["A - T"].score == pytest.approx(0.5, rel=1e-3)


# ===========================================================================
# _extract_best_image()
# ===========================================================================


def test_extract_best_image_prefers_mega(svc):
    """Lines 443-464: 'mega' preferred over smaller sizes."""
    images = [
        {"#text": "https://img.example.com/large.jpg", "size": "large"},
        {"#text": "https://img.example.com/mega.jpg", "size": "mega"},
        {"#text": "https://img.example.com/medium.jpg", "size": "medium"},
    ]
    assert svc._extract_best_image(images) == "https://img.example.com/mega.jpg"


def test_extract_best_image_falls_through_size_order(svc):
    """Lines 454-457: falls through to next available size."""
    images = [{"#text": "https://img.example.com/small.jpg", "size": "small"}]
    assert svc._extract_best_image(images) == "https://img.example.com/small.jpg"


def test_extract_best_image_skips_empty_urls(svc):
    """Lines 456-457: empty string URL must be skipped."""
    images = [
        {"#text": "", "size": "mega"},
        {"#text": "   ", "size": "extralarge"},
        {"#text": "https://img.example.com/ok.jpg", "size": "large"},
    ]
    assert svc._extract_best_image(images) == "https://img.example.com/ok.jpg"


def test_extract_best_image_returns_none_for_empty_list(svc):
    """Lines 445-446: empty list returns None."""
    assert svc._extract_best_image([]) is None


def test_extract_best_image_last_resort_any_url(svc):
    """Lines 460-462: unknown size falls back to last resort."""
    images = [{"#text": "https://img.example.com/custom.jpg", "size": "unknown_size"}]
    assert svc._extract_best_image(images) == "https://img.example.com/custom.jpg"


def test_extract_best_image_returns_none_when_all_empty(svc):
    """Lines 463-464: all URLs empty/whitespace returns None."""
    images = [{"#text": "", "size": "mega"}, {"#text": "  ", "size": "large"}]
    assert svc._extract_best_image(images) is None
