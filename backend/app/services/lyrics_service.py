"""
Lyrics service using Genius API.
Provides lyrics fetching with Redis caching.
"""

import logging
from typing import Optional

from app.core.cache import cache_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache TTL: 24 hours
LYRICS_CACHE_TTL = 86400


class LyricsService:
    """Service for fetching and caching song lyrics from Genius."""

    def __init__(self):
        self._genius = None

    def _get_genius_client(self):
        """Lazy initialization of Genius client."""
        if self._genius is None:
            genius_token = getattr(settings, "GENIUS_API_TOKEN", None)
            if not genius_token:
                logger.warning("GENIUS_API_TOKEN not configured")
                return None

            try:
                import lyricsgenius

                self._genius = lyricsgenius.Genius(
                    genius_token,
                    verbose=False,
                    remove_section_headers=True,
                    skip_non_songs=True,
                    excluded_terms=["(Remix)", "(Live)"],
                    timeout=10,
                )
            except Exception as e:
                logger.error(f"Failed to initialize Genius client: {e}")
                return None

        return self._genius

    def _get_cache_key(self, artist: str, title: str) -> str:
        """Generate cache key for lyrics."""
        # Normalize for cache key
        normalized = f"{artist.lower().strip()}:{title.lower().strip()}"
        return f"lyrics:{normalized}"

    async def get_lyrics(self, artist: str, title: str, use_cache: bool = True) -> Optional[dict]:
        """
        Fetch lyrics for a song.

        Args:
            artist: Artist name
            title: Song title
            use_cache: Whether to use Redis cache

        Returns:
            Dict with lyrics data or None if not found
        """
        if not artist or not title:
            return None

        cache_key = self._get_cache_key(artist, title)

        # Try cache first
        if use_cache:
            cached = await self._get_from_cache(cache_key, artist, title)
            if cached:
                return cached

        # Fetch from Genius
        genius = self._get_genius_client()
        if not genius:
            return None

        return await self._fetch_and_cache_genius(genius, artist, title, cache_key)

    async def _get_from_cache(self, cache_key: str, artist: str, title: str) -> Optional[dict]:
        """Try to retrieve lyrics from cache."""
        if not cache_manager.redis:
            return None

        try:
            cached = await cache_manager.get(cache_key)
            if cached:
                logger.debug(f"Lyrics cache hit for {artist} - {title}")
                return cached
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None

    async def _fetch_and_cache_genius(self, genius, artist: str, title: str, cache_key: str) -> Optional[dict]:
        """Fetch from Genius and update cache."""
        try:
            song = genius.search_song(title, artist)

            if not song:
                logger.info(f"No lyrics found for {artist} - {title}")
                # Cache negative result for shorter time (1 hour)
                await self._cache_result(cache_key, {"found": False, "lyrics": None}, 3600)
                return {"found": False, "lyrics": None}

            result = {
                "found": True,
                "lyrics": song.lyrics,
                "title": song.title,
                "artist": song.artist,
                "url": song.url,
                "album": getattr(song, "album", None),
                "release_date": getattr(song, "release_date", None),
            }

            # Cache successful result
            await self._cache_result(cache_key, result, LYRICS_CACHE_TTL)
            logger.debug(f"Cached lyrics for {artist} - {title}")

            return result

        except Exception as e:
            logger.error(f"Failed to fetch lyrics for {artist} - {title}: {e}")
            return None

    async def _cache_result(self, key: str, data: dict, ttl: int):
        """Helper to cache results safely."""
        if cache_manager.redis:
            try:
                await cache_manager.set(key, data, ttl=ttl)
            except Exception as e:
                logger.warning(f"Cache write error: {e}")

    async def clear_cache(self, artist: str, title: str) -> bool:
        """Clear cached lyrics for a specific song."""
        if not cache_manager.redis:
            return False

        cache_key = self._get_cache_key(artist, title)
        try:
            await cache_manager.redis.delete(cache_key)
            return True
        except Exception as e:
            logger.error(f"Failed to clear lyrics cache: {e}")
            return False


# Singleton instance
lyrics_service = LyricsService()
