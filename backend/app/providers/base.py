from abc import ABC, abstractmethod
from typing import List, Optional
from app.schemas.metadata import TrackMetadata, PlaylistMetadata

class MusicProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g. 'spotify', 'tidal', 'generic')"""
        pass

    @property
    @abstractmethod
    def domains(self) -> List[str]:
        """List of supported domains (e.g., ['spotify.com', 'open.spotify.com'])"""
        pass

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if this provider can handle the given URL"""
        pass

    @abstractmethod
    async def extract_playlist(self, url: str) -> Optional[PlaylistMetadata]:
        """Extract metadata from a playlist URL"""
        pass

    @abstractmethod
    async def get_track(self, url: str) -> Optional[TrackMetadata]:
        """Extract metadata from a single track URL"""
        pass
