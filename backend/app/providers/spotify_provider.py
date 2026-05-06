from app.providers.base import MusicProvider
from app.schemas.metadata import PlaylistMetadata, TrackMetadata
from app.services.spotify_service import SpotifyService  # noqa: F401


class SpotifyProvider(MusicProvider):
    SPOTIFY_URI_PREFIX = "spotify:"
    SPOTIFY_DOMAIN = "spotify.com"

    def __init__(self):
        self.service = SpotifyService()

    @property
    def name(self) -> str:
        return "spotify"

    @property
    def domains(self) -> list[str]:
        return ["open.spotify.com", self.SPOTIFY_DOMAIN]

    def can_handle(self, url: str) -> bool:
        return any(domain in url for domain in self.domains) or url.startswith(self.SPOTIFY_URI_PREFIX)

    async def extract_playlist(self, url: str) -> PlaylistMetadata | None:
        import re

        playlist_id = url
        if self.SPOTIFY_DOMAIN in url or self.SPOTIFY_URI_PREFIX in url:
            match = re.search(r"playlist[:/]([a-zA-Z0-9_-]+)", url)
            if match:
                playlist_id = match.group(1)

        playlist_data = await self.service.get_playlist_details(playlist_id)
        if not playlist_data:
            return None

        tracks = []
        for t in playlist_data.get("tracks", []):
            tracks.append(
                TrackMetadata(
                    title=t.get("title", "Unknown"),
                    artist=t.get("artist", "Unknown"),
                    album=t.get("album", "Unknown"),
                    duration_ms=t.get("duration_ms", 0) or 0,
                    image_url=t.get("image_url"),
                    source="spotify",
                    source_id=t.get("id", ""),
                    isrc=t.get("isrc"),
                )
            )

        return PlaylistMetadata(
            title=playlist_data.get("title", "Unknown Playlist"),
            description=None,
            author=None,
            image_url=playlist_data.get("image_url"),
            tracks=tracks,
            source="spotify",
            source_id=playlist_data.get("id", ""),
        )

    async def get_track(self, url: str) -> TrackMetadata | None:
        import re

        track_id = url
        if self.SPOTIFY_DOMAIN in url or self.SPOTIFY_URI_PREFIX in url:
            match = re.search(r"track[:/]([a-zA-Z0-9_-]+)", url)
            if match:
                track_id = match.group(1)

        t = await self.service.get_track(track_id)
        if t:
            return TrackMetadata(
                title=t.get("title", "Unknown"),
                artist=t.get("artist", "Unknown"),
                album=t.get("album", "Unknown"),
                duration_ms=t.get("duration_ms", 0) or 0,
                image_url=t.get("image_url"),
                source="spotify",
                source_id=t.get("id", ""),
                isrc=t.get("isrc"),
            )
        return None
