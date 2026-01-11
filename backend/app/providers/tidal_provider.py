from typing import List, Optional
from app.providers.base import MusicProvider
from app.schemas.metadata import PlaylistMetadata, TrackMetadata
from app.services.tidal_service import tidal_service


class TidalProvider(MusicProvider):
    @property
    def name(self) -> str:
        return "tidal"

    @property
    def domains(self) -> List[str]:
        return ["tidal.com", "listen.tidal.com"]

    def can_handle(self, url: str) -> bool:
        return tidal_service.can_handle(url)

    async def extract_playlist(self, url: str) -> Optional[PlaylistMetadata]:
        tracks = await tidal_service.get_tracks(url)
        if not tracks:
            return None

        # We need to map dicts to TrackMetadata
        track_metadatas = []
        for t in tracks:
            track_metadatas.append(
                TrackMetadata(
                    title=t["title"],
                    artist=t["artist"],
                    album=t["album"],
                    duration_ms=t["duration_ms"],
                    image_url=t["image_url"],
                    source_id=t["id"],
                    source_url=t.get("source_url"),
                    source="tidal",
                )
            )

        title = "Tidal Import"
        if track_metadatas:
            # In extract_flat album field often contains playlist title if it came from playlist URL
            if "playlist" in url:
                title = track_metadatas[0].album or "Tidal Playlist"
            else:
                title = track_metadatas[0].album or "Tidal Album"

        return PlaylistMetadata(
            title=title,
            description="Imported from Tidal",
            author="Unknown",
            tracks=track_metadatas,
        )

    async def get_track(self, url: str) -> Optional[TrackMetadata]:
        tracks = await tidal_service.get_tracks(url)
        if tracks:
            t = tracks[0]
            return TrackMetadata(
                title=t["title"],
                artist=t["artist"],
                album=t["album"],
                duration_ms=t["duration_ms"],
                image_url=t["image_url"],
                source_id=t["id"],
                source_url=t.get("source_url"),
                source="tidal",
            )
        return None
