"""
SearchOrchestrator — Multi-source search aggregation layer.

Aggregates track results from Deezer, YouTube Music, SoundCloud, Apple Music
(iTunes), MusicBrainz and Spotify (optional).
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

from app.services.apple_music_service import apple_music_service
from app.services.deezer_service import DeezerService
from app.services.musicbrainz_service import MusicBrainzService
from app.services.soundcloud_service import soundcloud_service
from app.services.spotify_service import SpotifyService  # noqa: F401

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    """Centralized search service aggregating multiple music metadata providers."""

    def __init__(self) -> None:
        self.deezer = DeezerService()
        self.musicbrainz = MusicBrainzService()
        self.spotify = SpotifyService()
        self.soundcloud = soundcloud_service
        self.apple = apple_music_service
        self._youtube: Any = None

    @property
    def youtube(self) -> Any:
        """Lazily construct YouTubeService — ``YTMusic()`` init is deferred so a
        transient ytmusicapi failure cannot break module import / app startup."""
        if self._youtube is None:
            from app.services.youtube_service import YouTubeService

            self._youtube = YouTubeService()
        return self._youtube

    # --- Public Search Methods ---

    async def search_tracks(
        self, query: str, limit: int = 20, source: str = "all", offset: int = 0
    ) -> list[dict[str, Any]]:
        """Search tracks across providers (or a single one) and deduplicate.

        offset > 0 (pagination beyond page 1) is only supported by Deezer —
        Spotify partner search and MusicBrainz would just return page 1 again,
        polluting later pages with duplicates after dedup. So for offset > 0
        we query Deezer exclusively; if `source` requests a different single
        provider, there's no pagination available and we return an empty list.
        """
        if offset > 0:
            if source not in ("all", "deezer"):
                return []
            results = await self._safe_call(self.deezer.search(query, limit=limit, offset=offset))
            return results[:limit]

        providers = {
            "deezer": self._search_deezer,
            "youtube": self._search_youtube,
            "soundcloud": self._search_soundcloud,
            "apple_music": self._search_apple,
            "musicbrainz": self._search_musicbrainz,
            "spotify": self._search_spotify,
        }
        selected = [providers[source]] if source in providers else list(providers.values())
        tasks = [self._safe_call(fn(query, limit)) for fn in selected]

        results_lists = await asyncio.gather(*tasks)
        all_results = []
        for results in results_lists:
            all_results.extend(results)

        deduplicated = self._deduplicate_results(all_results)
        # Round-robin by source so a provider that fills the whole page (Deezer
        # always returns a full page) does not push every other source past the
        # `limit` cut — the reason "all" used to look Deezer-only.
        interleaved = self._interleave_by_source(deduplicated)
        return interleaved[:limit]

    async def search_artists(self, query: str, limit: int = 10, source: str = "all") -> list[dict[str, Any]]:
        """Search artists across providers. No Spotify artist search available."""
        providers = {
            "deezer": self._search_deezer_artists,
            "musicbrainz": self._search_musicbrainz_artists,
        }
        if source in providers:
            selected = [providers[source]]
        elif source == "all":
            selected = list(providers.values())
        else:
            return []
        tasks = [self._safe_call(fn(query, limit)) for fn in selected]

        results_lists = await asyncio.gather(*tasks)
        all_results = []
        for results in results_lists:
            all_results.extend(results)

        deduplicated = self._deduplicate_by_name(all_results)
        return deduplicated[:limit]

    async def search_albums(self, query: str, limit: int = 10, source: str = "all") -> list[dict[str, Any]]:
        """Search albums across providers. No Spotify album search available."""
        providers = {
            "deezer": self._search_deezer_albums,
            "musicbrainz": self._search_musicbrainz_albums,
        }
        if source in providers:
            selected = [providers[source]]
        elif source == "all":
            selected = list(providers.values())
        else:
            return []
        tasks = [self._safe_call(fn(query, limit)) for fn in selected]

        results_lists = await asyncio.gather(*tasks)
        all_results = []
        for results in results_lists:
            all_results.extend(results)

        return all_results[:limit]

    async def search_playlists(self, query: str, limit: int = 10, source: str = "all") -> list[dict[str, Any]]:
        """Search playlists. Deezer is the only provider with public playlist search."""
        if source not in ("all", "deezer"):
            return []
        results = await self._safe_call(self.deezer.search_playlists(query, limit=limit))
        return (results or [])[:limit]

    # --- Track/Artist/Album Details ---

    async def get_track_details(self, source: str, track_id: str) -> dict[str, Any] | None:
        """Get track details from a specific source."""
        if source == "deezer":
            return await self.deezer.get_track(track_id)
        elif source == "spotify":
            return await self.spotify.get_track(track_id)
        elif source == "musicbrainz":
            return await self.musicbrainz.get_track_by_isrc(track_id)
        return None

    async def get_artist_details(self, source: str, artist_id: str) -> dict[str, Any] | None:
        """Get artist details from a specific source."""
        if source == "deezer":
            return await self.deezer.get_artist_details(artist_id)
        elif source == "spotify":
            return await self.spotify.get_artist_details(artist_id)
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
            return await self.spotify.get_album_details(album_id)
        return None

    async def get_playlist_details(self, source: str, playlist_id: str) -> dict[str, Any] | None:
        """Get playlist details from a specific source."""
        if source == "deezer":
            return await self.deezer.get_playlist_details(playlist_id)
        elif source == "spotify":
            return await self.spotify.get_playlist_details(playlist_id)
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
        """Search tracks via MusicBrainz API using a free-form query.

        The whole phrase is handed to MusicBrainz as-is instead of being split on
        the first space into artist/title — that split produced garbage for any
        query longer than "Artist Title".
        """
        return await self.musicbrainz.search_recording(query, limit=limit)

    async def _search_youtube(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search tracks via YouTube Music (ytmusicapi is sync — off-load to a thread)."""
        return await asyncio.to_thread(self.youtube.search, query, limit, "song")

    async def _search_soundcloud(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search tracks via SoundCloud (yt-dlp ``scsearch``)."""
        return await self.soundcloud.search(query, limit=limit)

    async def _search_apple(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search tracks via Apple Music (iTunes Search API)."""
        return await self.apple.search(query, limit=limit)

    async def _search_spotify(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search tracks via Spotify API (optional)."""
        # Spotify API Feb 2026: search limit reduced to max 10
        spotify_limit = min(limit, 10)
        try:
            return await self.spotify.search(query, limit=spotify_limit, type="track")
        except Exception as e:
            logger.warning(f"Spotify async search failed: {e}")
            return []

    async def _search_deezer_artists(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search artists via Deezer artist search endpoint."""
        return await self.deezer.search_artists(query, limit=limit)

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

    def _replace_if_better_image(self, unique: list, seen_map: dict, key: str, result: dict[str, Any]) -> None:
        existing = seen_map[key]
        if not existing.get("image_url") and result.get("image_url"):
            unique[unique.index(existing)] = result
            seen_map[key] = result

    def _interleave_by_source(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Round-robin results across their ``source`` while preserving first-seen
        source order and each source's internal ranking."""
        buckets: dict[str, list[dict[str, Any]]] = {}
        for r in results:
            buckets.setdefault(r.get("source", "?"), []).append(r)

        queues = list(buckets.values())
        interleaved: list[dict[str, Any]] = []
        while queues:
            for queue in list(queues):
                interleaved.append(queue.pop(0))
                if not queue:
                    queues.remove(queue)
        return interleaved

    def _deduplicate_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate results by ISRC, preferring entries with cover art."""
        seen_isrcs: dict[str, dict[str, Any]] = {}
        seen_titles: dict[str, dict[str, Any]] = {}
        unique: list[dict[str, Any]] = []

        for result in results:
            isrc = result.get("isrc")
            title_key = f"{result.get('title', '').lower()}|{result.get('artist', '').lower()}"

            if isrc:
                if isrc in seen_isrcs:
                    self._replace_if_better_image(unique, seen_isrcs, isrc, result)
                    continue
                seen_isrcs[isrc] = result
                seen_titles[title_key] = result
                unique.append(result)
            else:
                if title_key in seen_titles:
                    self._replace_if_better_image(unique, seen_titles, title_key, result)
                    continue
                seen_titles[title_key] = result
                unique.append(result)

        return unique

    def _deduplicate_by_name(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate artist/album results by name, preferring one with image."""
        seen: dict[str, dict[str, Any]] = {}
        unique: list[dict[str, Any]] = []

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

    async def _safe_call(self, coro, timeout: float = 15.0) -> list[dict[str, Any]]:
        """Safely call a coroutine, returning empty list on failure or timeout.

        A per-provider timeout keeps one slow backend (SoundCloud's yt-dlp
        ``scsearch`` in particular) from stalling the whole aggregated search.
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except TimeoutError:
            logger.warning("Provider search timed out after %.0fs", timeout)
            return []
        except Exception as e:
            logger.warning(f"Provider search failed: {e}")
            return []


# Module-level singleton
search_orchestrator = SearchOrchestrator()
