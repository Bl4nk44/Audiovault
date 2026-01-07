from typing import List, Optional
from app.providers.base import MusicProvider
from app.schemas.metadata import PlaylistMetadata, TrackMetadata
from app.services.amazon_music_service import amazon_music_service


class AmazonMusicProvider(MusicProvider):
    @property
    def name(self) -> str:
        return "amazon_music"

    @property
    def domains(self) -> List[str]:
        return [
            "music.amazon.com",
            "amazon.com",
            "music.amazon.co.uk",
            "music.amazon.de",
            "music.amazon.jp",
        ]

    def can_handle(self, url: str) -> bool:
        return amazon_music_service.can_handle(url)

    async def extract_playlist(self, url: str) -> Optional[PlaylistMetadata]:
        tracks = await amazon_music_service.get_tracks(url)
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
                    source="amazon_music",
                )
            )

        title = "Amazon Music Import"
        if track_metadatas:
            # In extract_flat album field often contains playlist title if it came from playlist URL
            if (
                "playlist" in url or "albums" in url
            ):  # Amazon URLs often have /albums/ or /playlists/
                title = track_metadatas[0].album or "Amazon Music Playlist"
            else:
                title = track_metadatas[0].album or "Amazon Music Album"

        return PlaylistMetadata(
            title=title,
            description="Imported from Amazon Music",
            author="Unknown",
            tracks=track_metadatas,
        )

    async def get_track(self, url: str) -> Optional[TrackMetadata]:
        tracks = await amazon_music_service.get_tracks(url)
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
                source="amazon_music",
            )
        return None
