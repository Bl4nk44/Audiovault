from typing import List, Optional
from app.providers.base import MusicProvider
from app.schemas.metadata import PlaylistMetadata, TrackMetadata


class ProviderManager:
    def __init__(self):
        self.providers: List[MusicProvider] = []

    def register_provider(self, provider: MusicProvider):
        """Register a new provider instance"""
        self.providers.append(provider)

    def get_provider(self, url: str) -> Optional[MusicProvider]:
        """Find a provider that can handle the URL"""
        for provider in self.providers:
            if provider.can_handle(url):
                return provider
        return None

    def get_provider_by_name(self, name: str) -> Optional[MusicProvider]:
        """Find a provider by its name (e.g. 'spotify', 'tidal')"""
        for provider in self.providers:
            if provider.name == name:
                return provider
        return None

    async def extract_playlist(self, url: str) -> Optional[PlaylistMetadata]:
        provider = self.get_provider(url)
        if not provider:
            return None
        return await provider.extract_playlist(url)

    async def get_track(self, url: str) -> Optional[TrackMetadata]:
        provider = self.get_provider(url)
        if not provider:
            return None
        return await provider.get_track(url)


provider_manager = ProviderManager()
