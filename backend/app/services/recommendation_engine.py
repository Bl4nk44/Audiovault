import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional

from app.core.cache import cache_manager
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse, RecommendedArtist, RecommendedPlaylist, RecommendedTrack
from app.services.deezer_service import DeezerService
from app.services.lastfm_service import LastfmError, LastfmService

logger = logging.getLogger(__name__)

# Last.fm placeholder image hashes - returned when no real cover exists
# Two known placeholders: gray star icon
LASTFM_PLACEHOLDER_HASHES = [
    "2a96cbd8b46e442fc41c2b86b821562f",  # Most common placeholder
    "c6f59c1e5e7240a4c0d427abd71f3dbb",  # Alternative placeholder
]


def _is_missing_image(image_url: Optional[str]) -> bool:
    """Check if image URL is missing, empty, or a Last.fm placeholder."""
    if not image_url or not image_url.strip():
        return True
    # Last.fm returns placeholder hashes for missing covers
    for placeholder in LASTFM_PLACEHOLDER_HASHES:
        if placeholder in image_url:
            return True
    return False


class HybridRecommendationEngine:
    def __init__(self, lastfm_service: LastfmService):
        self.lastfm = lastfm_service
        self.cache = cache_manager

    def _user_has_lastfm(self, user: User) -> bool:
        """Check if user has a Last.fm session connected."""
        return bool(user.lastfm_session_key)

    async def _get_cached_recommendations(self, cache_key: str) -> Optional[RecommendationResponse]:
        cached_data = await self.cache.get(cache_key)
        if not cached_data:
            return None
        try:
            data = json.loads(cached_data)
            return RecommendationResponse(**data)
        except Exception as e:
            logger.error(f"Failed to parse cached recommendations: {e}")
            return None

    async def _fetch_lastfm_recommendations(self, user: User, source: str) -> List[RecommendedTrack]:
        if source != "auto":
            # We used to support 'lastfm' vs 'llm', now only 'auto' (which is lastfm)
            # or we can treat everything as auto for now.
            pass

        if not self._user_has_lastfm(user):
            return []

        try:
            target_user = user.lastfm_username or user.username
            session_key = user.lastfm_session_key
            logger.info(f"Fetching recommendations from Last.fm for user {target_user}")
            tracks = await self.lastfm.get_recommendations(target_user, session_key=session_key)

            # --- Spotify Image Fallback ---
            # For tracks missing images (including Last.fm placeholder)
            tracks_missing_images = [t for t in tracks if _is_missing_image(t.image_url)]
            logger.info(f"Tracks total: {len(tracks)}, missing images: {len(tracks_missing_images)}")

            if tracks_missing_images:
                logger.info(f"Found {len(tracks_missing_images)} tracks missing images, searching Deezer...")
                deezer = DeezerService()

                async def fetch_track_image(track: RecommendedTrack):
                    try:
                        query = f"{track.artist} {track.name}"
                        results = await deezer.search(query, limit=5)

                        for result in results:
                            img = result.get("image_url")
                            if img:
                                track.image_url = img
                                logger.info(f"✓ Image found for: {track.name}")
                                return

                        logger.warning(f"✗ No image on Deezer for: {track.artist} - {track.name}")
                    except Exception as e:
                        logger.error(f"Deezer search error for {track.name}: {e}")

                # Process all missing images (up to 50)
                await asyncio.gather(*[fetch_track_image(t) for t in tracks_missing_images[:50]])

            # ------------------------------

            return tracks
        except LastfmError as e:
            logger.warning(f"Last.fm failed for user {user.id}: {e}")
            return []

    async def _search_deezer_playlists_for_artist(self, deezer: DeezerService, artist_name: str) -> list:
        results = []
        try:
            r1 = await deezer.search(f"This Is {artist_name}", limit=2)
            if r1:
                results.extend(r1)
            r2 = await deezer.search(f"{artist_name} Mix", limit=2)
            if r2:
                results.extend(r2)
        except Exception as e:
            logger.warning(f"Playlist search failed for {artist_name}: {e}")
        return results

    def _collect_unique_playlists(self, search_results: list) -> List[RecommendedPlaylist]:
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
                            url=f"https://www.deezer.com/track/{p['id']}",
                        )
                    )
                    seen_ids.add(p["id"])
        return playlists

    async def _fetch_playlists(self, user: User) -> List[RecommendedPlaylist]:
        """Fetch recommended playlists based on user's top artists."""
        if not self._user_has_lastfm(user):
            return []

        try:
            target_user = user.lastfm_username or user.username
            artists = await self.lastfm.get_user_top_artists(target_user, limit=5, period="1month")

            if not artists:
                recent = await self.lastfm.get_user_recent_tracks(target_user, limit=10)
                raw = [{"name": r.get("artist", {}).get("#text") or r.get("artist", {}).get("name")} for r in recent]
                artists = list({a["name"]: a for a in raw if a.get("name")}.values())[:5]

            if not artists:
                return []

            artist_names = [a.get("name") for a in artists if a.get("name")]
            logger.info(f"Fetching playlists for artists: {artist_names}")

            deezer = DeezerService()
            search_tasks = [self._search_deezer_playlists_for_artist(deezer, name) for name in artist_names]
            search_results = await asyncio.gather(*search_tasks)
            return self._collect_unique_playlists(search_results)[:15]
        except Exception as e:
            logger.error(f"Failed to fetch playlist recommendations: {e}")
            return []

    async def _fill_artist_image(self, deezer: DeezerService, artist: RecommendedArtist) -> None:
        try:
            results = await deezer.search(artist.name, limit=1)
            if results and results[0].get("image_url"):
                artist.image_url = results[0]["image_url"]
                return
            logger.warning(f"✗ No image on Deezer for artist: {artist.name}")
        except Exception as e:
            logger.error(f"Deezer artist search error for {artist.name}: {e}")

    async def _fetch_artists(self, user: User) -> List[RecommendedArtist]:
        """Fetch recommended artists with Spotify image fallback."""
        target_user = user.lastfm_username or user.username
        session_key = user.lastfm_session_key

        if not target_user:
            logger.info(f"User {user.id} has no Last.fm username or session for artist recommendations")
            return []

        try:
            logger.info(f"Fetching recommended artists for user {user.id} (lastfm_user: {target_user})")
            artists = await self.lastfm.get_recommended_artists(session_key, limit=20, user_name=target_user)
            logger.info(f"Fetched {len(artists)} recommended artists")

            for a in artists:
                a.image_url = None

            if artists:
                logger.info(f"Searching Deezer for images of {len(artists)} artists...")
                deezer = DeezerService()
                await asyncio.gather(*[self._fill_artist_image(deezer, a) for a in artists[:20]])
            return artists
        except Exception as e:
            logger.warning(f"Failed to fetch artists for user {user.id}: {e}")
            return []

    async def get_recommendations(
        self, user: User, source: str = "auto", force_refresh: bool = False
    ) -> RecommendationResponse:
        cache_key = f"rec:{user.id}"

        if not force_refresh:
            cached = await self._get_cached_recommendations(cache_key)
            if cached:
                return cached
        else:
            logger.info(f"Force refresh: clearing cache for user {user.id}")
            await self.cache.delete(cache_key)

        # 1. Fetch Tracks (Already implemented)
        tracks = await self._fetch_lastfm_recommendations(user, source)

        # 2. Fetch Artists
        artists = await self._fetch_artists(user)

        # 3. Fetch Playlists
        playlists = await self._fetch_playlists(user)

        used_source = "lastfm+deezer" if (tracks or artists or playlists) else "unknown"

        response = RecommendationResponse(
            tracks=tracks,
            artists=artists,
            playlists=playlists,
            source=used_source,
            cache_status="miss",
            lastfm_connected=self._user_has_lastfm(user),
            generated_at=datetime.now(),
        )

        if tracks or artists or playlists:
            logger.info(
                f"Caching recommendations for user {user.id}: {len(tracks)} tracks, "
                f"{len(artists)} artists, {len(playlists)} playlists"
            )
            try:
                await self.cache.set(cache_key, response.model_dump_json(), expire=86400)
            except Exception as e:
                logger.error(f"Failed to cache recommendations: {e}")
        else:
            logger.warning(f"No recommendations generated for user {user.id}")

        return response


recommendation_engine = HybridRecommendationEngine(LastfmService())
