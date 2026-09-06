import asyncio
import json
import logging
import random
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.cache import cache_manager
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse, RecommendedArtist, RecommendedPlaylist, RecommendedTrack
from app.services.deezer_service import DeezerService
from app.services.lastfm_service import LastfmError, LastfmService
from app.services.listening.base import ListeningError, ListeningProvider, ProviderCredentials
from app.services.listening.registry import connected_providers, get_provider
from app.utils.log_sanitize import sanitize_log

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Last.fm placeholder image hashes - returned when no real cover exists
LASTFM_PLACEHOLDER_HASHES = [
    "2a96cbd8b46e442fc41c2b86b821562f",
    "c6f59c1e5e7240a4c0d427abd71f3dbb",
]


def _is_missing_image(image_url: str | None) -> bool:
    if not image_url or not image_url.strip():
        return True
    return any(placeholder in image_url for placeholder in LASTFM_PLACEHOLDER_HASHES)


class HybridRecommendationEngine:
    """Generates recommendations from a user's listening history.

    Seeds come from whichever :class:`ListeningProvider` the user picked
    (Last.fm or ListenBrainz); the similarity expansion + final scoring is
    always Last.fm's public graph (``expansion``), and cover art is back-filled
    from Deezer.
    """

    def __init__(
        self,
        provider: ListeningProvider | None = None,
        credentials: ProviderCredentials | None = None,
        expansion: LastfmService | None = None,
    ) -> None:
        self.provider = provider
        self.credentials = credentials
        self.expansion = expansion or LastfmService()
        self.cache = cache_manager

    @classmethod
    async def for_user(cls, user: User, db: AsyncSession, preferred: str | None = None) -> HybridRecommendationEngine:
        """Build an engine bound to the user's chosen (or first connected) provider."""
        choice = preferred or (user.preferences or {}).get("listening_provider", "auto")
        connected = await connected_providers(user, db)

        provider: ListeningProvider | None = None
        credentials: ProviderCredentials | None = None
        if choice and choice != "auto":
            wanted = get_provider(choice)
            for prov, creds in connected:
                if wanted is not None and prov.name == wanted.name:
                    provider, credentials = prov, creds
                    break
        elif connected:
            provider, credentials = connected[0]

        return cls(provider=provider, credentials=credentials)

    @property
    def is_connected(self) -> bool:
        return self.provider is not None and self.credentials is not None

    async def _get_cached_recommendations(self, cache_key: str) -> RecommendationResponse | None:
        cached_data = await self.cache.get(cache_key)
        if not cached_data:
            return None
        try:
            return RecommendationResponse(**json.loads(cached_data))
        except Exception as e:
            logger.error(f"Failed to parse cached recommendations: {e}")
            return None

    async def _backfill_track_images(self, tracks: list[RecommendedTrack]) -> None:
        missing = [t for t in tracks if _is_missing_image(t.image_url)]
        if not missing:
            return
        deezer = DeezerService()

        async def fetch(track: RecommendedTrack) -> None:
            try:
                results = await deezer.search(f"{track.artist} {track.name}", limit=5)
                for result in results:
                    if result.get("image_url"):
                        track.image_url = result["image_url"]
                        return
            except Exception as e:
                logger.error(f"Deezer search error for {track.name}: {e}")

        await asyncio.gather(*[fetch(t) for t in missing[:50]])

    async def _gather_seeds(self, variety: bool) -> tuple[list[tuple[str, str]], list[str]]:
        if not self.is_connected:
            return [], []
        assert self.provider is not None and self.credentials is not None
        try:
            return await self.provider.get_seeds(self.credentials, variety=variety)
        except (ListeningError, LastfmError) as e:
            logger.warning("Seed fetch failed (%s): %s", self.provider.name, e)
            return [], []

    async def _expand_tracks(
        self, seed_tracks: list[tuple[str, str]], seed_artists: list[str], variety: bool
    ) -> list[RecommendedTrack]:
        if not seed_tracks and not seed_artists:
            return []
        try:
            tracks = await self.expansion.recommend_from_seeds(seed_tracks, seed_artists, variety=variety, limit=60)
        except LastfmError as e:
            logger.warning("Seed expansion failed: %s", e)
            return []
        await self._backfill_track_images(tracks)
        return tracks

    async def _fill_artist_image(self, deezer: DeezerService, artist: RecommendedArtist) -> None:
        try:
            results = await deezer.search(artist.name, limit=1)
            if results and results[0].get("image_url"):
                artist.image_url = results[0]["image_url"]
        except Exception as e:
            logger.error(f"Deezer artist search error for {artist.name}: {e}")

    async def _fetch_artists(self, variety: bool) -> list[RecommendedArtist]:
        if not self.is_connected:
            return []
        assert self.provider is not None and self.credentials is not None
        try:
            artists = await self.provider.get_recommended_artists(self.credentials, limit=50)
        except (ListeningError, LastfmError) as e:
            logger.warning("Artist recommendation fetch failed (%s): %s", self.provider.name, e)
            return []

        if variety:
            random.shuffle(artists)
        artists = artists[:24]
        for a in artists:
            a.image_url = None
        if artists:
            deezer = DeezerService()
            await asyncio.gather(*[self._fill_artist_image(deezer, a) for a in artists])
        return artists

    async def _search_deezer_playlists_for_artist(self, deezer: DeezerService, artist_name: str) -> list:
        try:
            return await deezer.search_playlists(artist_name, limit=3) or []
        except Exception as e:
            logger.warning(f"Playlist search failed for {artist_name}: {e}")
            return []

    def _collect_unique_playlists(self, search_results: list) -> list[RecommendedPlaylist]:
        seen_ids: set = set()
        playlists = []
        for results_batch in search_results:
            for p in results_batch:
                if p["id"] not in seen_ids:
                    playlists.append(
                        RecommendedPlaylist(
                            id=p["id"],
                            title=p.get("title", ""),
                            image_url=p.get("image_url"),
                            track_count=p.get("track_count", 0),
                            source="deezer",
                            url=p.get("url") or f"https://www.deezer.com/playlist/{p['id']}",
                        )
                    )
                    seen_ids.add(p["id"])
        return playlists

    async def _fetch_playlists(self, seed_artists: list[str]) -> list[RecommendedPlaylist]:
        artist_names = seed_artists[:5]
        if not artist_names:
            return []
        deezer = DeezerService()
        search_results = await asyncio.gather(
            *[self._search_deezer_playlists_for_artist(deezer, name) for name in artist_names]
        )
        return self._collect_unique_playlists(search_results)[:15]

    async def get_recommendations(
        self, user: User, source: str = "auto", force_refresh: bool = False
    ) -> RecommendationResponse:
        provider_name = self.provider.name if self.provider else "none"
        cache_key = f"rec:{user.id}:{provider_name}"

        if not force_refresh:
            cached = await self._get_cached_recommendations(cache_key)
            if cached:
                return cached
        else:
            logger.info(f"Force refresh: clearing cache for user {user.id}")
            await self.cache.delete(cache_key)

        variety = force_refresh

        seed_tracks, seed_artists = await self._gather_seeds(variety)
        tracks = await self._expand_tracks(seed_tracks, seed_artists, variety)
        artists = await self._fetch_artists(variety)
        playlists = await self._fetch_playlists(seed_artists)

        used_source = f"{provider_name}+deezer" if (tracks or artists or playlists) else "unknown"

        response = RecommendationResponse(
            tracks=tracks,
            artists=artists,
            playlists=playlists,
            source=used_source,
            cache_status="miss",
            provider=provider_name,
            lastfm_connected=self.is_connected and provider_name == "lastfm",
            generated_at=datetime.now(),
        )

        if tracks or artists or playlists:
            logger.info(
                "Caching recommendations for user %s: %d tracks, %d artists, %d playlists",
                sanitize_log(user.id),
                len(tracks),
                len(artists),
                len(playlists),
            )
            try:
                await self.cache.set(cache_key, response.model_dump_json(), expire=86400)
            except Exception as e:
                logger.error(f"Failed to cache recommendations: {e}")
        else:
            logger.warning(f"No recommendations generated for user {user.id}")

        return response
