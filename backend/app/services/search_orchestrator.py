"""
SearchOrchestrator — Multi-source search aggregation layer.

Aggregates results from Deezer (primary), MusicBrainz, and Spotify (optional fallback).
Provides:
- Unified search across providers
- ISRC-based deduplication
- Title+artist fuzzy deduplication
- Preference for results with cover art
- Fallback when individual providers fail
- ISRC resolution for track matching
"""

import asyncio
import logging
from typing import Any

from app.services.deezer_service import DeezerService
from app.services.musicbrainz_service import MusicBrainzService
from app.services.spotify_service import SpotifyService

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    """Centralized search service aggregating multiple music metadata providers."""

    def __init__(self) -> None:
        self.deezer = DeezerService()
        self.musicbrainz = MusicBrainzService()
        self.spotify = SpotifyService()

    # --- Public Search Methods ---

    async def search_tracks(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search tracks across all providers and return deduplicated results."""
        tasks = [
            self._safe_call(self._search_deezer(query, limit)),
            self._safe_call(self._search_musicbrainz(query, limit)),
            self._safe_call(self._search_spotify(query, limit)),
        ]

        results_lists = await asyncio.gather(*tasks)
        all_results = []
        for results in results_lists:
            all_results.extend(results)

        deduplicated = self._deduplicate_results(all_results)
        return deduplicated[:limit]

    async def search_artists(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search artists across providers."""
        tasks = [
            self._safe_call(self._search_deezer_artists(query, limit)),
            self._safe_call(self._search_musicbrainz_artists(query, limit)),
        ]

        results_lists = await asyncio.gather(*tasks)
        all_results = []
        for results in results_lists:
            all_results.extend(results)

        deduplicated = self._deduplicate_by_name(all_results)
        return deduplicated[:limit]

    async def search_albums(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search albums across providers."""
        tasks = [
            self._safe_call(self._search_deezer_albums(query, limit)),
            self._safe_call(self._search_musicbrainz_albums(query, limit)),
        ]

        results_lists = await asyncio.gather(*tasks)
        all_results = []
        for results in results_lists:
            all_results.extend(results)

        return all_results[:limit]

    # --- Track/Artist/Album Details ---

    async def get_track_details(self, source: str, track_id: str) -> dict[str, Any] | None:
        """Get track details from a specific source."""
        if source == "deezer":
            return await self.deezer.get_track(track_id)
        elif source == "spotify":
            if self.spotify.client:
                return self.spotify.get_track(track_id)
            return None
        elif source == "musicbrainz":
            return await self.musicbrainz.get_track_by_isrc(track_id)
        return None

    async def get_artist_details(self, source: str, artist_id: str) -> dict[str, Any] | None:
        """Get artist details from a specific source."""
        if source == "deezer":
            return await self.deezer.get_artist_details(artist_id)
        elif source == "spotify":
            if self.spotify.client:
                return self.spotify.get_artist_details(artist_id)
            return None
        elif source == "musicbrainz":
            return await self.musicbrainz.get_artist(artist_id)
        elif source == "auto":
            # Try Deezer first, then MusicBrainz
            result = await self.deezer.get_artist_details(artist_id)
            if not result:
                result = await self.musicbrainz.get_artist(artist_id)
            return result
        return None

    async def get_album_details(self, source: str, album_id: str) -> dict[str, Any] | None:
        """Get album details from a specific source."""
        if source == "deezer":
            tracks = await self.deezer.get_album_tracks(album_id)
            return {"id": album_id, "tracks": tracks, "source": "deezer"} if tracks else None
        elif source == "spotify":
            if self.spotify.client:
                return self.spotify.get_album_details(album_id)
            return None
        return None

    async def get_playlist_details(self, source: str, playlist_id: str) -> dict[str, Any] | None:
        """Get playlist details from a specific source."""
        if source == "deezer":
            return await self.deezer.get_playlist_details(playlist_id)
        elif source == "spotify":
            if self.spotify.client:
                return self.spotify.get_playlist_details(playlist_id)
            return None
        return None

    # --- ISRC Resolution ---

    async def resolve_isrc(self, artist: str, title: str) -> str | None:
        """Try to resolve an ISRC for a track using MusicBrainz."""
        try:
            results = await self.musicbrainz.search_track(artist, title, limit=1)
            if results:
                return results[0].get("isrc")
        except Exception as e:
            logger.warning(f"Failed to resolve ISRC for {artist} - {title}: {e}")
        return None

    # --- Internal Provider Methods ---

    async def _search_deezer(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search tracks via Deezer API."""
        return await self.deezer.search(query, limit=limit)

    async def _search_musicbrainz(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search tracks via MusicBrainz API."""
        # MusicBrainz search expects artist and title separately
        # For a generic query, we split crudely or search as full string
        parts = query.split(" ", 1)
        if len(parts) >= 2:
            return await self.musicbrainz.search_track(artist=parts[0], title=parts[1], limit=limit)
        return await self.musicbrainz.search_track(artist="", title=query, limit=limit)

    async def _search_spotify(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search tracks via Spotify API (optional)."""
        if not self.spotify.client:
            return []
        # Spotify API Feb 2026: search limit reduced to max 10
        spotify_limit = min(limit, 10)
        try:
            return await asyncio.to_thread(self.spotify.search, query, limit=spotify_limit, type="track")
        except Exception as e:
            logger.warning(f"Spotify search failed: {e}")
            return []

    async def _search_deezer_artists(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search artists via Deezer — uses track search and extracts artists."""
        tracks = await self.deezer.search(query, limit=limit)
        artists_seen = set()
        artists = []
        for t in tracks:
            name = t.get("artist")
            if name and name not in artists_seen:
                artists_seen.add(name)
                artists.append(
                    {
                        "id": t.get("id"),
                        "name": name,
                        "image_url": t.get("image_url"),
                        "source": "deezer",
                        "type": "artist",
                    }
                )
        return artists

    async def _search_musicbrainz_artists(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search artists via MusicBrainz."""
        return await self.musicbrainz.search_artist(query, limit=limit)

    async def _search_deezer_albums(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search albums via Deezer — uses track search and extracts unique albums."""
        tracks = await self.deezer.search(query, limit=limit)
        albums_seen = set()
        albums = []
        for t in tracks:
            album_name = t.get("album")
            if album_name and album_name not in albums_seen:
                albums_seen.add(album_name)
                albums.append(
                    {
                        "id": t.get("id"),
                        "title": album_name,
                        "artist": t.get("artist"),
                        "image_url": t.get("image_url"),
                        "source": "deezer",
                    }
                )
        return albums

    async def _search_musicbrainz_albums(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search albums (releases) via MusicBrainz."""
        return await self.musicbrainz.search_album(query, limit=limit)

    # --- Deduplication ---

    def _deduplicate_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate results by ISRC, preferring entries with cover art."""
        seen_isrcs: dict[str, dict[str, Any]] = {}
        seen_titles: dict[str, dict[str, Any]] = {}
        unique = []

        for result in results:
            isrc = result.get("isrc")
            title_key = f"{result.get('title', '').lower()}|{result.get('artist', '').lower()}"

            # ISRC-based dedup
            if isrc:
                if isrc in seen_isrcs:
                    # Prefer the one with an image
                    existing = seen_isrcs[isrc]
                    if not existing.get("image_url") and result.get("image_url"):
                        # Replace with the one that has an image
                        idx = unique.index(existing)
                        unique[idx] = result
                        seen_isrcs[isrc] = result
                    continue
                seen_isrcs[isrc] = result
                seen_titles[title_key] = result
                unique.append(result)
            else:
                # Title+artist dedup for results without ISRC
                if title_key in seen_titles:
                    existing = seen_titles[title_key]
                    if not existing.get("image_url") and result.get("image_url"):
                        idx = unique.index(existing)
                        unique[idx] = result
                        seen_titles[title_key] = result
                    continue
                seen_titles[title_key] = result
                unique.append(result)

        return unique

    def _deduplicate_by_name(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate artist/album results by name, preferring one with image."""
        seen: dict[str, dict[str, Any]] = {}
        unique = []

        for result in results:
            name = result.get("name", result.get("title", "")).lower()
            if name in seen:
                existing = seen[name]
                if not existing.get("image_url") and result.get("image_url"):
                    idx = unique.index(existing)
                    unique[idx] = result
                    seen[name] = result
                continue
            seen[name] = result
            unique.append(result)

        return unique

    # --- Utility ---

    async def _safe_call(self, coro) -> list[dict[str, Any]]:
        """Safely call a coroutine, returning empty list on failure."""
        try:
            return await coro
        except Exception as e:
            logger.warning(f"Provider search failed: {e}")
            return []


# Module-level singleton
search_orchestrator = SearchOrchestrator()
