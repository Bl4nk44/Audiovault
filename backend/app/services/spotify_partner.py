"""
Spotify Partner API client.

Uses Spotify's internal GraphQL endpoint (api-partner.spotify.com) with anonymous
TOTP-based authentication — no developer app, no user OAuth, no external scripts.
Works from any IP including Docker containers.

Token chain (all automatic):
  thetadev.de secrets → TOTP → open.spotify.com/api/token → access_token
  clienttoken.spotify.com → client_token
  → api-partner.spotify.com/pathfinder/v1/query (GraphQL)
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import random
import re
import struct
import time
import urllib.parse
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Rotated UA pool — pick one per session, not per-request
_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",  # noqa: E501
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

_SECRETS_PATH = b"aHR0cHM6Ly9jb2RlLnRoZXRhZGV2LmRlL1RoZXRhRGV2L3Nwb3RpZnktc2VjcmV0cy9yYXcvYnJhbmNoL21haW4vc2VjcmV0cy9zZWNyZXREaWN0Lmpzb24="  # noqa: E501
_OPEN_SPOTIFY = "https://open.spotify.com"  # noqa: S1192 — intentional single definition
_TOKEN_URL = f"{_OPEN_SPOTIFY}/api/token"
_CLIENT_TOKEN_URL = "https://clienttoken.spotify.com/v1/clienttoken"  # noqa: S105
_PARTNER_URL = "https://api-partner.spotify.com/pathfinder/v1/query"
_JSON_CT = "application/json"  # noqa: S1192

# Known stable hashes — refreshed automatically when Spotify deploys new JS
_KNOWN_HASHES: dict[str, str] = {
    "fetchPlaylist": "a65e12194ed5fc443a1cdebed5fabe33ca5b07b987185d63c72483867ad13cb4",
    "searchTracks": "59ee4a659c32e9ad894a71308207594a65ba67bb6b632b183abe97303a51fa55",
}

_CHUNK_BASE = "https://open.spotifycdn.com/cdn/build/web-player/"

# Current Spotify web-player version — updated automatically from JS discovery
_CURRENT_CLIENT_VERSIONS = [
    "1.2.90.84.gb6020db2",
    "1.2.89.434.gf8c94a14",
    "1.2.88.358.g7ab1e484",
]

_CACHE_TTL_PLAYLIST = 86400  # 24h

# Jitter range between paginated requests (ms) — mimics human/browser timing
_PAGE_JITTER_MS = (150, 600)


def _ua() -> str:
    return random.choice(_UA_POOL)  # noqa: S311


def _browser_headers(ua: str, *, origin: str = _OPEN_SPOTIFY) -> dict[str, str]:
    """Full Chrome header set — missing these is a bot signal."""
    return {
        "User-Agent": ua,
        "Origin": origin,
        "Referer": f"{origin}/",
        "Accept": _JSON_CT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "DNT": "1",
    }


def _totp(secret_b32: str) -> str:
    pad = (8 - len(secret_b32) % 8) % 8
    key = base64.b32decode(secret_b32 + "=" * pad)
    t_val = struct.pack(">Q", int(time.time()) // 30)
    h = hmac.new(key, t_val, hashlib.sha1).digest()
    offset = h[-1] & 0xF
    code = (struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return str(code).zfill(6)


def _derive_totp_secret(raw_bytes: bytearray) -> str:
    transformed = [b ^ ((i % 33) + 9) for i, b in enumerate(raw_bytes)]
    hex_str = "".join(str(x) for x in transformed).encode().hex()
    return base64.b32encode(bytes.fromhex(hex_str)).decode().rstrip("=")


async def _jitter() -> None:
    """Random sleep between paginated requests to avoid bot-pattern detection."""
    lo, hi = _PAGE_JITTER_MS
    await asyncio.sleep(random.uniform(lo, hi) / 1000)  # noqa: S311


class SpotifyPartnerClient:
    """
    Fetches Spotify metadata via the internal partner GraphQL API.
    All auth is anonymous and automatic — no configuration needed.
    """

    def __init__(self):
        self._ua: str = _ua()
        self._access_token: str = ""
        self._access_token_expires: float = 0
        self._client_token: str = ""
        self._client_token_expires: float = 0
        self._client_version: str = random.choice(_CURRENT_CLIENT_VERSIONS)  # noqa: S311
        self._client_id: str = ""
        self._totp_secret: str = ""
        self._totp_version: str = ""
        self._totp_secret_expires: float = 0
        self._graphql_hashes: dict[str, str] = dict(_KNOWN_HASHES)
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ #
    # Auth bootstrap                                                       #
    # ------------------------------------------------------------------ #

    async def _refresh_totp_secret(self) -> None:
        url = base64.b64decode(_SECRETS_PATH).decode()
        async with httpx.AsyncClient(headers={"User-Agent": self._ua}) as client:
            resp = await client.get(url, timeout=8.0)
            resp.raise_for_status()
            secrets: dict[str, list[int]] = resp.json()
        version = max(secrets, key=int)
        self._totp_secret = _derive_totp_secret(bytearray(secrets[version]))
        self._totp_version = version
        self._totp_secret_expires = time.time() + 3600

    async def _refresh_access_token(self) -> None:
        if not self._totp_secret or time.time() >= self._totp_secret_expires:
            await self._refresh_totp_secret()
        code = _totp(self._totp_secret)
        url = (
            f"{_TOKEN_URL}?reason=init&productType=web-player"
            f"&totp={code}&totpVer={self._totp_version}&totpServer={code}"
        )
        headers = {
            **_browser_headers(self._ua, origin=_OPEN_SPOTIFY),
            "Spotify-App-Version": self._client_version,
        }
        async with httpx.AsyncClient(headers=headers) as client:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
        self._access_token = data["accessToken"]
        self._client_id = data.get("clientId") or self._client_id
        exp_ms = data.get("accessTokenExpirationTimestampMs", 0)
        self._access_token_expires = (exp_ms / 1000) - 60 if exp_ms else time.time() + 3540

    async def _refresh_client_token(self) -> None:
        body = {
            "client_data": {
                "client_version": self._client_version,
                "client_id": self._client_id or "d8a5ed958d274c2e8ee7",
                "js_sdk_data": {
                    "device_brand": "unknown",
                    "device_model": "unknown",
                    "os": "windows",
                    "os_version": "NT 10.0",
                    "device_type": "computer",
                },
            }
        }
        headers = {
            **_browser_headers(self._ua, origin=_OPEN_SPOTIFY),
            "Content-Type": _JSON_CT,
            "Accept": _JSON_CT,
        }
        async with httpx.AsyncClient(headers=headers) as client:
            resp = await client.post(_CLIENT_TOKEN_URL, json=body, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
        self._client_token = data["granted_token"]["token"]
        self._client_token_expires = time.time() + 3600

    async def _ensure_auth(self) -> None:
        async with self._lock:
            if not self._access_token or time.time() >= self._access_token_expires:
                await self._refresh_access_token()
            if not self._client_token or time.time() >= self._client_token_expires:
                await self._refresh_client_token()

    # ------------------------------------------------------------------ #
    # GraphQL hash discovery                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _lazy_chunk_urls(js_text: str, operation: str) -> list[str]:
        """Resolve webpack lazy-chunk URLs whose names hint at the operation.

        Search/browse GraphQL operations live in route chunks (e.g.
        "xpui-routes-search") that are not referenced from the HTML — their
        names and content hashes sit in the main bundle's webpack chunk map.
        """
        segment_start = js_text.find(".u=e=>")
        if segment_start == -1:
            return []
        segment = js_text[segment_start : segment_start + 20000]
        objects = re.findall(r'\{(?:\d+:"[^"]*",?)+\}', segment)
        name_maps: list[dict[str, str]] = []
        hash_maps: list[dict[str, str]] = []
        for obj in objects:
            entries = dict(re.findall(r'(\d+):"([^"]+)"', obj))
            if entries and all(re.fullmatch(r"[0-9a-f]{8}", v) for v in entries.values()):
                hash_maps.append(entries)
            else:
                name_maps.append(entries)

        # Split camelCase ("searchTracks" → "search", "tracks") to match chunk names.
        tokens = [t.lower() for t in re.findall(r"[A-Z]?[a-z]+", operation) if len(t) > 3]
        urls: list[str] = []
        for names in name_maps:
            for chunk_id, name in names.items():
                if not any(t in name.lower() for t in tokens):
                    continue
                for hashes in hash_maps:
                    content_hash = hashes.get(chunk_id)
                    if content_hash:
                        url = f"{_CHUNK_BASE}{name}.{content_hash}.js"
                        if url not in urls:
                            urls.append(url)
        return urls

    async def _scan_js_urls(
        self, client: httpx.AsyncClient, urls: list[str], operation: str, *, collect_lazy: bool
    ) -> tuple[str, list[str]]:
        """Scan JS files for the operation hash; optionally collect lazy-chunk URLs."""
        # Lazy quantifier — greedy would skip past the operation's own hash
        # and capture the hash of the NEXT operation within the window.
        pattern = re.compile(rf"{re.escape(operation)}.{{0,300}}?([a-f0-9]{{64}})")
        lazy_urls: list[str] = []
        for url in urls:
            try:
                js_resp = await client.get(url, timeout=30.0)
            except Exception as e:
                logger.debug(f"JS fetch error {url}: {e}")
                continue
            m = pattern.search(js_resp.text)
            if m:
                logger.info(f"Found GraphQL hash for {operation} in {url[-60:]}")
                return m.group(1), lazy_urls
            if collect_lazy:
                lazy_urls.extend(u for u in self._lazy_chunk_urls(js_resp.text, operation) if u not in lazy_urls)
        return "", lazy_urls

    async def _find_hash_in_js(self, operation: str) -> str:
        headers = _browser_headers(self._ua, origin=_OPEN_SPOTIFY)
        # Advertise only encodings httpx can decode without extra deps —
        # with "br" the CDN sends brotli and resp.text is compressed garbage.
        headers["Accept-Encoding"] = "gzip, deflate"
        async with httpx.AsyncClient(headers=headers) as client:
            html_resp = await client.get(_OPEN_SPOTIFY, timeout=10.0)
            # Single-quantifier regex (linear time) + netloc check ensures
            # spotifycdn.com is the actual host, not an arbitrary path segment.
            js_urls = [
                url
                for url in re.findall(r'src="(https://[^"]+\.js)"', html_resp.text)
                if (h := urllib.parse.urlparse(url).netloc) == "spotifycdn.com" or h.endswith(".spotifycdn.com")
            ]
            found, lazy_urls = await self._scan_js_urls(client, js_urls, operation, collect_lazy=True)
            if found:
                return found
            found, _ = await self._scan_js_urls(client, lazy_urls, operation, collect_lazy=False)
            return found

    async def _get_hash(self, operation: str) -> str:
        if operation not in self._graphql_hashes:
            h = await self._find_hash_in_js(operation)
            self._graphql_hashes[operation] = h or ""
        return self._graphql_hashes[operation]

    # ------------------------------------------------------------------ #
    # GraphQL request                                                      #
    # ------------------------------------------------------------------ #

    async def _query(self, operation: str, variables: dict[str, Any], _retry: bool = True) -> dict | None:
        await self._ensure_auth()
        sha256_hash = await self._get_hash(operation)
        if not sha256_hash:
            logger.warning(f"No GraphQL hash for {operation}")
            return None

        params = {
            "operationName": operation,
            "variables": json.dumps(variables),
            "extensions": json.dumps({"persistedQuery": {"version": 1, "sha256Hash": sha256_hash}}),
        }
        headers = {
            **_browser_headers(self._ua, origin=_OPEN_SPOTIFY),
            "Authorization": f"Bearer {self._access_token}",
            "Client-Token": self._client_token,
            "Spotify-App-Version": self._client_version,
            "App-Platform": "WebPlayer",
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(_PARTNER_URL, params=params, headers=headers, timeout=15.0)
            except Exception as e:
                logger.error(f"Partner API request failed: {e}")
                return None

        if resp.status_code == 400 and _retry:
            errors = resp.json().get("errors", [])
            msgs = " ".join(e.get("message", "") for e in errors)
            if "sha256Hash" in msgs or "persistedQuery" in msgs or "hash" in msgs.lower():
                logger.info(f"Stale GraphQL hash for {operation}, re-fetching from JS...")
                self._graphql_hashes.pop(operation, None)
                h = await self._find_hash_in_js(operation)
                if h:
                    self._graphql_hashes[operation] = h
                    return await self._query(operation, variables, _retry=False)
            logger.warning(f"Partner API 400 for {operation}: {msgs}")
            return None

        if resp.status_code == 401:
            self._access_token = ""
            self._access_token_expires = 0
            logger.warning("Partner API 401 — access token expired")
            return None

        try:
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Partner API error [{operation}]: {e}")
            return None

    # ------------------------------------------------------------------ #
    # Data formatters                                                      #
    # ------------------------------------------------------------------ #

    def _fmt_track_from_item(self, item: dict) -> dict[str, Any] | None:
        # Playlist payloads wrap tracks in "itemV2", search payloads in "item".
        wrapper = item.get("itemV2") or item.get("item") or {}
        if wrapper.get("__typename") != "TrackResponseWrapper":
            return None
        t = wrapper.get("data") or {}
        if not t:
            return None

        uri = t.get("uri", "")
        track_id = uri.split(":")[-1]

        artists_items = (t.get("artists") or {}).get("items") or []
        artist_names = ", ".join(a["profile"]["name"] for a in artists_items if (a.get("profile") or {}).get("name"))
        artist_id = artists_items[0].get("uri", "").split(":")[-1] if artists_items else None

        album = t.get("albumOfTrack") or {}
        album_name = album.get("name")
        covers = (album.get("coverArt") or {}).get("sources") or []
        image_url = max(covers, key=lambda s: s.get("width") or 0, default={}).get("url")  # type: ignore[call-overload]

        duration_ms = (t.get("trackDuration") or {}).get("totalMilliseconds")

        return {
            "id": track_id,
            "title": t.get("name") or "Unknown",
            "artist": artist_names or "Unknown Artist",
            "artist_id": artist_id,
            "album": album_name,
            "duration_ms": duration_ms,
            "image_url": image_url,
            "source": "spotify",
            "popularity": 0,
            "isrc": None,
        }

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def _tracks_from_content(self, content: dict[str, Any]) -> list[dict]:
        """Map raw GraphQL playlist items to formatted track dicts."""
        tracks: list[dict] = []
        for item in content.get("items") or []:
            t = self._fmt_track_from_item(item)
            if t:
                tracks.append(t)
        return tracks

    async def _paginate_tracks(self, variables: dict[str, Any], batch: int, total: int) -> list[dict]:
        """Fetch remaining playlist pages after the first batch."""
        tracks: list[dict] = []
        offset = batch
        while offset < total:
            await _jitter()
            page_data = await self._query("fetchPlaylist", {**variables, "offset": offset})
            if not page_data:
                break
            content = (page_data.get("data") or {}).get("playlistV2", {}).get("content", {})
            tracks.extend(self._tracks_from_content(content))
            offset += batch
        return tracks

    @staticmethod
    def _first_image_url(pl: dict[str, Any]) -> str | None:
        images = (pl.get("images") or {}).get("items") or []
        if not images:
            return None
        sources = images[0].get("sources") or []
        return sources[0].get("url") if sources else None

    async def _cache_get_playlist(self, cache_key: str) -> dict[str, Any] | None:
        from app.core.cache import cache_manager

        try:
            cached = await cache_manager.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
        return None

    async def _cache_set_playlist(self, cache_key: str, result: dict[str, Any]) -> None:
        from app.core.cache import cache_manager

        try:
            await cache_manager.set(cache_key, json.dumps(result), expire=_CACHE_TTL_PLAYLIST)
        except Exception as e:
            logger.debug(f"Cache write error: {e}")

    async def get_playlist(self, playlist_id: str) -> dict[str, Any] | None:
        cache_key = f"sp:pl:{playlist_id}"
        cached = await self._cache_get_playlist(cache_key)
        if cached is not None:
            logger.debug(f"Spotify playlist {playlist_id} served from cache")
            return cached

        batch = 343
        variables: dict[str, Any] = {
            "uri": f"spotify:playlist:{playlist_id}",
            "offset": 0,
            "limit": batch,
            "enableWatchFeedEntrypoint": False,
        }

        data = await self._query("fetchPlaylist", variables)
        if not data:
            return None

        pl = (data.get("data") or {}).get("playlistV2")
        if not pl:
            return None

        content = pl.get("content") or {}
        total = content.get("totalCount") or 0
        tracks = self._tracks_from_content(content)
        tracks.extend(await self._paginate_tracks(variables, batch, total))

        result = {
            "id": playlist_id,
            "title": pl.get("name"),
            "image_url": self._first_image_url(pl),
            "source": "spotify",
            "type": "playlist",
            "track_count": total,
            "tracks": tracks,
        }

        await self._cache_set_playlist(cache_key, result)
        return result

    async def search_tracks(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Text track search via the web-player GraphQL endpoint.

        No official API credentials needed — same anonymous auth chain as
        playlist fetching. The persisted-query hash for "searchTracks" is
        discovered from the web-player JS on first use.
        """
        # Exact variable shape the web player sends for searchTracks —
        # persisted queries reject unexpected/missing variables.
        variables: dict[str, Any] = {
            "searchTerm": query,
            "offset": 0,
            "limit": limit,
            "includeEpisodeContentRatingsV2": False,
        }
        data = await self._query("searchTracks", variables)
        if not data:
            return []

        items = ((((data.get("data") or {}).get("searchV2") or {}).get("tracksV2") or {}).get("items")) or []
        tracks: list[dict[str, Any]] = []
        for item in items:
            t = self._fmt_track_from_item(item)
            if t:
                tracks.append(t)
        return tracks

    async def invalidate_playlist_cache(self, playlist_id: str) -> None:
        from app.core.cache import cache_manager

        try:
            await cache_manager.delete(f"sp:pl:{playlist_id}")
        except Exception:  # noqa: S110
            pass


# Module-level singleton shared across all callers.
partner_client = SpotifyPartnerClient()
