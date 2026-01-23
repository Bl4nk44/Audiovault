import re

from app.providers.base import MusicProvider
from app.schemas.metadata import PlaylistMetadata, TrackMetadata
from app.services.youtube_service import YouTubeService


class YouTubeProvider(MusicProvider):
    def __init__(self):
        self.service = YouTubeService()

    @property
    def name(self) -> str:
        return "youtube"

    @property
    def domains(self) -> list[str]:
        return ["youtube.com", "youtu.be", "music.youtube.com"]

    def can_handle(self, url: str) -> bool:
        return any(domain in url for domain in self.domains)

    async def extract_playlist(self, url: str) -> PlaylistMetadata | None:
        # Handle ID or URL
        playlist_id = url
        match = re.search(r"[?&]list=([a-zA-Z0-9_-]+)", url)
        if match:
            playlist_id = match.group(1)

        # Get playlist details using YouTubeService
        playlist_data = self.service.get_playlist_details(playlist_id)

        if not playlist_data:
            return None

        tracks = []
        for t in playlist_data.get("tracks", []):
            tracks.append(
                TrackMetadata(
                    title=t["title"],
                    artist=t["artist"],
                    album=t["album"],
                    duration_ms=t["duration_ms"],
                    image_url=t["image_url"],
                    source="youtube",
                    source_id=t["id"],
                    source_url=f"https://www.youtube.com/watch?v={t['id']}",
                )
            )

        return PlaylistMetadata(
            title=playlist_data.get("title", "Unknown Playlist"),
            description=playlist_data.get("description"),
            author=None,
            image_url=playlist_data.get("image_url"),
            tracks=tracks,
            source="youtube",
            source_id=playlist_id,
        )

    async def get_track(self, url: str) -> TrackMetadata | None:
        # Not implemented for generic YT link yet, usually used for search
        # But if needed:
        return None
