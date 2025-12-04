from typing import Optional, Dict, Any, List
from app.models.track import Track
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class MetadataService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_track_metadata(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        Pobiera metadane utworu z bazy danych lub zewnętrznych serwisów.
        Na razie implementacja podstawowa oparta o bazę danych.
        """
        # Tutaj w przyszłości można dodać logikę odpytywania Spotify/YouTube
        # jeśli metadane w bazie są niepełne.
        
        query = select(Track).where(Track.id == track_id)
        result = await self.db.execute(query)
        track = result.scalar_one_or_none()
        
        if not track:
            return None
            
        return {
            "title": track.title,
            "artist": track.artist,
            "album": track.album,
            "duration_ms": track.duration_ms,
            "metadata": track.metadata,
            "sources": {
                "spotify": track.spotify_id,
                "youtube": track.youtube_id,
                "deezer": track.deezer_id
            }
        }

    async def search_metadata(self, query: str) -> List[Dict[str, Any]]:
        """
        Wyszukuje metadane (placeholder dla przyszłej integracji z MusicBrainz/Spotify).
        """
        # Placeholder
        return []

metadata_service = MetadataService
