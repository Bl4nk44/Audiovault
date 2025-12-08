from typing import Optional, Dict, Any, List
from app.models.track import Track
from app.models.artist import Artist
from app.models.album import Album
from app.services.spotify_service import SpotifyService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.db.database import AsyncSessionLocal
import logging

logger = logging.getLogger(__name__)

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

    async def fetch_and_save_track_metadata(self, source: str, external_id: str) -> Optional[Track]:
        """
        Fetches metadata from source, creates/updates Artist, Album, and Track in DB.
        Returns the Track object (persisted).
        """
        if source != 'spotify':
            # Currently only Spotify is robust enough for metadata
            # Fallback for others or implement Deezer later
            logger.warning(f"Metadata fetch not implemented for source: {source}")
            return None

        spotify = SpotifyService()
        track_data = spotify.get_track(external_id)
        
        if not track_data:
            logger.error(f"Could not fetch track data for {external_id} from {source}")
            return None
            
        # 1. Handle Artist
        # Spotify returns multiple artists, we usually take the first one as primary for linking
        # but storing string representation of all.
        primary_artist_name = track_data['artist'].split(', ')[0] 
        # API returns "artist": "Name1, Name2", logic above is simple split
        # Ideally we should get array from spotify_service but it returns formatted string currently.
        # Let's verify spotify_service._format_track output: 
        # "artist": ", ".join([artist['name'] for artist in item['artists']]),
        
        # We need raw artist ID to link properly if possible, but _format_track doesn't return list of artist objs with IDs.
        # We might need to fetch artist details or just fuzzy match by name if we don't have ID.
        # For better data quality, let's just use Name for now or improve SpotifyService later.
        
        # Check if artist exists by spotify_id or name
        # TODO: Add spotify_id to artist model and use that for lookup if we enhance SpotifyService (DONE)
        
        # Checking by ID then name
        artist = await self._get_or_create_artist(
            primary_artist_name, 
            spotify_id=track_data.get('artist_id'), 
            simple=True
        )
        
        # 2. Handle Album
        album_name = track_data['album']
        # Check by title AND artist to avoid collisions
        album = await self._get_or_create_album(album_name, artist, track_data.get('image_url'))
        
        # 3. Handle Track
        # Check if track exists by Spotify ID
        query = select(Track).where(Track.spotify_id == track_data['id'])
        result = await self.db.execute(query)
        track = result.scalar_one_or_none()
        
        if not track:
            track = Track(
                title=track_data['title'],
                artist=track_data['artist'], # String representation
                album=track_data['album'],   # String representation
                duration_ms=track_data['duration_ms'],
                spotify_id=track_data['id'],
                isrc=track_data.get('isrc'),
                metadata_content={
                    "image_url": track_data.get('image_url'),
                    "popularity": track_data.get('popularity'),
                    "source": "spotify"
                },
                artist_rel=artist,
                album_rel=album
            )
            self.db.add(track)
            logger.info(f"Created new track: {track.title} ({track.id})")
        else:
            # Update missing fields/relations if needed
            if not track.artist_rel:
                track.artist_rel = artist
            if not track.album_rel:
                track.album_rel = album
            logger.info(f"Updated existing track: {track.title} ({track.id})")
            
        await self.db.commit()
        await self.db.refresh(track)
        return track

    async def _get_or_create_artist(self, name: str, spotify_id: str = None, simple: bool = False) -> Artist:
        # Try to find by spotify_id first if provided
        artist = None
        if spotify_id:
            query = select(Artist).where(Artist.spotify_id == spotify_id)
            result = await self.db.execute(query)
            artist = result.scalar_one_or_none()

        if not artist:
            # Try to find by name (case insensitive ideally, but strict for now)
            query = select(Artist).where(Artist.name == name)
            result = await self.db.execute(query)
            artist = result.scalar_one_or_none()
            
            # If found by name but we have a spotify_id, update it
            if artist and spotify_id and not artist.spotify_id:
                artist.spotify_id = spotify_id
                self.db.add(artist)
                await self.db.flush()
        
        if not artist:
            artist = Artist(name=name, spotify_id=spotify_id)
            self.db.add(artist)
            # await self.db.commit() # Commit handled by caller usually or flush?
            # We need ID for Album creation so flush
            await self.db.flush()
        return artist

    async def _get_or_create_album(self, title: str, artist: Artist, image_url: str = None) -> Album:
        query = select(Album).where(Album.title == title, Album.artist_id == artist.id)
        result = await self.db.execute(query)
        album = result.scalar_one_or_none()
        
        if not album:
            album = Album(
                title=title,
                artist=artist,
                images={"cover": image_url} if image_url else {}
            )
            self.db.add(album)
            await self.db.flush()
        return album

    async def resolve_and_save_track(self, title: str, artist: str, album: str = None, image_url: str = None) -> Track:
        """
        Creates or returns an existing track based on basic metadata (without external ID).
        """
        # 1. Get or Create Artist
        artist_obj = await self._get_or_create_artist(artist, simple=True)
        
        # 2. Get or Create Album (optional)
        album_obj = None
        if album:
            album_obj = await self._get_or_create_album(album, artist_obj, image_url)
            
        # 3. Check if track exists
        # Using join to filter by related artist
        query = select(Track).join(Track.artist_rel).where(
            Track.title == title, 
            Artist.id == artist_obj.id
        )
        result = await self.db.execute(query)
        track = result.scalar_one_or_none()
        
        if not track:
            track = Track(
                title=title,
                artist=artist,
                album=album,
                metadata_content={
                    "image_url": image_url,
                    "source": "imported"
                },
                artist_rel=artist_obj,
                album_rel=album_obj
            )
            self.db.add(track)
            await self.db.flush() # Ensure ID is generated
            logger.info(f"Resolved new track: {title} by {artist}")
        else:
            logger.info(f"Resolved existing track: {title} by {artist}")
            
        await self.db.commit()
        await self.db.refresh(track)
        return track

metadata_service = MetadataService
