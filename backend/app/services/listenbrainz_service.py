"""ListenBrainz HTTP client.

ListenBrainz (https://listenbrainz.org) is MetaBrainz's open scrobbling service.
Unlike Last.fm there is no application registration: each user pastes a personal
token from https://listenbrainz.org/settings/, sent as ``Authorization: Token``.

Docs: https://listenbrainz.readthedocs.io/en/latest/users/api/
"""

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.config import settings
from app.utils.log_sanitize import sanitize_log

logger = logging.getLogger(__name__)

SUBMISSION_CLIENT = "Audiovault"

# Map our coarse period names onto ListenBrainz stat ranges.
_RANGE_MAP = {
    "7day": "week",
    "1month": "month",
    "3month": "month",
    "6month": "month",
    "12month": "year",
    "week": "week",
    "month": "month",
    "year": "year",
    "all": "all_time",
    "all_time": "all_time",
}


class ListenBrainzError(Exception):
    """Any failure talking to the ListenBrainz API."""


class ListenBrainzService:
    # Class-level rate limiter (ListenBrainz allows generous but finite rates).
    _request_times: list[float] = []
    _rate_lock = asyncio.Lock()
    _MAX_PER_SECOND = 8

    def __init__(self) -> None:
        self.base_url = settings.LISTENBRAINZ_API_URL.rstrip("/")
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=15.0)

    async def close(self) -> None:
        await self.client.aclose()

    async def _rate_limit(self) -> None:
        async with ListenBrainzService._rate_lock:
            now = time.monotonic()
            ListenBrainzService._request_times = [t for t in ListenBrainzService._request_times if now - t < 1.0]
            if len(ListenBrainzService._request_times) >= self._MAX_PER_SECOND:
                await asyncio.sleep(1.0 - (now - min(ListenBrainzService._request_times)))
            ListenBrainzService._request_times.append(time.monotonic())

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Token {token}"}

    async def _get(self, path: str, token: str | None = None, params: dict[str, Any] | None = None) -> Any:
        await self._rate_limit()
        try:
            resp = await self.client.get(path, params=params, headers=self._auth(token) if token else None)
            if resp.status_code == 204:
                return None
            if resp.status_code == 429:
                raise ListenBrainzError("Rate limit exceeded")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error("ListenBrainz GET %s failed: %s", sanitize_log(path), sanitize_log(e))
            raise ListenBrainzError(f"HTTP request failed: {e}") from e

    async def _post(self, path: str, token: str, payload: dict[str, Any]) -> Any:
        await self._rate_limit()
        try:
            resp = await self.client.post(path, json=payload, headers=self._auth(token))
            if resp.status_code == 429:
                raise ListenBrainzError("Rate limit exceeded")
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except httpx.HTTPError as e:
            logger.error("ListenBrainz POST %s failed: %s", sanitize_log(path), sanitize_log(e))
            raise ListenBrainzError(f"HTTP request failed: {e}") from e

    # --- Auth ---

    async def validate_token(self, token: str) -> str:
        """Return the username the token belongs to, or raise ListenBrainzError."""
        data = await self._get("/1/validate-token", token=token)
        if not data or not data.get("valid") or not data.get("user_name"):
            raise ListenBrainzError("Invalid ListenBrainz token")
        return str(data["user_name"])

    # --- Submitting listens ---

    @staticmethod
    def _track_metadata(track: str, artist: str, album: str | None) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "artist_name": artist,
            "track_name": track,
            "additional_info": {"submission_client": SUBMISSION_CLIENT},
        }
        if album:
            meta["release_name"] = album
        return meta

    async def submit_now_playing(self, token: str, track: str, artist: str, album: str | None = None) -> None:
        payload = {
            "listen_type": "playing_now",
            "payload": [{"track_metadata": self._track_metadata(track, artist, album)}],
        }
        await self._post("/1/submit-listens", token, payload)

    async def submit_listen(
        self, token: str, track: str, artist: str, listened_at: int, album: str | None = None
    ) -> None:
        payload = {
            "listen_type": "single",
            "payload": [
                {
                    "listened_at": int(listened_at),
                    "track_metadata": self._track_metadata(track, artist, album),
                }
            ],
        }
        await self._post("/1/submit-listens", token, payload)

    # --- Reading listening history / stats ---

    def _range(self, period: str) -> str:
        return _RANGE_MAP.get(period, "month")

    async def get_top_artists(self, username: str, period: str = "1month", limit: int = 20) -> list[dict[str, Any]]:
        data = await self._get(
            f"/1/stats/user/{username}/artists",
            params={"range": self._range(period), "count": limit},
        )
        if not data:
            return []
        return [
            {"name": a.get("artist_name"), "mbid": a.get("artist_mbid"), "playcount": a.get("listen_count", 0)}
            for a in data.get("payload", {}).get("artists", [])
            if a.get("artist_name")
        ]

    async def get_top_tracks(self, username: str, period: str = "1month", limit: int = 50) -> list[dict[str, Any]]:
        data = await self._get(
            f"/1/stats/user/{username}/recordings",
            params={"range": self._range(period), "count": limit},
        )
        if not data:
            return []
        return [
            {
                "name": r.get("track_name"),
                "artist": r.get("artist_name"),
                "album": r.get("release_name"),
                "mbid": r.get("recording_mbid"),
                "playcount": r.get("listen_count", 0),
            }
            for r in data.get("payload", {}).get("recordings", [])
            if r.get("track_name") and r.get("artist_name")
        ]

    async def get_recent_tracks(self, username: str, limit: int = 50) -> list[dict[str, Any]]:
        data = await self._get(f"/1/user/{username}/listens", params={"count": limit})
        if not data:
            return []
        out = []
        for listen in data.get("payload", {}).get("listens", []):
            meta = listen.get("track_metadata", {})
            if meta.get("track_name") and meta.get("artist_name"):
                out.append(
                    {
                        "name": meta.get("track_name"),
                        "artist": meta.get("artist_name"),
                        "album": meta.get("release_name"),
                        "listened_at": listen.get("listened_at"),
                    }
                )
        return out

    async def get_recommended_recording_mbids(self, username: str, limit: int = 100) -> list[str]:
        """Recording MBIDs from ListenBrainz's precomputed recommendations.

        Names are not included — callers resolve MBIDs via MusicBrainz. Empty
        when ListenBrainz has not generated recommendations for the user yet.
        """
        data = await self._get(f"/1/user/{username}/recommendation/tracks", params={"count": limit})
        if not data:
            return []
        return [m["recording_mbid"] for m in data.get("payload", {}).get("mbids", []) if m.get("recording_mbid")]

    async def get_listen_count(self, username: str) -> int:
        data = await self._get(f"/1/user/{username}/listen-count")
        if not data:
            return 0
        return int(data.get("payload", {}).get("count", 0))

    async def get_similar_users(self, username: str, limit: int = 8) -> list[dict[str, Any]]:
        data = await self._get(f"/1/user/{username}/similar-users")
        if not data:
            return []
        rows = data.get("payload", data) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            return []
        return [
            {"name": u.get("user_name"), "similarity": u.get("similarity")} for u in rows[:limit] if u.get("user_name")
        ]

    async def get_profile(self, username: str) -> dict[str, Any]:
        count, similar = await asyncio.gather(
            self.get_listen_count(username),
            self.get_similar_users(username),
            return_exceptions=True,
        )
        return {
            "user": {
                "name": username,
                "playcount": 0 if isinstance(count, BaseException) else count,
                "url": f"https://listenbrainz.org/user/{username}/",
            },
            "similar_users": [] if isinstance(similar, BaseException) else similar,
        }
