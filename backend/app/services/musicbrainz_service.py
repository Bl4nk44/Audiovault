"""
MusicBrainz API service for Audiovault.

Provides metadata lookup using the MusicBrainz Web API v2.
Primary use cases:
- Track search by artist + title
- Artist and album search
- ISRC-based track lookup
- Cover art via Cover Art Archive
- Artist discography (top releases)

Rate limited to 1 request/second as per MusicBrainz API guidelines.
"""

import asyncio
import logging
import re
import time
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

_MBID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_ISRC_RE = re.compile(r"^[A-Za-z]{2}[A-Za-z0-9]{3}\d{7}$")


def _sanitize_log(value: object) -> str:
    """Strip CR/LF from a value before logging to prevent log injection/forging."""
    return str(value).replace("\r", "").replace("\n", "")


class MusicBrainzService:
    BASE_URL = "https://musicbrainz.org/ws/2"
    COVER_ART_URL = "https://coverartarchive.org"
    USER_AGENT = "Audiovault/2.0 (https://github.com/Bl4nk44/Audiovault)"
    UNKNOWN_ARTIST = "Unknown Artist"
    UNKNOWN_ALBUM = "Unknown Album"

    def __init__(self) -> None:
        self._last_request_time: float = 0.0
        self._rate_lock = asyncio.Lock()

    async def _rate_limit(self) -> None:
        """Enforce 1 request/second rate limit for MusicBrainz API compliance."""
        async with self._rate_lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
            self._last_request_time = time.monotonic()

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Make a rate-limited GET request to MusicBrainz or Cover Art Archive."""
        await self._rate_limit()
        headers = {"User-Agent": self.USER_AGENT, "Accept": "application/json"}

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.warning(f"MusicBrainz API returned {response.status} for {_sanitize_log(url)}")
                        return None
                    return await response.json()
        except Exception as e:
            logger.error(f"MusicBrainz API request failed: {e}")
            return None

    # --- Search Methods ---

    async def search_track(self, artist: str, title: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for recordings by artist and title."""
        query = f'recording:"{title}" AND artist:"{artist}"'
        params = {"query": query, "limit": limit, "fmt": "json"}

        data = await self._get(f"{self.BASE_URL}/recording", params=params)
        if not data:
            return []

        recordings = data.get("recordings", [])
        return [self._format_recording(rec) for rec in recordings]

    async def search_recording(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Free-form recording search — passes the whole phrase as the Lucene query.

        Unlike :meth:`search_track`, this does not force ``recording:``/``artist:``
        field qualifiers, so a generic phrase like "the weeknd blinding lights"
        matches across MusicBrainz's default fields instead of being split
        arbitrarily on the first space.
        """
        params = {"query": query, "limit": limit, "fmt": "json"}

        data = await self._get(f"{self.BASE_URL}/recording", params=params)
        if not data:
            return []

        return [self._format_recording(rec) for rec in data.get("recordings", [])]

    async def search_artist(self, name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for artists by name."""
        params = {"query": f'artist:"{name}"', "limit": limit, "fmt": "json"}

        data = await self._get(f"{self.BASE_URL}/artist", params=params)
        if not data:
            return []

        artists = data.get("artists", [])
        return [self._format_artist(a) for a in artists]

    async def search_album(self, title: str, artist: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """Search for releases by title and optional artist."""
        query = f'release:"{title}"'
        if artist:
            query += f' AND artist:"{artist}"'

        params = {"query": query, "limit": limit, "fmt": "json"}

        data = await self._get(f"{self.BASE_URL}/release", params=params)
        if not data:
            return []

        releases = data.get("releases", [])
        return [self._format_release(rel) for rel in releases]

    # --- Lookup Methods ---

    async def get_track_by_isrc(self, isrc: str) -> dict[str, Any] | None:
        """Look up a recording by ISRC code."""
        if not _ISRC_RE.match(isrc):
            logger.warning(f"Rejected malformed ISRC: {_sanitize_log(isrc)}")
            return None

        params = {"inc": "artist-credits+releases", "fmt": "json"}

        data = await self._get(f"{self.BASE_URL}/isrc/{isrc}", params=params)
        if not data:
            return None

        recordings = data.get("recordings", [])
        if not recordings:
            return None

        return self._format_recording(recordings[0])

    async def get_artist(self, mbid: str) -> dict[str, Any] | None:
        """Get artist details by MusicBrainz ID."""
        if not _MBID_RE.match(mbid):
            logger.warning(f"Rejected malformed MBID: {_sanitize_log(mbid)}")
            return None

        params = {"fmt": "json"}

        data = await self._get(f"{self.BASE_URL}/artist/{mbid}", params=params)
        if not data:
            return None

        return self._format_artist(data)

    async def get_cover_art(self, release_mbid: str) -> str | None:
        """Get front cover art URL from Cover Art Archive."""
        if not _MBID_RE.match(release_mbid):
            logger.warning(f"Rejected malformed release MBID: {_sanitize_log(release_mbid)}")
            return None

        data = await self._get(f"{self.COVER_ART_URL}/release/{release_mbid}")
        if not data:
            return None

        images = data.get("images", [])
        for img in images:
            if img.get("front"):
                thumbnails = img.get("thumbnails", {})
                # Prefer 500px, then large, then full image
                return thumbnails.get("500") or thumbnails.get("large") or img.get("image")

        # Fallback to first image if no front cover
        if images:
            thumbnails = images[0].get("thumbnails", {})
            return thumbnails.get("500") or thumbnails.get("large") or images[0].get("image")

        return None

    async def get_artist_top_releases(self, mbid: str, limit: int = 20) -> list[dict[str, Any]]:
        """Get official releases for an artist."""
        params = {
            "artist": mbid,
            "type": "album|single",
            "status": "official",
            "limit": limit,
            "fmt": "json",
        }

        data = await self._get(f"{self.BASE_URL}/release", params=params)
        if not data:
            return []

        releases = data.get("releases", [])
        formatted = []
        seen_titles = set()

        for rel in releases:
            title = rel.get("title", "")
            # De-duplicate by title (MusicBrainz returns multiple editions)
            if title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())

            formatted.append(
                {
                    "id": rel.get("id"),
                    "title": title,
                    "date": rel.get("date"),
                    "status": rel.get("status"),
                    "type": rel.get("release-group", {}).get("primary-type", "Album"),
                    "source": "musicbrainz",
                }
            )

        return formatted

    # --- Formatting Methods ---

    def _format_recording(self, rec: dict[str, Any]) -> dict[str, Any]:
        """Format a MusicBrainz recording to match Audiovault track format."""
        # Artist
        artist_name = self.UNKNOWN_ARTIST
        artist_credits = rec.get("artist-credit", [])
        if artist_credits:
            artist_parts = []
            for credit in artist_credits:
                artist_obj = credit.get("artist", {})
                name = artist_obj.get("name", "")
                if name:
                    artist_parts.append(name)
                joinphrase = credit.get("joinphrase", "")
                if joinphrase:
                    artist_parts.append(joinphrase.strip())
            artist_name = " ".join(artist_parts) if artist_parts else self.UNKNOWN_ARTIST

        # Album (first release)
        album_name = self.UNKNOWN_ALBUM
        release_mbid = None
        releases = rec.get("releases", [])
        if releases:
            album_name = releases[0].get("title", self.UNKNOWN_ALBUM)
            release_mbid = releases[0].get("id")

        # ISRC
        isrcs = rec.get("isrcs", [])
        isrc = isrcs[0] if isrcs else None

        return {
            "id": rec.get("id"),
            "title": rec.get("title", "Unknown"),
            "artist": artist_name,
            "album": album_name,
            "duration_ms": rec.get("length"),
            "image_url": None,  # MusicBrainz doesn't provide images directly; use Cover Art Archive
            "source": "musicbrainz",
            "isrc": isrc,
            "release_mbid": release_mbid,
            "score": rec.get("score"),
        }

    def _format_artist(self, artist: dict[str, Any]) -> dict[str, Any]:
        """Format a MusicBrainz artist to match Audiovault artist format."""
        return {
            "id": artist.get("id"),
            "name": artist.get("name", "Unknown"),
            "image_url": None,  # MusicBrainz doesn't provide artist images
            "source": "musicbrainz",
            "type": "artist",
            "country": artist.get("country"),
        }

    def _format_release(self, release: dict[str, Any]) -> dict[str, Any]:
        """Format a MusicBrainz release to match Audiovault album format."""
        artist_name = self.UNKNOWN_ARTIST
        artist_credits = release.get("artist-credit", [])
        if artist_credits:
            artist_obj = artist_credits[0].get("artist", {})
            artist_name = artist_obj.get("name", self.UNKNOWN_ARTIST)

        return {
            "id": release.get("id"),
            "title": release.get("title", "Unknown"),
            "artist": artist_name,
            "date": release.get("date"),
            "track_count": release.get("track-count"),
            "image_url": None,
            "source": "musicbrainz",
            "type": release.get("release-group", {}).get("primary-type", "Album"),
        }


musicbrainz_service = MusicBrainzService()
