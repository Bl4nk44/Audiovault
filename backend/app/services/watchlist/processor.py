import logging

from app.services.spotify_service import SpotifyService
from app.services.youtube_service import YouTubeService

logger = logging.getLogger(__name__)


class WatchlistItemProcessor:
    def __init__(
        self,
        provider_manager,
        spotify_service: SpotifyService,
        youtube_service: YouTubeService,
    ):
        self.provider_manager = provider_manager
        self.spotify_service = spotify_service
        self.youtube_service = youtube_service

    async def fetch_tracks_for_item(self, item) -> list:
        """Fetch tracks from the appropriate provider for a given watchlist item."""
        try:
            if item.watch_type == "playlist":
                return await self._fetch_playlist_tracks(item)
            elif item.watch_type in ["artist", "channel"]:
                return await self._fetch_artist_or_channel_tracks(item)
        except Exception as e:
            logger.error(f"Error fetching tracks for item {item.source_name}: {e}")
        return []

    async def _fetch_playlist_tracks(self, item) -> list:
        provider = self.provider_manager.get_provider_by_name(item.source)
        if not provider:
            logger.warning(f"No provider found for source: {item.source}")
            return []

        playlist_metadata = await provider.extract_playlist(item.source_id)
        tracks = []
        if playlist_metadata and playlist_metadata.tracks:
            for t in playlist_metadata.tracks:
                tracks.append(
                    {
                        "id": t.source_id,
                        "title": t.title,
                        "artist": t.artist,
                        "album": t.album,
                        "duration_ms": t.duration_ms,
                        "image_url": t.image_url,
                        "isrc": t.isrc,
                        "source_url": t.source_url,
                    }
                )
        return tracks

    async def _fetch_artist_or_channel_tracks(self, item) -> list:
        tracks = []
        target_artist = str(item.source_name).lower() if item.source_name else ""

        if item.source == "spotify":
            # Run sync method in executor if it blocks, but here we just wrap it
            albums = await self.spotify_service.get_artist_albums(item.source_id) or []
            for album in albums:
                album_id = album.get("id")
                if not album_id:
                    continue
                # Potentially strictly sync, might block loop but ok for now
                album_tracks = await self.spotify_service.get_album_tracks(str(album_id)) or []
                for t in album_tracks:
                    t_artist = t.get("artist") or ""
                    if not target_artist or target_artist in t_artist.lower():
                        tracks.append(t)
        elif item.source == "youtube":
            raw_tracks = self.youtube_service.get_artist_tracks(item.source_id) or []
            for t in raw_tracks:
                t_artist = t.get("artist") or ""
                if not target_artist or target_artist in t_artist.lower():
                    tracks.append(t)
        elif item.source == "deezer":
            logger.warning(f"Deezer artist fetching not implemented for {item.source_id}")
        return tracks
