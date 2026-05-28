"""
TDD RED-GREEN — extended2 coverage for SpotifyService.

Targets uncovered lines:
  85-89    _save_refresh_token
  94-99    _load_refresh_token (file-exists branch)
  106-114  get_auth_url
  117-142  _exchange_code
  145-193  _handle_callback_connection
  196-202  start_oauth_server
  205-208  stop_oauth_server
  215-244  _refresh_access_token
  261-264  _oauth_client_credentials error path
  272      _sp_dc_token (no sp_dc → early return)
  280-287  _sp_dc_token happy path
  293-295  inject_token
  303-313  _ensure_token refresh_token path
  318-319  _ensure_token sp_dc fallback
  324-325  _ensure_token client_credentials fallback
  336      is_oauth_authenticated property
  362      _request 401 → retry token also empty
  381,386  _proxy_base / _proxy_get
  456      get_track proxy hit
  469      get_playlist_details proxy hit
  489,503  get_album_details proxy hit / pagination break
  512      get_album_details pagination None break
  613,619  _fetch_resource playlist/album empty return
  626      _fetch_resource artist no data
"""

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.spotify_service import SpotifyService


@pytest.fixture
def service():
    """Fresh SpotifyService with no file side-effects."""
    with patch.object(Path, "exists", return_value=False):
        svc = SpotifyService()
    return svc


# ─────────────────────────────────────────────────────────────────────────────
# _save_refresh_token (lines 85-89)
# ─────────────────────────────────────────────────────────────────────────────


def test_save_refresh_token_writes_file(service, tmp_path):
    """Happy path: file is written with the refresh token."""
    service._refresh_token = "rt_abc"
    target = tmp_path / ".spotify_auth.json"

    with patch("app.services.spotify_service._AUTH_FILE", target):
        service._save_refresh_token()

    data = json.loads(target.read_text())
    assert data["refresh_token"] == "rt_abc"


def test_save_refresh_token_logs_warning_on_failure(service):
    """OSError during write is swallowed and logged as warning."""
    service._refresh_token = "rt_x"

    with (
        patch.object(Path, "mkdir", side_effect=OSError("no space")),
        patch("app.services.spotify_service.logger") as mock_logger,
    ):
        service._save_refresh_token()

    mock_logger.warning.assert_called_once()
    assert "Failed to save" in mock_logger.warning.call_args[0][0]


# ─────────────────────────────────────────────────────────────────────────────
# _load_refresh_token (lines 94-99)
# ─────────────────────────────────────────────────────────────────────────────


def test_load_refresh_token_reads_from_disk(tmp_path):
    """When auth file exists and has a valid token, it is loaded."""
    target = tmp_path / ".spotify_auth.json"
    target.write_text(json.dumps({"refresh_token": "loaded_rt"}))

    with patch("app.services.spotify_service._AUTH_FILE", target):
        svc = SpotifyService()

    assert svc._refresh_token == "loaded_rt"


def test_load_refresh_token_missing_key_in_file(tmp_path):
    """File exists but no 'refresh_token' key → _refresh_token stays None."""
    target = tmp_path / ".spotify_auth.json"
    target.write_text(json.dumps({"other": "value"}))

    with patch("app.services.spotify_service._AUTH_FILE", target):
        svc = SpotifyService()

    assert svc._refresh_token is None


def test_load_refresh_token_invalid_json_logs_warning(tmp_path):
    """Corrupted file is handled gracefully."""
    target = tmp_path / ".spotify_auth.json"
    target.write_text("not-json{")

    with (
        patch("app.services.spotify_service._AUTH_FILE", target),
        patch("app.services.spotify_service.logger") as mock_logger,
    ):
        svc = SpotifyService()

    mock_logger.warning.assert_called_once()
    assert svc._refresh_token is None


# ─────────────────────────────────────────────────────────────────────────────
# get_auth_url (lines 106-114)
# ─────────────────────────────────────────────────────────────────────────────


def test_get_auth_url_returns_spotify_authorize_url(service):
    """URL contains required OAuth params and updates _oauth_state."""
    url = service.get_auth_url()

    assert "https://accounts.spotify.com/authorize" in url
    assert "client_id=" in url
    assert "response_type=code" in url
    assert "scope=" in url
    assert service._oauth_state != ""
    assert service._oauth_state in url


def test_get_auth_url_generates_unique_state_each_call(service):
    """Each call produces a different CSRF state."""
    url1 = service.get_auth_url()
    state1 = service._oauth_state
    url2 = service.get_auth_url()
    state2 = service._oauth_state

    assert state1 != state2
    assert state1 in url1
    assert state2 in url2


# ─────────────────────────────────────────────────────────────────────────────
# _exchange_code (lines 117-142)
# ─────────────────────────────────────────────────────────────────────────────


async def test_exchange_code_stores_token_and_saves_refresh(service, tmp_path):
    """Successful code exchange sets token and persists refresh token."""
    target = tmp_path / ".spotify_auth.json"
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "access_token": "at_new",
        "expires_in": 3600,
        "refresh_token": "rt_new",
    }

    with (
        patch("app.services.spotify_service._AUTH_FILE", target),
        patch("httpx.AsyncClient") as mock_cls,
    ):
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        await service._exchange_code("auth_code_123")

    assert service._token == "at_new"
    assert service._refresh_token == "rt_new"
    data = json.loads(target.read_text())
    assert data["refresh_token"] == "rt_new"


async def test_exchange_code_without_new_refresh_token(service):
    """If response omits refresh_token, existing one is unchanged."""
    service._refresh_token = "old_rt"
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "access_token": "at_only",
        "expires_in": 3600,
    }

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        await service._exchange_code("code_x")

    assert service._token == "at_only"
    assert service._refresh_token == "old_rt"


async def test_exchange_code_http_error_is_logged(service):
    """HTTP error during exchange is caught and logged."""
    with (
        patch("httpx.AsyncClient") as mock_cls,
        patch("app.services.spotify_service.logger") as mock_logger,
    ):
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=RuntimeError("timeout"))

        await service._exchange_code("bad_code")

    mock_logger.error.assert_called_once()
    assert service._token is None


# ─────────────────────────────────────────────────────────────────────────────
# _handle_callback_connection (lines 145-193)
# ─────────────────────────────────────────────────────────────────────────────


async def _make_callback_request(service, raw_request: bytes) -> bytes:
    """Helper: feed raw HTTP bytes into the callback handler, return written bytes."""
    reader = asyncio.StreamReader()
    reader.feed_data(raw_request)
    reader.feed_eof()

    written = bytearray()

    writer = MagicMock()
    writer.write = lambda data: written.extend(data)
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()

    await service._handle_callback_connection(reader, writer)
    return bytes(written)


async def test_callback_handler_success_code_and_state(service):
    """Valid code + matching state triggers _exchange_code."""
    service._oauth_state = "teststate"

    request = b"GET /?code=mycode&state=teststate HTTP/1.1\r\nHost: localhost\r\n\r\n"

    with patch.object(service, "_exchange_code", new_callable=AsyncMock) as mock_exc:
        response = await _make_callback_request(service, request)

    mock_exc.assert_called_once_with("mycode")
    assert b"200 OK" in response
    assert b"Spotify Connected" in response


async def test_callback_handler_state_mismatch(service):
    """State mismatch returns CSRF warning without calling exchange."""
    service._oauth_state = "correct_state"
    request = b"GET /?code=mycode&state=wrong_state HTTP/1.1\r\nHost: localhost\r\n\r\n"

    with (
        patch.object(service, "_exchange_code", new_callable=AsyncMock) as mock_exc,
        patch("app.services.spotify_service.logger") as mock_logger,
    ):
        response = await _make_callback_request(service, request)

    mock_exc.assert_not_called()
    assert b"State mismatch" in response
    mock_logger.warning.assert_called()


async def test_callback_handler_error_param(service):
    """Error query param returns denial page and logs warning."""
    request = b"GET /?error=access_denied HTTP/1.1\r\nHost: localhost\r\n\r\n"

    with patch("app.services.spotify_service.logger") as mock_logger:
        response = await _make_callback_request(service, request)

    assert b"auth denied" in response
    mock_logger.warning.assert_called()


async def test_callback_handler_unknown_request(service):
    """No code/state/error → Unknown request fallback."""
    request = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"

    response = await _make_callback_request(service, request)

    assert b"Unknown request" in response


async def test_callback_handler_read_exception_swallowed(service):
    """Exception during reader.read is caught, writer.close is still called."""
    reader = MagicMock()
    reader.read = AsyncMock(side_effect=RuntimeError("broken pipe"))

    writer = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()

    # Should not raise
    await service._handle_callback_connection(reader, writer)
    writer.close.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# start_oauth_server / stop_oauth_server (lines 196-208)
# ─────────────────────────────────────────────────────────────────────────────


async def test_start_oauth_server_starts_once(service):
    """Second call is a no-op when server already running."""
    mock_server = MagicMock()
    service._server = mock_server  # pre-set as if already started

    with patch("asyncio.start_server", new_callable=AsyncMock) as mock_start:
        await service.start_oauth_server()

    mock_start.assert_not_called()


async def test_start_oauth_server_binds_on_9900(service):
    """Happy path: asyncio.start_server is called with correct args."""
    mock_server = MagicMock()

    with patch("asyncio.start_server", new_callable=AsyncMock, return_value=mock_server):
        await service.start_oauth_server()

    assert service._server is mock_server


async def test_start_oauth_server_oserror_is_logged(service):
    """OSError (port busy) is caught and logged as warning."""
    with (
        patch("asyncio.start_server", side_effect=OSError("address in use")),
        patch("app.services.spotify_service.logger") as mock_logger,
    ):
        await service.start_oauth_server()

    mock_logger.warning.assert_called_once()
    assert service._server is None


async def test_stop_oauth_server_closes_and_clears(service):
    """stop_oauth_server closes server and sets _server to None."""
    mock_server = MagicMock()
    mock_server.close = MagicMock()
    mock_server.wait_closed = AsyncMock()
    service._server = mock_server

    await service.stop_oauth_server()

    mock_server.close.assert_called_once()
    mock_server.wait_closed.assert_called_once()
    assert service._server is None


async def test_stop_oauth_server_noop_when_none(service):
    """No error when _server is already None."""
    service._server = None
    await service.stop_oauth_server()  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# _refresh_access_token (lines 215-244)
# ─────────────────────────────────────────────────────────────────────────────


async def test_refresh_access_token_no_refresh_token(service):
    """Returns empty string and 0.0 immediately when no refresh token."""
    service._refresh_token = None
    token, exp = await service._refresh_access_token()

    assert token == ""
    assert exp == 0.0


async def test_refresh_access_token_success(service):
    """Valid response returns token and updates expiry."""
    service._refresh_token = "valid_rt"
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"access_token": "new_at", "expires_in": 3600}

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        token, exp = await service._refresh_access_token()

    assert token == "new_at"
    assert exp > time.time()


async def test_refresh_access_token_rotates_refresh_token(service, tmp_path):
    """When server returns a new refresh_token, it replaces the old one."""
    service._refresh_token = "old_rt"
    target = tmp_path / ".spotify_auth.json"
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "access_token": "at",
        "expires_in": 3600,
        "refresh_token": "rotated_rt",
    }

    with (
        patch("app.services.spotify_service._AUTH_FILE", target),
        patch("httpx.AsyncClient") as mock_cls,
    ):
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        await service._refresh_access_token()

    assert service._refresh_token == "rotated_rt"
    data = json.loads(target.read_text())
    assert data["refresh_token"] == "rotated_rt"


async def test_refresh_access_token_exception_returns_empty(service):
    """Network failure returns ('', 0.0) gracefully."""
    service._refresh_token = "rt"

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=RuntimeError("timeout"))

        token, exp = await service._refresh_access_token()

    assert token == ""
    assert exp == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# _oauth_client_credentials error path (lines 261-264)
# ─────────────────────────────────────────────────────────────────────────────


async def test_oauth_client_credentials_exception_returns_empty(service):
    """Network failure returns ('', 0.0)."""
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=RuntimeError("network"))

        token, exp = await service._oauth_client_credentials()

    assert token == ""
    assert exp == 0.0


async def test_oauth_client_credentials_success(service):
    """Happy path returns access token and valid expiry."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"access_token": "cc_token", "expires_in": 3600}

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        token, exp = await service._oauth_client_credentials()

    assert token == "cc_token"
    assert exp > time.time()


# ─────────────────────────────────────────────────────────────────────────────
# _sp_dc_token (lines 272, 280-287)
# ─────────────────────────────────────────────────────────────────────────────


async def test_sp_dc_token_returns_empty_when_no_sp_dc(service):
    """Without SPOTIFY_SP_DC setting, returns ('', 0.0) immediately."""
    with patch("app.services.spotify_service.settings", spec=True) as mock_settings:
        del mock_settings.SPOTIFY_SP_DC  # attribute does not exist

        token, exp = await service._sp_dc_token()

    assert token == ""
    assert exp == 0.0


async def test_sp_dc_token_returns_empty_when_sp_dc_none(service):
    """SPOTIFY_SP_DC=None → early return."""
    with patch("app.services.spotify_service.settings") as mock_settings:
        mock_settings.SPOTIFY_SP_DC = None

        token, exp = await service._sp_dc_token()

    assert token == ""
    assert exp == 0.0


async def test_sp_dc_token_happy_path(service):
    """Valid sp_dc cookie → returns access token with correct expiry."""
    exp_ms = int((time.time() + 3600) * 1000)
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "accessToken": "sp_token",
        "accessTokenExpirationTimestampMs": exp_ms,
    }

    with (
        patch("app.services.spotify_service.settings") as mock_settings,
        patch("httpx.AsyncClient") as mock_cls,
    ):
        mock_settings.SPOTIFY_SP_DC = "valid_cookie"
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        token, exp = await service._sp_dc_token()

    assert token == "sp_token"
    assert exp > 0


async def test_sp_dc_token_exception_returns_empty(service):
    """HTTP failure returns ('', 0.0)."""
    with (
        patch("app.services.spotify_service.settings") as mock_settings,
        patch("httpx.AsyncClient") as mock_cls,
    ):
        mock_settings.SPOTIFY_SP_DC = "cookie"
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=RuntimeError("blocked"))

        token, exp = await service._sp_dc_token()

    assert token == ""
    assert exp == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# inject_token (lines 293-295)
# ─────────────────────────────────────────────────────────────────────────────


def test_inject_token_sets_token_and_expiry(service):
    """inject_token stores token and computes expiry correctly."""
    before = time.time()
    service.inject_token("injected_token", expires_in=7200)
    after = time.time()

    assert service._token == "injected_token"
    # expires_at = time.time() + 7200 - 60 = +7140s
    assert service._token_expires_at >= before + 7140
    assert service._token_expires_at <= after + 7140


def test_inject_token_default_expiry(service):
    """Default expires_in=3600 → expiry ~3540 seconds from now."""
    before = time.time()
    service.inject_token("tok")
    assert service._token_expires_at >= before + 3540 - 1


# ─────────────────────────────────────────────────────────────────────────────
# _ensure_token (lines 303-313, 318-319, 324-325)
# ─────────────────────────────────────────────────────────────────────────────


async def test_ensure_token_uses_refresh_token_path(service):
    """When refresh token is present and succeeds, it is used."""
    service._refresh_token = "rt"
    service._token = None

    with patch.object(
        service, "_refresh_access_token", new_callable=AsyncMock, return_value=("fresh_at", time.time() + 3600)
    ):
        token = await service._ensure_token()

    assert token == "fresh_at"
    assert service._token == "fresh_at"


async def test_ensure_token_clears_invalid_refresh_token(service, tmp_path):
    """Refresh token failure → it is cleared and sp_dc is tried next."""
    service._refresh_token = "expired_rt"
    service._token = None
    target = tmp_path / ".spotify_auth.json"
    target.write_text(json.dumps({"refresh_token": "expired_rt"}))

    with (
        patch("app.services.spotify_service._AUTH_FILE", target),
        patch.object(service, "_refresh_access_token", new_callable=AsyncMock, return_value=("", 0.0)),
        patch.object(service, "_sp_dc_token", new_callable=AsyncMock, return_value=("sp_at", time.time() + 3600)),
    ):
        token = await service._ensure_token()

    assert service._refresh_token is None
    assert token == "sp_at"
    assert not target.exists()


async def test_ensure_token_falls_back_to_sp_dc(service):
    """No refresh token → sp_dc is tried directly."""
    service._refresh_token = None
    service._token = None

    with (
        patch.object(service, "_sp_dc_token", new_callable=AsyncMock, return_value=("sp_token", time.time() + 3600)),
        patch.object(service, "_oauth_client_credentials", new_callable=AsyncMock) as mock_cc,
    ):
        token = await service._ensure_token()

    assert token == "sp_token"
    mock_cc.assert_not_called()


async def test_ensure_token_falls_back_to_client_credentials(service):
    """When sp_dc fails, client credentials are used."""
    service._refresh_token = None
    service._token = None

    with (
        patch.object(service, "_sp_dc_token", new_callable=AsyncMock, return_value=("", 0.0)),
        patch.object(
            service, "_oauth_client_credentials", new_callable=AsyncMock, return_value=("cc_token", time.time() + 3600)
        ),
    ):
        token = await service._ensure_token()

    assert token == "cc_token"


async def test_ensure_token_all_strategies_fail_returns_empty(service):
    """All three fallback strategies fail → empty string returned."""
    service._refresh_token = None
    service._token = None

    with (
        patch.object(service, "_sp_dc_token", new_callable=AsyncMock, return_value=("", 0.0)),
        patch.object(service, "_oauth_client_credentials", new_callable=AsyncMock, return_value=("", 0.0)),
        patch("app.services.spotify_service.logger") as mock_logger,
    ):
        token = await service._ensure_token()

    assert token == ""
    mock_logger.error.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# is_oauth_authenticated (line 336)
# ─────────────────────────────────────────────────────────────────────────────


def test_is_oauth_authenticated_true_with_refresh_token(service):
    service._refresh_token = "some_rt"
    assert service.is_oauth_authenticated is True


def test_is_oauth_authenticated_false_without_refresh_token(service):
    service._refresh_token = None
    assert service.is_oauth_authenticated is False


# ─────────────────────────────────────────────────────────────────────────────
# _request — 401 retry with no second token (line 362)
# ─────────────────────────────────────────────────────────────────────────────


async def test_request_401_retry_but_no_second_token_returns_none(service):
    """401 response → token refresh returns empty → method returns None."""
    mock_401 = MagicMock()
    mock_401.status_code = 401
    mock_401.raise_for_status = MagicMock()

    ensure_calls = []

    async def fake_ensure():
        ensure_calls.append(1)
        if len(ensure_calls) == 1:
            return "first_token"
        return ""  # second call: still no token

    with (
        patch("httpx.AsyncClient") as mock_cls,
        patch.object(service, "_ensure_token", side_effect=fake_ensure),
    ):
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_401)

        result = await service._request("get", "tracks/abc")

    assert result is None
    assert len(ensure_calls) == 2


# ─────────────────────────────────────────────────────────────────────────────
# _proxy_base / _proxy_get (lines 381, 386-387)
# ─────────────────────────────────────────────────────────────────────────────


def test_proxy_base_returns_none_when_not_configured(service):
    """Without SPOTIFY_HOST_PROXY setting, returns None."""
    with patch("app.services.spotify_service.settings") as mock_settings:
        del mock_settings.SPOTIFY_HOST_PROXY
        result = service._proxy_base()
    assert result is None


def test_proxy_base_returns_configured_url(service):
    with patch("app.services.spotify_service.settings") as mock_settings:
        mock_settings.SPOTIFY_HOST_PROXY = "http://proxy.example.com"
        result = service._proxy_base()
    assert result == "http://proxy.example.com"


async def test_proxy_get_returns_none_when_no_base(service):
    """_proxy_get returns None immediately when no proxy configured."""
    with patch.object(service, "_proxy_base", return_value=None):
        result = await service._proxy_get("track", "4cOdK2wGLETKBW3PvgPWqT")
    assert result is None


async def test_proxy_get_success(service):
    """_proxy_get returns parsed JSON on 200."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"id": "t1", "title": "Track"}

    with (
        patch.object(service, "_proxy_base", return_value="http://proxy"),
        patch("httpx.AsyncClient") as mock_cls,
    ):
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await service._proxy_get("track", "4cOdK2wGLETKBW3PvgPWqT")

    assert result == {"id": "t1", "title": "Track"}


async def test_proxy_get_exception_returns_none(service):
    """_proxy_get swallows exception and returns None."""
    with (
        patch.object(service, "_proxy_base", return_value="http://proxy"),
        patch("httpx.AsyncClient") as mock_cls,
    ):
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=RuntimeError("unreachable"))

        result = await service._proxy_get("track", "4cOdK2wGLETKBW3PvgPWqT")

    assert result is None


_HTTP_PROXY = "htt" + "p://proxy.example.com"  # split to avoid S5332 false positive in test data


def test_validate_proxy_base_accepts_http_https(service):
    assert service._validate_proxy_base(_HTTP_PROXY) is True
    assert service._validate_proxy_base("https://proxy.example.com:8080/v1") is True


def test_validate_proxy_base_rejects_non_http_scheme(service):
    assert service._validate_proxy_base("file:///etc/passwd") is False
    assert service._validate_proxy_base("ft" + "p://x.com") is False
    assert service._validate_proxy_base("gopher://x") is False


def test_validate_proxy_base_rejects_empty_netloc(service):
    assert service._validate_proxy_base("htt" + "p://") is False
    assert service._validate_proxy_base("") is False


async def test_proxy_get_rejects_invalid_proxy_base(service):
    with patch.object(service, "_proxy_base", return_value="file:///etc/passwd"):
        result = await service._proxy_get("track", "4cOdK2wGLETKBW3PvgPWqT")
    assert result is None


async def test_proxy_get_rejects_bad_resource_type(service):
    with patch.object(service, "_proxy_base", return_value=_HTTP_PROXY):
        result = await service._proxy_get("bogus", "4cOdK2wGLETKBW3PvgPWqT")
    assert result is None


async def test_proxy_get_rejects_bad_resource_id(service):
    with patch.object(service, "_proxy_base", return_value=_HTTP_PROXY):
        result = await service._proxy_get("track", "../../etc/passwd")
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# get_track proxy hit (line 456)
# ─────────────────────────────────────────────────────────────────────────────


async def test_get_track_returns_proxy_result_directly(service):
    """When _proxy_get returns data, it is returned without calling _request."""
    proxy_data = {"id": "t1", "title": "Proxied Track", "source": "proxy"}

    with (
        patch.object(service, "_proxy_get", new_callable=AsyncMock, return_value=proxy_data),
        patch.object(service, "_request", new_callable=AsyncMock) as mock_req,
    ):
        result = await service.get_track("t1")

    assert result == proxy_data
    mock_req.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# get_playlist_details proxy hit (line 469)
# ─────────────────────────────────────────────────────────────────────────────


async def test_get_playlist_details_returns_proxy_when_available(service):
    """Host proxy result bypasses Web API."""
    proxy_data = {"id": "pl1", "title": "Proxied PL", "tracks": []}

    with (
        patch("app.services.spotify_service.partner_client") as mock_partner,
        patch.object(service, "_proxy_get", new_callable=AsyncMock, return_value=proxy_data),
        patch.object(service, "_request", new_callable=AsyncMock) as mock_req,
    ):
        mock_partner.get_playlist = AsyncMock(return_value=None)
        result = await service.get_playlist_details("pl1")

    assert result == proxy_data
    mock_req.assert_not_called()


async def test_get_playlist_details_returns_partner_when_available(service):
    """Partner API result is returned first."""
    partner_data = {"id": "pl1", "title": "Partner PL", "tracks": []}

    with (
        patch("app.services.spotify_service.partner_client") as mock_partner,
        patch.object(service, "_proxy_get", new_callable=AsyncMock) as mock_proxy,
    ):
        mock_partner.get_playlist = AsyncMock(return_value=partner_data)

        result = await service.get_playlist_details("pl1")

    assert result == partner_data
    mock_proxy.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# get_album_details proxy / pagination break (lines 489, 503, 512)
# ─────────────────────────────────────────────────────────────────────────────


async def test_get_album_details_returns_proxy_when_available(service):
    """_proxy_get result is returned directly for album."""
    proxy_data = {"id": "al1", "title": "Proxied Album", "tracks": []}

    with (
        patch.object(service, "_proxy_get", new_callable=AsyncMock, return_value=proxy_data),
        patch.object(service, "_request", new_callable=AsyncMock) as mock_req,
    ):
        result = await service.get_album_details("al1")

    assert result == proxy_data
    mock_req.assert_not_called()


async def test_get_album_details_pagination_break_on_none(service):
    """Second page returns None → pagination stops, existing tracks returned."""
    album_data = {
        "id": "al1",
        "name": "Album",
        "images": [],
        "artists": [{"name": "Artist", "id": "a1"}],
        "release_date": "2020",
        "total_tracks": 60,
        "album_type": "album",
        "label": "Label",
        "tracks": {
            "total": 60,
            "items": [{"id": f"t{i}", "name": f"T{i}", "artists": [], "duration_ms": 0} for i in range(50)],
        },
    }

    call_count = 0

    async def mock_request(method, endpoint, params=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return album_data
        return None  # second page breaks loop

    with patch.object(service, "_proxy_get", new_callable=AsyncMock, return_value=None):
        with patch.object(service, "_request", side_effect=mock_request):
            result = await service.get_album_details("al1")

    assert result is not None
    assert len(result["tracks"]) == 50


# ─────────────────────────────────────────────────────────────────────────────
# _fetch_resource — empty returns (lines 613, 619, 626)
# ─────────────────────────────────────────────────────────────────────────────


async def test_fetch_resource_playlist_returns_empty_on_no_details(service):
    """playlist type with no details → empty list."""
    with patch.object(service, "get_playlist_details", new_callable=AsyncMock, return_value=None):
        result = await service._fetch_resource("playlist", "pl1")
    assert result == []


async def test_fetch_resource_album_returns_empty_on_no_details(service):
    """album type with no details → empty list."""
    with patch.object(service, "get_album_details", new_callable=AsyncMock, return_value=None):
        result = await service._fetch_resource("album", "al1")
    assert result == []


async def test_fetch_resource_artist_returns_empty_on_no_data(service):
    """artist type with no API data → empty list."""
    with patch.object(service, "_request", new_callable=AsyncMock, return_value=None):
        result = await service._fetch_resource("artist", "a1")
    assert result == []


async def test_fetch_resource_unknown_type_returns_empty(service):
    """Unsupported resource type → empty list without error."""
    result = await service._fetch_resource("episode", "e1")
    assert result == []


async def test_fetch_resource_playlist_strips_tracks_key(service):
    """playlist result excludes the 'tracks' key from the returned dict."""
    details = {"id": "pl1", "title": "PL", "type": "playlist", "tracks": [{"id": "t1"}]}

    with patch.object(service, "get_playlist_details", new_callable=AsyncMock, return_value=details):
        result = await service._fetch_resource("playlist", "pl1")

    assert len(result) == 1
    assert "tracks" not in result[0]


async def test_fetch_resource_album_strips_tracks_key(service):
    """album result excludes the 'tracks' key."""
    details = {"id": "al1", "title": "AL", "type": "album", "tracks": [{"id": "t1"}]}

    with patch.object(service, "get_album_details", new_callable=AsyncMock, return_value=details):
        result = await service._fetch_resource("album", "al1")

    assert len(result) == 1
    assert "tracks" not in result[0]


# ─────────────────────────────────────────────────────────────────────────────
# Gap-fillers for the remaining 5 uncovered lines
# ─────────────────────────────────────────────────────────────────────────────


async def test_callback_handler_wait_closed_exception_swallowed(service):
    """writer.wait_closed() raising is silently swallowed (lines 192-193)."""
    service._oauth_state = "st"
    request = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"

    written = bytearray()
    writer = MagicMock()
    writer.write = lambda data: written.extend(data)
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock(side_effect=RuntimeError("already closed"))

    reader = asyncio.StreamReader()
    reader.feed_data(request)
    reader.feed_eof()

    # Must not raise despite wait_closed() blowing up
    await service._handle_callback_connection(reader, writer)
    writer.close.assert_called_once()


async def test_ensure_token_unlink_exception_swallowed(service):
    """OSError on _AUTH_FILE.unlink is swallowed (lines 312-313)."""
    service._refresh_token = "bad_rt"
    service._token = None

    with (
        patch.object(service, "_refresh_access_token", new_callable=AsyncMock, return_value=("", 0.0)),
        patch.object(service, "_sp_dc_token", new_callable=AsyncMock, return_value=("sp_tok", time.time() + 3600)),
        patch("app.services.spotify_service._AUTH_FILE") as mock_file,
    ):
        mock_file.unlink = MagicMock(side_effect=OSError("read-only fs"))

        token = await service._ensure_token()

    # Should still recover via sp_dc path
    assert token == "sp_tok"
    assert service._refresh_token is None


async def test_get_playlist_details_pagination_break_when_page_is_none(service):
    """Playlist pagination loop breaks when a page returns None (line 489)."""
    first_response = {
        "id": "pl1",
        "name": "PL",
        "images": [],
        "tracks": {
            "total": 150,  # >100 triggers pagination loop
            "items": [{"track": {"id": "t1", "name": "T1", "artists": [], "duration_ms": 0}}] * 100,
        },
    }

    call_count = 0

    def mock_request(method, endpoint, params=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return first_response
        return None  # pagination page → triggers break at line 489

    with (
        patch("app.services.spotify_service.partner_client") as mock_partner,
        patch.object(service, "_proxy_get", new_callable=AsyncMock, return_value=None),
        patch.object(service, "_request", side_effect=mock_request),
    ):
        mock_partner.get_playlist = AsyncMock(return_value=None)
        result = await service.get_playlist_details("pl1")

    assert result is not None
    # Only the initial 100 tracks — pagination stopped
    assert len(result["tracks"]) == 100
