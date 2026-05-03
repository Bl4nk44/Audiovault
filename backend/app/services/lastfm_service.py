import asyncio
import hashlib
import logging
import time
from collections.abc import Coroutine
from typing import Any, cast

import httpx
from app.core.config import settings
from app.schemas.recommendation import RecommendedArtist, RecommendedTrack

logger = logging.getLogger(__name__)

# Rate limiter constants
MAX_REQUESTS_PER_SECOND = 5
RATE_WINDOW_SECONDS = 1.0


class LastfmError(Exception):
    pass


class LastfmAPIError(LastfmError):
    pass


class LastfmRateLimitError(LastfmAPIError):
    pass


LASTFM_TEXT_KEY = "#text"


class LastfmService:
    BASE_URL = "http://ws.audioscrobbler.com/2.0/"

    # Class-level rate limiter (shared across instances)
    _request_times: list = []
    _rate_lock = asyncio.Lock()

    def __init__(self):
        self.client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=10.0)

    async def close(self):
        await self.client.aclose()

    async def _rate_limit(self):
        """Enforce rate limiting: max 5 requests per second."""
        async with LastfmService._rate_lock:
            now = time.monotonic()
            # Remove timestamps older than 1 second
            LastfmService._request_times = [t for t in LastfmService._request_times if now - t < RATE_WINDOW_SECONDS]

            if len(LastfmService._request_times) >= MAX_REQUESTS_PER_SECOND:
                # Calculate wait time until oldest request expires
                oldest = min(LastfmService._request_times)
                wait_time = RATE_WINDOW_SECONDS - (now - oldest)
                if wait_time > 0:
                    logger.debug(f"Rate limiting: waiting {wait_time:.3f}s")
                    await asyncio.sleep(wait_time)

            # Record this request
            LastfmService._request_times.append(time.monotonic())

    def _sign_params(self, params: dict[str, Any]) -> str:
        """Calculate api_sig for Last.fm API."""
        sig_params = {k: v for k, v in params.items() if k not in ("format", "callback")}
        sorted_params = sorted(sig_params.items())
        sig_str = "".join(f"{k}{v}" for k, v in sorted_params)
        sig_str += str(settings.LASTFM_API_SECRET or "")
        # nosemgrep: python.lang.security.audit.md5-used-as-password.md5-used-as-password, md5-used-as-password
        return hashlib.md5(sig_str.encode("utf-8")).hexdigest()  # nosec B324

    async def _request(self, method: str, params: dict[str, Any], signed: bool = False) -> dict[str, Any]:
        # Apply rate limiting before each request
        await self._rate_limit()

        params["method"] = method
        params["api_key"] = settings.LASTFM_API_KEY

        if signed:
            params["api_sig"] = self._sign_params(params)

        params["format"] = "json"

        try:
            response = await self.client.get("/", params=params)

            if response.status_code == 429:
                raise LastfmRateLimitError("Rate limit exceeded")

            response.raise_for_status()
            data = response.json()

            logger.debug(f"Last.fm response for {method}: {data}")

            if "error" in data:
                raise LastfmAPIError(f"Last.fm API Error {data['error']}: {data.get('message', 'Unknown error')}")

            return data
        except httpx.HTTPError as e:
            logger.error(f"Last.fm request failed: {e}")
            raise LastfmAPIError(f"HTTP request failed: {str(e)}")

    def get_auth_url(self, base_url: str | None = None) -> str:
        if base_url:
            callback_base = base_url.rstrip("/")
        else:
            # Fallback to first CORS origin
            origins = list(settings.BACKEND_CORS_ORIGINS)
            callback_base = origins[0] if origins else "http://localhost:3000"
        callback_url = f"{callback_base}/recommendations"
        return f"http://www.last.fm/api/auth/?api_key={settings.LASTFM_API_KEY}&cb={callback_url}"

    async def get_session(self, token: str) -> dict[str, Any]:
        """Exchange token for session."""
        # Note: _request adds api_key
        # We just pass additional params.
        params = {"token": token}
        data = await self._request("auth.getSession", params, signed=True)
        return data.get("session", {})

    async def get_user_top_artists(self, user: str, period: str = "1month", limit: int = 20) -> list[dict[str, Any]]:
        data = await self._request("user.getTopArtists", {"user": user, "period": period, "limit": limit})
        return data.get("topartists", {}).get("artist", [])

    async def get_user_top_tracks(self, user: str, period: str = "1month", limit: int = 50) -> list[dict[str, Any]]:
        data = await self._request("user.getTopTracks", {"user": user, "period": period, "limit": limit})
        return data.get("toptracks", {}).get("track", [])

    async def get_user_info(self, user: str) -> dict[str, Any]:
        """Get user profile information (scrobbles, registration date, etc.)."""
        data = await self._request("user.getInfo", {"user": user})
        user_data = data.get("user", {})
        return {
            "name": user_data.get("name", ""),
            "realname": user_data.get("realname", ""),
            "url": user_data.get("url", ""),
            "country": user_data.get("country", ""),
            "age": user_data.get("age", 0),
            "playcount": int(user_data.get("playcount", 0)),
            "artist_count": int(user_data.get("artist_count", 0)),
            "track_count": int(user_data.get("track_count", 0)),
            "album_count": int(user_data.get("album_count", 0)),
            "image_url": self._extract_best_image(user_data.get("image", [])),
            "registered": user_data.get("registered", {}).get("unixtime", 0),
            "subscriber": user_data.get("subscriber", "0") == "1",
        }

    async def get_user_friends(self, user: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get user's friends list."""
        data = await self._request("user.getFriends", {"user": user, "limit": limit})
        friends_data = data.get("friends", {}).get("user", [])
        if isinstance(friends_data, dict):
            friends_data = [friends_data]

        return [
            {
                "name": f.get("name", ""),
                "realname": f.get("realname", ""),
                "url": f.get("url", ""),
                "country": f.get("country", ""),
                "image_url": self._extract_best_image(f.get("image", [])),
            }
            for f in friends_data
        ]

    async def get_user_recent_tracks(self, user: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent tracks for a user."""
        data = await self._request(
            "user.getRecentTracks",
            {
                "user": user,
                "limit": limit,
                "extended": 1,  # Use extended=1 to get more metadata
            },
        )
        return data.get("recenttracks", {}).get("track", [])

    async def get_user_top_tags(self, user: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get top tags for a user."""
        data = await self._request("user.getTopTags", {"user": user, "limit": limit})
        return data.get("toptags", {}).get("tag", [])

    async def get_artist_top_tags(self, artist: str, limit: int = 5) -> list[str]:
        """Get top tags for an artist."""
        try:
            data = await self._request("artist.getTopTags", {"artist": artist})
            tags = data.get("toptags", {}).get("tag", [])
            return [t.get("name") for t in tags[:limit] if t.get("name")]
        except Exception:
            return []

    async def _fetch_raw_artists_authenticated(self, session_key: str, limit: int) -> list:
        try:
            data = await self._request("user.getRecommendedArtists", {"sk": session_key, "limit": limit}, signed=True)
            raw = data.get("recommendations", {}).get("artist", [])
            return [raw] if isinstance(raw, dict) else raw
        except Exception as e:
            logger.warning(f"Authenticated artist fetch failed: {e}")
            return []

    async def _fetch_raw_top_artists(self, user_name: str, limit: int) -> list:
        try:
            data = await self._request("user.getTopArtists", {"user": user_name, "limit": limit})
            raw = data.get("topartists", {}).get("artist", [])
            return [raw] if isinstance(raw, dict) else raw
        except Exception as e:
            logger.error(f"Top artists fetch also failed: {e}")
            return []

    def _build_recommended_artist(self, a: dict) -> RecommendedArtist | None:
        name = a.get("name")
        if not name:
            return None
        return RecommendedArtist(
            name=name,
            url=a.get("url", ""),
            image_url=self._extract_best_image(a.get("image", [])),
            mbid=a.get("mbid"),
            match=float(a.get("match") or a.get("playcount") or 0.0),
        )

    async def get_recommended_artists(
        self, session_key: str | None, limit: int = 20, user_name: str | None = None
    ) -> list[RecommendedArtist]:
        """Get recommended artists for a user. Falls back to Top Artists if recommendations empty."""
        raw_artists: list = []

        if session_key:
            raw_artists = await self._fetch_raw_artists_authenticated(session_key, limit)

        if not raw_artists and user_name:
            logger.info(f"Falling back to user.getTopArtists for {user_name}")
            raw_artists = await self._fetch_raw_top_artists(user_name, limit)

        if not raw_artists:
            logger.warning(f"No artists found for user_name={user_name}, session_key={bool(session_key)}")
            return []

        logger.info(f"Processing {len(raw_artists)} raw artist items")
        results = [r for a in raw_artists if (r := self._build_recommended_artist(a))]
        logger.info(f"Returning {len(results)} processed artists")
        return results

    async def get_similar_tracks(self, artist: str, track: str, limit: int = 10) -> list[dict[str, Any]]:
        try:
            data = await self._request("track.getSimilar", {"artist": artist, "track": track, "limit": limit})
            return data.get("similartracks", {}).get("track", [])
        except LastfmAPIError:
            # Track might not have similar tracks or not found
            return []

    async def get_similar_artists(self, artist: str, limit: int = 10) -> list[dict[str, Any]]:
        try:
            data = await self._request("artist.getSimilar", {"artist": artist, "limit": limit})
            return data.get("similarartists", {}).get("artist", [])
        except LastfmAPIError:
            return []

    async def update_now_playing(self, track: str, artist: str, session_key: str, album: str | None = None) -> None:
        params = {"track": track, "artist": artist, "sk": session_key}
        if album:
            params["album"] = album

        await self._post_request("track.updateNowPlaying", params, signed=True)

    async def scrobble(
        self, track: str, artist: str, session_key: str, timestamp: int, album: str | None = None
    ) -> None:
        # Last.fm requires POST for scrobbling
        params = {"track": track, "artist": artist, "timestamp": timestamp, "sk": session_key}
        if album:
            params["album"] = album

        # We need to ensure _request handles POST correctly or create a new _post_request
        # Currently _request uses get.
        # Modifying _request to support POST would be better.

        # But wait, scrobbling requires POST. existing _request does GET.
        # Let's add a _post_request or modify _request.

        # I'll implement _post_request helper
        await self._post_request("track.scrobble", params, signed=True)

    async def _post_request(self, method: str, params: dict[str, Any], signed: bool = True) -> dict[str, Any]:
        """Send a POST request to Last.fm API."""
        params["method"] = method
        params["api_key"] = settings.LASTFM_API_KEY

        if signed:
            params["api_sig"] = self._sign_params(params)

        params["format"] = "json"

        # Last.fm POST body should contain the params (x-www-form-urlencoded usually, but passing as data work)

        try:
            response = await self.client.post("/", data=params)

            if response.status_code == 429:
                raise LastfmRateLimitError("Rate limit exceeded")

            response.raise_for_status()
            data = response.json()

            logger.debug(f"Last.fm POST response for {method}: {data}")

            if "error" in data:
                raise LastfmAPIError(f"Last.fm API Error {data['error']}: {data.get('message', 'Unknown error')}")

            return data
        except httpx.HTTPError as e:
            logger.error(f"Last.fm POST failed: {e}")
            raise LastfmAPIError(f"HTTP POST failed: {str(e)}")

    def _parse_artist_name(self, artist_data: Any) -> str | None:
        if isinstance(artist_data, str):
            return artist_data
        if isinstance(artist_data, dict):
            return artist_data.get("name") or artist_data.get(LASTFM_TEXT_KEY)
        if hasattr(artist_data, "name"):
            return artist_data.name
        return None

    def _add_track_seeds(self, result: Any, seed_tracks: list) -> None:
        if isinstance(result, Exception):
            return
        for t in cast(list[dict[str, Any]], result):
            artist = self._parse_artist_name(t.get("artist"))
            if t.get("name") and artist:
                seed_tracks.append((t["name"], artist))

    def _add_artist_seeds(self, result: Any, seed_artists: set) -> None:
        if isinstance(result, Exception):
            return
        for item in result:
            if name := self._parse_artist_name(item):
                seed_artists.add(name)

    async def _gather_seeds(self, user_id: str, session_key: str | None) -> tuple[list[tuple[str, str]], set[str]]:
        """Gather seed tracks and artists from multiple sources."""
        seed_tracks: list = []
        seed_artists: set = set()

        sources: list[Coroutine[Any, Any, Any]] = [
            self.get_user_top_tracks(user_id, period="1month", limit=10),
            self.get_user_recent_tracks(user_id, limit=10),
            self.get_user_top_artists(user_id, limit=10),
        ]
        if session_key:
            sources.append(self.get_recommended_artists(session_key, limit=10))

        results = cast(
            list[Any], await asyncio.gather(*[asyncio.create_task(s) for s in sources], return_exceptions=True)
        )

        self._add_track_seeds(results[0], seed_tracks)
        self._add_track_seeds(results[1], seed_tracks)
        self._add_artist_seeds(results[2], seed_artists)
        if session_key and len(results) > 3:
            self._add_artist_seeds(results[3], seed_artists)

        return seed_tracks, seed_artists

    async def get_recommendations(self, user_id: str, session_key: str | None = None) -> list[RecommendedTrack]:

        seed_tracks, seed_artists = await self._gather_seeds(user_id, session_key)

        # Deduplicate tracks
        unique_tracks = []
        seen_tracks = set()
        for n, a in seed_tracks:
            key = f"{a} - {n}"
            if key not in seen_tracks:
                unique_tracks.append((n, a))
                seen_tracks.add(key)

        if not unique_tracks and not seed_artists:
            logger.warning(f"No seeds found for user {user_id} on Last.fm")
            return []

        # 2. Process Seeds to find Similar Tracks/Top Tracks
        sem = asyncio.Semaphore(10)
        candidates: dict[str, RecommendedTrack] = {}

        async def fetch_similar_for_track(name, artist):
            async with sem:
                similar = await self.get_similar_tracks(artist, name, limit=10)
                for sim in similar:
                    self._add_to_candidates(candidates, sim)

        async def fetch_top_for_artist(artist_name):
            async with sem:
                try:
                    data = await self._request("artist.getTopTracks", {"artist": artist_name, "limit": 10})
                    tracks = data.get("toptracks", {}).get("track", [])
                    for t in tracks:
                        self._add_to_candidates(candidates, t, score_mult=0.5)
                except Exception:  # nosec B110
                    pass

        tasks = [fetch_similar_for_track(n, a) for n, a in unique_tracks[:15]]
        tasks.extend([fetch_top_for_artist(a) for a in list(seed_artists)[:10]])

        await asyncio.gather(*tasks)

        final_track_list = list(candidates.values())
        final_track_list.sort(key=lambda x: x.score, reverse=True)
        final_results = [r for r in final_track_list if f"{r.artist} - {r.name}" not in seen_tracks]

        logger.info(f"Generated {len(final_results)} recommendations for {user_id}")
        return final_results[:40]

    def _add_to_candidates(
        self, candidates: dict[str, RecommendedTrack], item: dict[str, Any], score_mult: float = 1.0
    ):
        name = item.get("name")
        artist = self._parse_artist_name(item.get("artist"))
        if not name or not artist:
            return

        key = f"{artist} - {name}"
        match = float(item.get("match") or item.get("rank") or 0.1)
        if "rank" in item:  # Top tracks use rank, we invert it for score
            match = 1.0 / (float(item["rank"]) + 1)

        if key not in candidates:
            image_url = self._extract_best_image(item.get("image", []))

            # Fallback to artist image if track image is missing
            # Only if artist is a dictionary containing image info
            artist_data = item.get("artist")
            if not image_url and isinstance(artist_data, dict):
                image_url = self._extract_best_image(artist_data.get("image", []))

            candidates[key] = RecommendedTrack(
                name=name, artist=artist, url=item.get("url", ""), image_url=image_url, match=match
            )

        candidates[key].score += match * score_mult

    def _extract_best_image(self, images: list[dict[str, str]]) -> str | None:
        """Extract the best quality image URL from Last.fm image array."""
        if not images:
            return None

        # Preferred order: larger to smaller
        sizes = ["mega", "extralarge", "large", "medium", "small"]

        # Build a map for easy lookup
        image_map = {img.get("size"): img.get(LASTFM_TEXT_KEY) for img in images if img.get(LASTFM_TEXT_KEY)}

        for size in sizes:
            url = image_map.get(size)
            if url and url.strip():
                return url

        # Last resort: just take any non-empty URL
        for url in image_map.values():
            if url and url.strip():
                return url

        return None
