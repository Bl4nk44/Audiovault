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

    def _matches_target_artist(self, track: dict, target_artist: str) -> bool:
        return not target_artist or target_artist in (track.get("artist") or "").lower()

    async def _fetch_spotify_artist_tracks(self, source_id: str, target_artist: str) -> list:
        tracks = []
        for album in await self.spotify_service.get_artist_albums(source_id) or []:
            album_id = album.get("id")
            if not album_id:
                continue
            for t in await self.spotify_service.get_album_tracks(str(album_id)) or []:
                if self._matches_target_artist(t, target_artist):
                    tracks.append(t)
        return tracks

    async def _fetch_artist_or_channel_tracks(self, item) -> list:
        target_artist = str(item.source_name).lower() if item.source_name else ""
        if item.source == "spotify":
            return await self._fetch_spotify_artist_tracks(item.source_id, target_artist)
        if item.source == "youtube":
            tracks = self.youtube_service.get_artist_tracks(item.source_id) or []
            return [t for t in tracks if self._matches_target_artist(t, target_artist)]
        if item.source == "deezer":
            logger.warning(f"Deezer artist fetching not implemented for {item.source_id}")
        return []
