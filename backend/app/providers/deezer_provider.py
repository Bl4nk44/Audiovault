from typing import List, Optional
from app.providers.base import MusicProvider
from app.schemas.metadata import PlaylistMetadata, TrackMetadata
from app.services.deezer_service import deezer_service
import re


class DeezerProvider(MusicProvider):
    @property
    def name(self) -> str:
        return "deezer"

    @property
    def domains(self) -> List[str]:
        return ["deezer.com", "www.deezer.com"]

    def can_handle(self, url: str) -> bool:
        return "deezer.com" in url

    async def extract_playlist(self, url: str) -> Optional[PlaylistMetadata]:
        # Parse URL to know what to call
        url_match = re.search(
            r"(?:https?://)?(?:www\.)?deezer\.com/(?:\w{2}/)?(track|album|playlist)/(\d+)",
            url,
        )
        if not url_match:
            return None

        kind, id = url_match.groups()
        tracks_data = []
        title = "Deezer Import"

        if kind == "playlist":
            tracks_data = await deezer_service.get_playlist_tracks(id)
            title = "Deezer Playlist"
        elif kind == "album":
            tracks_data = await deezer_service.get_album_tracks(id)
            title = "Deezer Album"
        elif kind == "track":
            t = await deezer_service.get_track(id)
            if t:
                tracks_data = [t]
            title = "Deezer Track"

        if not tracks_data:
            return None

        track_metadatas = []
        for t in tracks_data:
            track_metadatas.append(
                TrackMetadata(
                    title=t["title"],
                    artist=t["artist"],
                    album=t["album"],
                    duration_ms=t.get("duration_ms"),
                    image_url=t.get("image_url"),
                    source_id=t["id"],
                    source_url=f"https://deezer.com/track/{t['id']}",
                    source="deezer",
                )
            )

        return PlaylistMetadata(
            title=title,
            description="Imported from Deezer",
            author="Unknown",
            tracks=track_metadatas,
        )

    async def get_track(self, url: str) -> Optional[TrackMetadata]:
        # Reuse logic
        playlist = await self.extract_playlist(url)
        if playlist and playlist.tracks:
            return playlist.tracks[0]
        return None
