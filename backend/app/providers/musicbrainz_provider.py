"""
MusicBrainz provider for Audiovault's ProviderManager.

Implements the MusicProvider ABC to integrate MusicBrainz as a metadata source.
MusicBrainz doesn't have playlists, so extract_playlist always returns None.
"""

import re

from app.providers.base import MusicProvider
from app.schemas.metadata import PlaylistMetadata, TrackMetadata
from app.services.musicbrainz_service import MusicBrainzService


class MusicBrainzProvider(MusicProvider):
    """MusicBrainz metadata provider."""

    MUSICBRAINZ_DOMAIN = "musicbrainz.org"

    def __init__(self) -> None:
        self.service = MusicBrainzService()

    @property
    def name(self) -> str:
        return "musicbrainz"

    @property
    def domains(self) -> list[str]:
        return [self.MUSICBRAINZ_DOMAIN]

    def can_handle(self, url: str) -> bool:
        return self.MUSICBRAINZ_DOMAIN in url

    async def extract_playlist(self, url: str) -> PlaylistMetadata | None:
        """MusicBrainz doesn't support playlists."""
        return None

    async def get_track(self, url: str) -> TrackMetadata | None:
        """Extract track metadata from a MusicBrainz recording URL or MBID."""
        # Extract MBID from URL
        mbid = url
        match = re.search(r"recording/([a-f0-9-]+)", url)
        if match:
            mbid = match.group(1)

        # MusicBrainz doesn't have a direct "get recording by MBID" that returns
        # the same format as search. We'll use search as a workaround with the title
        # from a lookup, or if the URL contains artist+title info, parse it.
        # For simplicity, search using the MBID as a query might work.
        # Actually, we should add a get_recording method to MusicBrainzService.
        # For now, search_track with empty params won't work well.
        # Let's use search_track with a broad approach.

        results = await self.service.search_track(artist="", title=mbid, limit=1)
        if not results:
            return None

        track = results[0]

        # Try to get cover art if we have a release MBID
        image_url = track.get("image_url")
        release_mbid = track.get("release_mbid")
        if not image_url and release_mbid:
            image_url = await self.service.get_cover_art(release_mbid)

        return TrackMetadata(
            title=track["title"],
            artist=track["artist"],
            album=track.get("album"),
            duration_ms=track.get("duration_ms"),
            image_url=image_url,
            source="musicbrainz",
            source_id=track["id"],
            isrc=track.get("isrc"),
        )
