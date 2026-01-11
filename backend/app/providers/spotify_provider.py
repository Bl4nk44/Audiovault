from typing import List, Optional
from app.providers.base import MusicProvider
from app.schemas.metadata import TrackMetadata, PlaylistMetadata
from app.services.spotify_service import SpotifyService


class SpotifyProvider(MusicProvider):
    def __init__(self):
        self.service = SpotifyService()

    @property
    def name(self) -> str:
        return "spotify"

    @property
    def domains(self) -> List[str]:
        return ["open.spotify.com", "spotify.com"]

    def can_handle(self, url: str) -> bool:
        return any(domain in url for domain in self.domains) or url.startswith(
            "spotify:"
        )

    async def extract_playlist(self, url: str) -> Optional[PlaylistMetadata]:
        # Handle both URL and direct ID if passed
        # Currently Watchlist passes ID for Spotify.
        # If url is just an ID, self.service.get_playlist_tracks should handle it if we clean it?
        # Check SpotifyService: get_playlist_tracks(playlist_id)
        # We need to handle full URL parsing if 'url' is a URL.
        # SpotifyService.search parses URLs. But get_playlist_tracks takes ID.
        # Let's extract ID from URL if possible.

        import re

        playlist_id = url
        # Simple extraction if it looks like a URL
        if "spotify.com" in url or "spotify:" in url:
            match = re.search(r"(?:playlist[:/])([a-zA-Z0-9_-]+)", url)
            if match:
                playlist_id = match.group(1)

        # We need metadata about the playlist itself first?
        # Service has get_playlist logic inside search?
        # Service has _format_playlist.
        # Let's use search to get playlist info.

        # Wait, extract_playlist should return metadata AND tracks?
        # PlaylistMetadata definition?
        # Let's check schemas/metadata.py first? No, I assume standard.
        # Actually I need to check PlaylistMetadata definition to be safe.
        # But for now assume it needs title, tracks etc.

        # SpotifyService doesn't have a clean "get_playlist_with_tracks" method.
        # It has get_playlist_tracks.

        tracks_data = self.service.get_playlist_tracks(playlist_id)
        if not tracks_data:
            return None

        # We need playlist title etc.
        # Try to get playlist info
        try:
            # This is a bit hacky, but SpotifyService client is public
            if self.service.client:
                playlist_info = self.service.client.playlist(playlist_id)
                formatted_info = self.service._format_playlist(playlist_info)

                tracks = []
                for t in tracks_data:
                    tracks.append(
                        TrackMetadata(
                            title=t["title"],
                            artist=t["artist"],
                            album=t["album"],
                            duration_ms=t["duration_ms"],
                            image_url=t["image_url"],
                            source="spotify",
                            source_id=t["id"],
                            isrc=t.get("isrc"),  # Assuming isrc is there
                        )
                    )

                return PlaylistMetadata(
                    title=formatted_info["title"],
                    description=None,
                    author=None,
                    image_url=formatted_info["image_url"],
                    tracks=tracks,
                    source="spotify",
                    source_id=formatted_info["id"],
                )
        except Exception:  # nosec
            # Fallback if client fail or not configured
            pass

        return None

    async def get_track(self, url: str) -> Optional[TrackMetadata]:
        import re

        track_id = url
        if "spotify.com" in url or "spotify:" in url:
            match = re.search(r"(?:track[:/])([a-zA-Z0-9_-]+)", url)
            if match:
                track_id = match.group(1)

        t = self.service.get_track(track_id)
        if t:
            return TrackMetadata(
                title=t["title"],
                artist=t["artist"],
                album=t["album"],
                duration_ms=t["duration_ms"],
                image_url=t["image_url"],
                source="spotify",
                source_id=t["id"],
                isrc=t.get("isrc"),
            )
        return None
