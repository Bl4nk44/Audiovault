import asyncio
import logging
import re
import time
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Deezer enforces ~50 requests / 5s. A recommendation refresh fires dozens of
# image lookups before searching playlists, so without pacing the later calls
# get throttled and Deezer answers HTTP 200 with {"error": {"code": 4}} and an
# empty "data" list — a silent failure. This limiter spaces all Deezer requests
# to stay safely under the quota.
DEEZER_QUOTA_ERROR_CODE = 4


class _DeezerThrottle:
    """Serializes Deezer requests with a minimum interval to respect the quota."""

    def __init__(self, min_interval: float = 0.12):
        self._min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def wait(self) -> None:
        async with self._lock:
            delta = time.monotonic() - self._last
            if delta < self._min_interval:
                await asyncio.sleep(self._min_interval - delta)
            self._last = time.monotonic()


_throttle = _DeezerThrottle()


class DeezerService:
    BASE_URL = "https://api.deezer.com"
    UNKNOWN_ARTIST = "Unknown Artist"

    def __init__(self):
        """Initialize DeezerService — stateless, no configuration required."""

    async def _fetch(self, path: str, params: dict[str, Any] | None = None, retries: int = 3) -> dict[str, Any] | None:
        """GET a Deezer endpoint as JSON, pacing requests and retrying on quota errors.

        Returns the parsed body, or None on non-200 / persistent quota exhaustion.
        """
        url = f"{self.BASE_URL}{path}"
        backoff = 1.0
        for attempt in range(retries):
            await _throttle.wait()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return None
                    data = await response.json()

            error = data.get("error") if isinstance(data, dict) else None
            if error and error.get("code") == DEEZER_QUOTA_ERROR_CODE:
                logger.warning(f"Deezer quota exceeded for {path}, retry {attempt + 1}/{retries} in {backoff}s")
                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            return data

        logger.error(f"Deezer quota still exceeded after {retries} attempts for {path}")
        return None

    async def _maybe_resolve_short_link(self, query: str) -> str:
        if "page.link" in query:
            from app.utils.url_helper import resolve_redirects

            resolved = await resolve_redirects(query)
            if resolved != query:
                logger.info(f"Resolved Deezer short link to: {resolved}")
                return resolved
        return query

    async def _handle_direct_url(self, kind: str, deezer_id: str) -> list[dict[str, Any]] | None:
        if kind == "track":
            track = await self.get_track(deezer_id)
            return [track] if track else []
        if kind == "album":
            return await self.get_album_tracks(deezer_id)
        if kind == "playlist":
            return await self.get_playlist_tracks(deezer_id)
        return None

    async def search(self, query: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        query = await self._maybe_resolve_short_link(query)

        url_match = re.search(
            r"(?:https?://)?(?:www\.)?deezer\.com/(?:\w{2}/)?(track|album|playlist)/(\d+)",
            query,
        )
        if url_match:
            kind, deezer_id = url_match.groups()
            logger.info(f"Detected Deezer URL: kind={kind}, id={deezer_id}")
            result = await self._handle_direct_url(kind, deezer_id)
            if result is not None:
                return result

        data = await self._fetch("/search", params={"q": query, "limit": limit, "index": offset})
        if data is None:
            return []
        return [self._format_track(item) for item in data.get("data", [])]

    async def get_track(self, track_id: str) -> dict[str, Any] | None:
        data = await self._fetch(f"/track/{track_id}")
        if data is None or "error" in data:
            return None
        return self._format_track(data)

    async def get_album_tracks(self, album_id: str) -> list[dict[str, Any]]:
        data = await self._fetch(f"/album/{album_id}/tracks", params={"limit": 500})
        if data is None:
            return []
        # Album endpoint tracks may be simplified objects; _format_track handles what it can.
        return [self._format_track(item) for item in data.get("data", [])]

    async def get_playlist_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        data = await self._fetch(f"/playlist/{playlist_id}/tracks", params={"limit": 500})
        if data is None:
            return []
        return [self._format_track(item) for item in data.get("data", [])]

    async def get_playlist_details(self, playlist_id: str) -> dict[str, Any] | None:
        data = await self._fetch(f"/playlist/{playlist_id}")
        if data is None or "error" in data:
            return None

        tracks = []
        # Playlist details response usually contains 'tracks' -> 'data'
        if "tracks" in data and "data" in data["tracks"]:
            for item in data["tracks"]["data"]:
                tracks.append(self._format_track(item))

        return {
            "id": str(data["id"]),
            "title": data["title"],
            "description": data.get("description", ""),
            "image_url": data.get("picture_medium") or data.get("picture_big") or data.get("picture"),
            "source": "deezer",
            "author": data.get("creator", {}).get("name"),
            "tracks": tracks,
        }

    async def get_artist_details(self, artist_id: str) -> dict[str, Any] | None:
        # 1. Get Artist Info
        artist = await self._fetch(f"/artist/{artist_id}")
        if artist is None or "error" in artist:
            return None

        # 2. Get Top Tracks
        top_tracks = []
        top = await self._fetch(f"/artist/{artist_id}/top", params={"limit": 10})
        if top is not None:
            for item in top.get("data", []):
                top_tracks.append(self._format_track(item))

        # 3. Get Albums
        albums = []
        albums_data = await self._fetch(f"/artist/{artist_id}/albums", params={"limit": 20})
        if albums_data is not None:
            for item in albums_data.get("data", []):
                albums.append(
                    {
                        "id": str(item["id"]),
                        "title": item["title"],
                        "image_url": item.get("cover_medium") or item.get("cover_big"),
                        "year": str(item.get("release_date"))[:4] if item.get("release_date") else None,
                        "source": "deezer",
                    }
                )

        return {
            "id": str(artist["id"]),
            "name": artist["name"],
            "image_url": artist.get("picture_medium") or artist.get("picture_big"),
            "genres": [],  # Deezer doesn't easily expose genres in this view
            "tracks": top_tracks,
            "albums": albums,
            "source": "deezer",
        }

    async def search_playlists(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        data = await self._fetch("/search/playlist", params={"q": query, "limit": limit})
        if data is None:
            return []
        playlists = []
        for item in data.get("data", [])[:limit]:
            playlists.append(
                {
                    "id": str(item["id"]),
                    "title": item.get("title", ""),
                    "image_url": item.get("picture_medium") or item.get("picture_big") or item.get("picture"),
                    "track_count": item.get("nb_tracks", 0),
                    "url": item.get("link") or f"https://www.deezer.com/playlist/{item['id']}",
                    "source": "deezer",
                }
            )
        return playlists

    async def search_artists(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        data = await self._fetch("/search/artist", params={"q": query, "limit": limit})
        if data is None:
            return []
        artists = []
        for item in data.get("data", [])[:limit]:
            artists.append(
                {
                    "id": str(item["id"]),
                    "name": item["name"],
                    "image_url": item.get("picture_medium") or item.get("picture"),
                    "source": "deezer",
                    "type": "artist",
                }
            )
        return artists

    def _format_track(self, item: dict[str, Any]) -> dict[str, Any]:
        # Safe image extraction
        image_url = None
        album_name = "Unknown Album"

        if item.get("album"):
            album_name = item["album"].get("title", "Unknown Album")
            if item["album"].get("cover_medium"):
                image_url = item["album"]["cover_medium"]
            elif item["album"].get("cover_big"):
                image_url = item["album"]["cover_big"]
            elif item["album"].get("cover"):
                image_url = item["album"]["cover"]

        # Sometimes 'artist' is just a name string in some simplified responses?
        # Usually it is an object
        artist_name = self.UNKNOWN_ARTIST
        if isinstance(item.get("artist"), dict):
            artist_name = item["artist"].get("name", self.UNKNOWN_ARTIST)
        elif isinstance(item.get("artist"), str):
            artist_name = item.get("artist") or self.UNKNOWN_ARTIST

        return {
            "id": str(item["id"]),
            "title": item["title"],
            "artist": artist_name,
            "album": album_name,
            "duration_ms": int(item["duration"]) * 1000,
            "image_url": image_url,
            "source": "deezer",
            "popularity": item.get("rank", 0),
            "isrc": item.get("isrc"),
        }


deezer_service = DeezerService()
