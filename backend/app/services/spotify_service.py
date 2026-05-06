"""
Spotify metadata service.

Token strategy (priority order):
1. In-memory token (still valid) — fastest path.
2. Saved refresh token → auto-refresh via accounts.spotify.com/api/token.
   Works from any IP including Docker/VPS. Persisted to /downloads/.spotify_auth.json.
3. sp_dc cookie → get_access_token endpoint. Works from residential IPs,
   blocked from Docker/VPS IPs.
4. Client Credentials OAuth — works from any IP but Spotify blocks playlist
   endpoints since May 2024 (returns 429).

OAuth setup (one-time):
  Visit /api/v1/spotify/oauth/start in the browser.
  Spotify redirects back to http://127.0.0.1:9900/ (registered in the embedded app).
  The callback server saves the refresh token — all future calls use it silently.

Credentials: spotDL's publicly embedded client_id/secret (MIT-licensed, open-source).
Override with SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in .env for your own app.
"""

import asyncio
import base64
import json
import logging
import re
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from app.core.config import settings
from app.services.spotify_partner import partner_client  # noqa: E402

logger = logging.getLogger(__name__)

# spotDL's publicly embedded credentials — Authorization Code redirect registered
# to http://127.0.0.1:9900/ in their Spotify developer app (MIT-licensed project).
_FALLBACK_CLIENT_ID = "5f573c9620494bae87890c0f08a60293"  # noqa: S105  # nosemgrep  # ggignore — public spotDL MIT credentials
_FALLBACK_CLIENT_SECRET = "212476d9b0f3472eaa762d90b19b0ba8"  # noqa: S105  # nosemgrep  # ggignore — public spotDL MIT credentials

_REDIRECT_URI = "http://127.0.0.1:9900/"
_SCOPE = "playlist-read-private playlist-read-collaborative"
_AUTH_FILE = Path("/downloads/.spotify_auth.json")
_TOKEN_URL = "https://accounts.spotify.com/api/token"  # noqa: S105,S1192
_FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"  # noqa: S1192

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}


class SpotifyService:
    def __init__(self):
        self._token: str | None = None
        self._token_expires_at: float = 0
        self._refresh_token: str | None = None
        self._oauth_state: str = ""
        self._server: asyncio.AbstractServer | None = None
        self._load_refresh_token()

    # ------------------------------------------------------------------ #
    # Credential helpers                                                   #
    # ------------------------------------------------------------------ #

    def _client_id(self) -> str:
        return settings.SPOTIFY_CLIENT_ID or _FALLBACK_CLIENT_ID  # type: ignore[attr-defined]

    def _client_secret(self) -> str:
        return settings.SPOTIFY_CLIENT_SECRET or _FALLBACK_CLIENT_SECRET  # type: ignore[attr-defined]

    def _basic_auth(self) -> str:
        return base64.b64encode(f"{self._client_id()}:{self._client_secret()}".encode()).decode()

    # ------------------------------------------------------------------ #
    # Refresh token persistence                                            #
    # ------------------------------------------------------------------ #

    def _save_refresh_token(self) -> None:
        try:
            _AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
            _AUTH_FILE.write_text(json.dumps({"refresh_token": self._refresh_token}))
        except Exception as e:
            logger.warning(f"Failed to save Spotify refresh token: {e}")

    def _load_refresh_token(self) -> None:
        try:
            if _AUTH_FILE.exists():
                data = json.loads(_AUTH_FILE.read_text())
                self._refresh_token = data.get("refresh_token") or None
                if self._refresh_token:
                    logger.info("Spotify: loaded saved refresh token from disk")
        except Exception as e:
            logger.warning(f"Failed to load Spotify refresh token: {e}")

    # ------------------------------------------------------------------ #
    # OAuth Authorization Code flow                                        #
    # ------------------------------------------------------------------ #

    def get_auth_url(self) -> str:
        self._oauth_state = secrets.token_hex(16)
        params = {
            "client_id": self._client_id(),
            "response_type": "code",
            "redirect_uri": _REDIRECT_URI,
            "scope": _SCOPE,
            "state": self._oauth_state,
        }
        return f"https://accounts.spotify.com/authorize?{urlencode(params)}"

    async def _exchange_code(self, code: str) -> None:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    _TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {self._basic_auth()}",
                        "Content-Type": _FORM_CONTENT_TYPE,
                    },
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": _REDIRECT_URI,
                    },
                    timeout=10.0,
                )
                resp.raise_for_status()
                data = resp.json()
                self._token = data.get("access_token") or None
                self._token_expires_at = time.time() + data.get("expires_in", 3600) - 60
                refresh = data.get("refresh_token") or None
                if refresh:
                    self._refresh_token = refresh
                    self._save_refresh_token()
                logger.info("Spotify OAuth complete — refresh token saved")
            except Exception as e:
                logger.error(f"Spotify code exchange failed: {e}")

    async def _handle_callback_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            data = await asyncio.wait_for(reader.read(4096), timeout=10.0)
            request = data.decode("utf-8", errors="replace")
            first_line = request.split("\r\n")[0]
            parts = first_line.split(" ")

            html = "<h1>Unknown request</h1>"
            if len(parts) >= 2:
                parsed = urlparse(parts[1])
                params = parse_qs(parsed.query)
                code = (params.get("code") or [None])[0]  # type: ignore[list-item]
                state = (params.get("state") or [None])[0]  # type: ignore[list-item]
                error = (params.get("error") or [None])[0]  # type: ignore[list-item]

                if error:
                    safe_error = str(error).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    html = f"<h1>Spotify auth denied</h1><p>{safe_error}</p>"  # nosemgrep: raw-html-format
                    logger.warning(f"Spotify OAuth denied: {error}")
                elif code and state == self._oauth_state:
                    await self._exchange_code(code)
                    html = (
                        "<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
                        "<h1>✅ Spotify Connected</h1>"
                        "<p>Audiovault can now access your Spotify playlists.</p>"
                        "<p>You can close this tab.</p>"
                        "</body></html>"
                    )
                elif code:
                    html = "<h1>State mismatch — possible CSRF</h1>"
                    logger.warning("Spotify OAuth callback: state mismatch")

            body = html.encode()
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/html; charset=utf-8\r\n"
                + f"Content-Length: {len(body)}\r\n".encode()
                + b"Connection: close\r\n\r\n"
                + body
            )
            writer.write(response)
            await writer.drain()
        except Exception as e:
            logger.debug(f"OAuth callback handler error: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # noqa: S110
                pass

    async def start_oauth_server(self) -> None:
        if self._server is not None:
            return
        try:
            self._server = await asyncio.start_server(self._handle_callback_connection, "127.0.0.1", 9900)
            logger.info("Spotify OAuth callback server listening on :9900")
        except OSError as e:
            logger.warning(f"Could not bind Spotify OAuth server on :9900: {e}")

    async def stop_oauth_server(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    # ------------------------------------------------------------------ #
    # Token acquisition                                                    #
    # ------------------------------------------------------------------ #

    async def _refresh_access_token(self) -> tuple[str, float]:
        if not self._refresh_token:
            return "", 0.0
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    _TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {self._basic_auth()}",
                        "Content-Type": _FORM_CONTENT_TYPE,
                    },
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self._refresh_token,
                    },
                    timeout=10.0,
                )
                resp.raise_for_status()
                data = resp.json()
                token = data.get("access_token") or ""
                expires_at = time.time() + data.get("expires_in", 3600) - 60
                new_refresh = data.get("refresh_token")
                if new_refresh:
                    self._refresh_token = new_refresh
                    self._save_refresh_token()
                if token:
                    logger.debug("Spotify: access token refreshed via refresh_token")
                return token, expires_at
            except Exception as e:
                logger.warning(f"Spotify token refresh failed: {e}")
                return "", 0.0

    async def _oauth_client_credentials(self) -> tuple[str, float]:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    _TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {self._basic_auth()}",
                        "Content-Type": _FORM_CONTENT_TYPE,
                    },
                    data={"grant_type": "client_credentials"},
                    timeout=10.0,
                )
                resp.raise_for_status()
                data = resp.json()
                token = data.get("access_token") or ""
                expires_at = time.time() + data.get("expires_in", 3600) - 60
                if token:
                    logger.info("Spotify: Client Credentials token obtained (limited — no playlist access)")
                return token, expires_at
            except Exception as e:
                logger.warning(f"Spotify Client Credentials failed: {e}")
                return "", 0.0

    async def _sp_dc_token(self) -> tuple[str, float]:
        sp_dc = getattr(settings, "SPOTIFY_SP_DC", None)
        if not sp_dc:
            return "", 0.0
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                resp = await client.get(
                    "https://open.spotify.com/get_access_token?reason=transport&productType=web_player",
                    headers={**_BROWSER_HEADERS, "Cookie": f"sp_dc={sp_dc}"},
                    timeout=10.0,
                )
                resp.raise_for_status()
                data = resp.json()
                token = data.get("accessToken") or ""
                exp_ms = data.get("accessTokenExpirationTimestampMs", 0)
                expires_at = (exp_ms / 1000) - 60 if exp_ms else time.time() + 3540
                if token:
                    logger.info("Spotify: sp_dc token strategy succeeded")
                return token, expires_at
            except Exception as e:
                logger.debug(f"Spotify sp_dc strategy failed (expected from Docker): {e}")
                return "", 0.0

    def inject_token(self, token: str, expires_in: int = 3600) -> None:
        self._token = token
        self._token_expires_at = time.time() + expires_in - 60
        logger.info(f"Spotify: token injected manually, valid ~{expires_in // 60}min")

    async def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token

        # 1. Refresh token → always works from any IP
        if self._refresh_token:
            token, exp = await self._refresh_access_token()
            if token:
                self._token, self._token_expires_at = token, exp
                return token
            # refresh token expired/revoked — clear it
            logger.warning("Spotify: refresh token invalid, clearing — re-authenticate via /api/v1/spotify/oauth/start")
            self._refresh_token = None
            try:
                _AUTH_FILE.unlink(missing_ok=True)
            except Exception:  # noqa: S110
                pass

        # 2. sp_dc cookie (works only from residential IPs)
        token, exp = await self._sp_dc_token()
        if token:
            self._token, self._token_expires_at = token, exp
            return token

        # 3. Client Credentials (no playlist access since May 2024)
        token, exp = await self._oauth_client_credentials()
        if token:
            self._token, self._token_expires_at = token, exp
            return token

        logger.error("All Spotify token strategies failed — visit /api/v1/spotify/oauth/start to authenticate")
        return ""

    # ------------------------------------------------------------------ #
    # Status                                                               #
    # ------------------------------------------------------------------ #

    @property
    def is_oauth_authenticated(self) -> bool:
        return bool(self._refresh_token)

    async def get_anonymous_token(self) -> str:
        """Backward-compat shim — delegates to _ensure_token."""
        return await self._ensure_token() or ""

    # ------------------------------------------------------------------ #
    # HTTP helper                                                          #
    # ------------------------------------------------------------------ #

    async def _request(self, method: str, endpoint: str, params: dict | None = None) -> dict[str, Any] | None:
        token = await self._ensure_token()
        if not token:
            return None

        url = f"https://api.spotify.com/v1/{endpoint}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        async with httpx.AsyncClient() as client:
            try:
                resp = await getattr(client, method)(url, headers=headers, params=params, timeout=10.0)
                if resp.status_code == 401:
                    self._token = None
                    self._token_expires_at = 0
                    token = await self._ensure_token()
                    if not token:
                        return None
                    headers["Authorization"] = f"Bearer {token}"
                    resp = await getattr(client, method)(url, headers=headers, params=params, timeout=10.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Spotify API [{endpoint}]: {e}")
                return None

    # ------------------------------------------------------------------ #
    # Host proxy (embed scraping via residential IP)                      #
    # ------------------------------------------------------------------ #

    def _proxy_base(self) -> str | None:
        return getattr(settings, "SPOTIFY_HOST_PROXY", None)  # type: ignore[attr-defined]

    async def _proxy_get(self, resource_type: str, resource_id: str) -> dict[str, Any] | None:
        base = self._proxy_base()
        if not base:
            return None
        url = f"{base.rstrip('/')}/{resource_type}/{resource_id}"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, timeout=15.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.debug(f"Host proxy unavailable ({url}): {e}")
                return None

    # ------------------------------------------------------------------ #
    # Formatters                                                           #
    # ------------------------------------------------------------------ #

    def _fmt_track(self, item: dict[str, Any], album_obj: dict | None = None) -> dict[str, Any]:
        album_name = "Unknown Album"
        image_url = None
        if "album" in item:
            album_name = item["album"].get("name", album_name)
            images = item["album"].get("images") or []
            image_url = images[0]["url"] if images else None
        elif album_obj:
            album_name = album_obj.get("name", album_name)
            images = album_obj.get("images") or []
            image_url = images[0]["url"] if images else None

        artists_raw = item.get("artists") or []
        artists = ", ".join(a.get("name", "") for a in artists_raw if a.get("name"))
        artist_id = artists_raw[0].get("id") if artists_raw else None

        return {
            "id": item.get("id"),
            "title": item.get("name") or item.get("title", "Unknown"),
            "artist": artists or "Unknown Artist",
            "artist_id": artist_id,
            "album": album_name,
            "duration_ms": item.get("duration_ms"),
            "image_url": image_url,
            "source": "spotify",
            "popularity": item.get("popularity", 0),
            "isrc": item.get("external_ids", {}).get("isrc"),
        }

    _format_track = _fmt_track  # noqa: E305 — backward-compat alias used by tests

    def _fmt_playlist(self, item: dict[str, Any], is_album: bool = False) -> dict[str, Any]:
        images = item.get("images") or []
        track_count = item.get("tracks", {}).get("total") if not is_album else item.get("total_tracks")
        return {
            "id": item.get("id"),
            "title": item.get("name"),
            "image_url": images[0]["url"] if images else None,
            "source": "spotify",
            "type": "album" if is_album else "playlist",
            "track_count": track_count,
        }

    def _fmt_artist(self, item: dict[str, Any]) -> dict[str, Any]:
        images = item.get("images") or []
        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "image_url": images[0]["url"] if images else None,
            "source": "spotify",
            "type": "artist",
        }

    # ------------------------------------------------------------------ #
    # Data fetchers                                                        #
    # ------------------------------------------------------------------ #

    async def get_track(self, track_id: str) -> dict[str, Any] | None:
        proxy = await self._proxy_get("track", track_id)
        if proxy:
            return proxy
        data = await self._request("get", f"tracks/{track_id}")
        return self._fmt_track(data) if data else None

    async def get_playlist_details(self, playlist_id: str) -> dict[str, Any] | None:
        # 1. Partner API — works from Docker, full pagination (no 50-track limit), no external scripts
        partner_result = await partner_client.get_playlist(playlist_id)
        if partner_result:
            return partner_result

        # 2. Host proxy — embed scraping via residential IP, limited to 50 tracks
        proxy = await self._proxy_get("playlist", playlist_id)
        if proxy:
            return proxy

        # 3. Spotify Web API — requires OAuth refresh token
        data = await self._request("get", f"playlists/{playlist_id}")
        if not data:
            return None

        formatted = self._fmt_playlist(data)
        tracks_meta = data.get("tracks", {})
        total = tracks_meta.get("total", 0)
        tracks = [self._fmt_track(i["track"]) for i in (tracks_meta.get("items") or []) if i.get("track")]

        offset = 100
        while offset < total and offset < 500:
            page = await self._request(
                "get",
                f"playlists/{playlist_id}/tracks",
                params={"limit": 50, "offset": offset},
            )
            if not page:
                break
            tracks += [self._fmt_track(i["track"]) for i in page.get("items", []) if i.get("track")]
            offset += 50

        formatted["tracks"] = tracks
        return formatted

    async def get_playlist_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        result = await self.get_playlist_details(playlist_id)
        return result.get("tracks", []) if result else []

    async def get_album_details(self, album_id: str) -> dict[str, Any] | None:
        proxy = await self._proxy_get("album", album_id)
        if proxy:
            return proxy
        data = await self._request("get", f"albums/{album_id}")
        if not data:
            return None
        tracks = [self._fmt_track(t, album_obj=data) for t in data.get("tracks", {}).get("items", [])]
        offset, total = 50, data.get("tracks", {}).get("total", 1)
        while offset < total and offset < 500:
            page = await self._request("get", f"albums/{album_id}/tracks", params={"limit": 50, "offset": offset})
            if not page:
                break
            tracks += [self._fmt_track(t, album_obj=data) for t in page.get("items", [])]
            offset += 50
        images = data.get("images") or []
        artists = data.get("artists") or []
        return {
            "id": data.get("id"),
            "title": data.get("name"),
            "artist": artists[0]["name"] if artists else "Unknown Artist",
            "artist_id": artists[0]["id"] if artists else None,
            "image_url": images[0]["url"] if images else None,
            "release_date": data.get("release_date"),
            "total_tracks": data.get("total_tracks"),
            "album_type": data.get("album_type", "album"),
            "label": data.get("label"),
            "tracks": tracks,
            "source": "spotify",
            "type": "album",
        }

    async def get_album_tracks(self, album_id: str) -> list[dict[str, Any]]:
        result = await self.get_album_details(album_id)
        return result.get("tracks", []) if result else []

    async def get_album(self, album_id: str) -> dict[str, Any] | None:
        return await self._request("get", f"albums/{album_id}")

    async def get_artist_top_tracks(self, artist_id: str) -> list[dict[str, Any]]:
        data = await self._request("get", f"artists/{artist_id}/top-tracks", params={"market": "US"})
        return [self._fmt_track(t) for t in (data or {}).get("tracks", [])]

    async def get_artist_albums(self, artist_id: str) -> list[dict[str, Any]]:
        albums: list[dict] = []
        offset, total = 0, 1
        while offset < total and offset < 200:
            data = await self._request(
                "get",
                f"artists/{artist_id}/albums",
                params={"include_groups": "album,single", "limit": 50, "offset": offset},
            )
            if not data:
                break
            total = data.get("total", 0)
            for alb in data.get("items", []):
                if alb.get("album_type") == "compilation":
                    continue
                if any(a.get("name", "").lower() == "various artists" for a in alb.get("artists", [])):
                    continue
                albums.append(alb)
            offset += 50
        return albums

    async def get_artist_details(self, artist_id: str) -> dict[str, Any] | None:
        data = await self._request("get", f"artists/{artist_id}")
        if not data:
            return None
        formatted = self._fmt_artist(data)
        formatted["tracks"] = await self.get_artist_top_tracks(artist_id)
        albums = await self.get_artist_albums(artist_id)
        seen: set[str] = set()
        formatted["albums"] = []
        for alb in albums:
            title = alb.get("name", "")
            if title in seen:
                continue
            seen.add(title)
            images = alb.get("images") or []
            formatted["albums"].append(
                {
                    "id": alb.get("id"),
                    "title": title,
                    "image_url": images[0]["url"] if images else None,
                    "release_date": alb.get("release_date"),
                    "total_tracks": alb.get("total_tracks"),
                    "type": alb.get("type"),
                    "album_type": alb.get("album_type", "album"),
                }
            )
        return formatted

    # ------------------------------------------------------------------ #
    # Search / URL resolver                                                #
    # ------------------------------------------------------------------ #

    async def _resolve_short_link(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.head(url, timeout=5)
                return str(resp.url)
        except Exception as e:
            logger.warning(f"Failed to resolve short link {url}: {e}")
            return url

    async def _fetch_resource(self, resource_type: str, resource_id: str) -> list[dict[str, Any]]:
        if resource_type == "track":
            track = await self.get_track(resource_id)
            return [track] if track else []

        if resource_type == "playlist":
            details = await self.get_playlist_details(resource_id)
            if not details:
                return []
            return [{k: v for k, v in details.items() if k != "tracks"}]

        if resource_type == "album":
            details = await self.get_album_details(resource_id)
            if not details:
                return []
            return [{k: v for k, v in details.items() if k != "tracks"}]

        if resource_type == "artist":
            data = await self._request("get", f"artists/{resource_id}")
            return [self._fmt_artist(data)] if data else []

        return []

    async def search(  # noqa: A002
        self, query: str, limit: int = 10, offset: int = 0, type: str = "track"
    ) -> list[dict[str, Any]]:
        """Returns results only for Spotify URLs — not a general search engine."""
        _ = limit, offset, type
        logger.info(f"Spotify search: {query}")

        if "spotify.link" in query or "spoti.fi" in query:
            query = await self._resolve_short_link(query)

        match = re.search(
            r"(?:https?://)?(?:www\.)?(?:open\.spotify\.com/(?:intl-\w+/)?|spotify:)"
            r"(track|artist|playlist|album)[:/]([a-zA-Z0-9_-]+)",
            query,
        )
        if match:
            resource_type, resource_id = match.groups()
            logger.info(f"Detected Spotify URL: type={resource_type}, id={resource_id}")
            try:
                return await self._fetch_resource(resource_type, resource_id)
            except Exception as e:
                logger.error(f"Spotify URL resolution failed: {e}")
                return []

        return []


# Module-level singleton — all importers share one token cache.
spotify_service = SpotifyService()
