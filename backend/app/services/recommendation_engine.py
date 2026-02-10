import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional

from app.core.cache import cache_manager
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse, RecommendedPlaylist, RecommendedTrack
from app.services.lastfm_service import LastfmError, LastfmService
from app.services.spotify_service import SpotifyService

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
                logger.info(f"Found {len(tracks_missing_images)} tracks missing images, searching Spotify...")
                spotify = SpotifyService()

                async def fetch_spotify_image(track: RecommendedTrack):
                    try:
                        # Broaden search - try multiple results
                        query = f"{track.artist} {track.name}"
                        results = await asyncio.to_thread(spotify.search, query, limit=5, type="track")

                        for result in results:
                            img = result.get("image_url")
                            if img:
                                track.image_url = img
                                logger.info(f"✓ Image found for: {track.name}")
                                return

                        logger.warning(f"✗ No image on Spotify for: {track.artist} - {track.name}")
                    except Exception as e:
                        logger.error(f"Spotify search error for {track.name}: {e}")

                # Process all missing images (up to 50)
                await asyncio.gather(*[fetch_spotify_image(t) for t in tracks_missing_images[:50]])

            # ------------------------------

            return tracks
        except LastfmError as e:
            logger.warning(f"Last.fm failed for user {user.id}: {e}")
            return []

    async def _fetch_playlists(self, user: User) -> List[RecommendedPlaylist]:
        """Fetch recommended playlists based on user's top artists."""
        if not self._user_has_lastfm(user):
            return []

        try:
            target_user = user.lastfm_username or user.username
            # Use Top Artists instead of Tags for better relevance
            # Tags often result in generic or regionally irrelevant lists (e.g. "Mix" -> "Uzbek Mix")
            artists = await self.lastfm.get_user_top_artists(target_user, limit=5, period="1month")

            if not artists:
                # Fallback to recent tracks artists if no top artists (new account)
                recent = await self.lastfm.get_user_recent_tracks(target_user, limit=10)
                artists = [
                    {"name": r.get("artist", {}).get("#text") or r.get("artist", {}).get("name")} for r in recent
                ]
                # Deduplicate preserving order
                seen = set()
                deduped = []
                for a in artists:
                    name = a.get("name")
                    if name and name not in seen:
                        deduped.append(a)
                        seen.add(name)
                artists = deduped[:5]

            if not artists:
                return []

            artist_names = [a.get("name") for a in artists if a.get("name")]
            logger.info(f"Fetching playlists for artists: {artist_names}")

            spotify = SpotifyService()
            playlists = []

            async def search_artist_playlists(artist_name):
                # Search for "This Is {Artist}" (Spotify Official) or "{Artist} Mix"
                # We try two queries to get good coverage
                results = []
                try:
                    # 1. "This Is {Artist}" - High quality official playlists
                    q1 = f"This Is {artist_name}"
                    r1 = await asyncio.to_thread(spotify.search, q1, limit=2, type="playlist")
                    if r1:
                        results.extend(r1)

                    # 2. "{Artist} Mix" - Good algorithmic playlists
                    q2 = f"{artist_name} Mix"
                    r2 = await asyncio.to_thread(spotify.search, q2, limit=2, type="playlist")
                    if r2:
                        results.extend(r2)
                except Exception as e:
                    logger.warning(f"Playlist search failed for {artist_name}: {e}")
                return results

            search_tasks = [search_artist_playlists(name) for name in artist_names]
            search_results = await asyncio.gather(*search_tasks)

            seen_ids = set()
            for results in search_results:
                for p in results:
                    if p["id"] not in seen_ids:
                        # Basic filtering to avoid completely irrelevant stuff
                        # (e.g. strict name check is hard, but we trust Spotify search relevance for specific queries)
                        playlists.append(
                            RecommendedPlaylist(
                                id=p["id"],
                                title=p["title"],
                                image_url=p.get("image_url"),
                                track_count=p.get("track_count", 0),
                                source="spotify",
                                url=f"https://open.spotify.com/playlist/{p['id']}",
                            )
                        )
                        seen_ids.add(p["id"])

            return playlists[:15]
        except Exception as e:
            logger.error(f"Failed to fetch playlist recommendations: {e}")
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
        artists = []
        target_user = user.lastfm_username or user.username
        session_key = user.lastfm_session_key

        if target_user:
            try:
                logger.info(f"Fetching recommended artists for user {user.id} (lastfm_user: {target_user})")
                # Update service method to handle username even if session_key is None
                artists = await self.lastfm.get_recommended_artists(session_key, limit=20, user_name=target_user)
                logger.info(f"Fetched {len(artists)} recommended artists")

                # FORCE SPOTIFY IMAGES: Last.fm images are unreliable/deprecated for artists.
                # We intentionally clear any image provided by Last.fm and force a new search.
                for a in artists:
                    a.image_url = None

                artists_missing_images = artists  # All of them

                if artists_missing_images:
                    logger.info(f"Forcing Spotify image search for {len(artists_missing_images)} artists...")
                    spotify = SpotifyService()

                    async def fetch_artist_image(artist):
                        try:
                            results = await asyncio.to_thread(spotify.search, artist.name, limit=1, type="artist")
                            if results and len(results) > 0:
                                img = results[0].get("image_url")
                                if img:
                                    artist.image_url = img
                                    # logger.info(f"✓ Artist image found for: {artist.name}")
                                    return
                            logger.warning(f"✗ No image on Spotify for artist: {artist.name}")
                        except Exception as e:
                            logger.error(f"Spotify artist search error for {artist.name}: {e}")

                    # Process all artists (up to 20)
                    await asyncio.gather(*[fetch_artist_image(a) for a in artists_missing_images[:20]])

            except Exception as e:
                logger.warning(f"Failed to fetch artists for user {user.id}: {e}")

        else:
            logger.info(f"User {user.id} has no Last.fm username or session for artist recommendations")

        # 3. Fetch Playlists
        playlists = await self._fetch_playlists(user)

        used_source = "lastfm+spotify" if (tracks or artists or playlists) else "unknown"

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
