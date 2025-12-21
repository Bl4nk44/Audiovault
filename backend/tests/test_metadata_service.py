import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.metadata_service import MetadataService
from app.models.artist import Artist
from app.models.album import Album
from app.models.track import Track

@pytest.mark.asyncio
async def test_fetch_and_save_metadata_creates_relations():
    # Setup mocks
    with patch('app.services.metadata_service.AsyncSessionLocal') as mock_session_cls:
        # We need a proper DB session mock or use a test DB. 
        # Since setting up test DB with alembic inside this environment is complex, 
        # we will use mocks to verify the logic flow (entity creation and add() calls).
        
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_db
        
        # Mock DB execute for check queries (return None so it creates new)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Mock SpotifyService
        with patch('app.services.metadata_service.SpotifyService') as MockSpotify:
            spotify_instance = MockSpotify.return_value
            spotify_instance.get_track.return_value = {
                "id": "spotify_id_123",
                "title": "Test Track",
                "artist": "Test Artist", # String from Spotify
                "album": "Test Album",
                "duration_ms": 1000,
                "image_url": "http://example.com/img.jpg",
                "popularity": 50,
                "isrc": "US12345"
            }
            
            service = MetadataService(mock_db)
            
            # Action
            track = await service.fetch_and_save_track_metadata("spotify", "spotify_id_123")
            
            # Verification
            # Check if Artist was added
            # MetadataService adds Artist, Album, Track to db
            
            # Since we mock db.add, we can inspect calls
            assert mock_db.add.call_count >= 3 
            
            # Check arguments to add
            added_objects = [call.args[0] for call in mock_db.add.call_args_list]
            
            artists = [o for o in added_objects if isinstance(o, Artist)]
            albums = [o for o in added_objects if isinstance(o, Album)]
            tracks = [o for o in added_objects if isinstance(o, Track)]
            
            assert len(artists) == 1
            assert artists[0].name == "Test Artist"
            
            assert len(albums) == 1
            assert albums[0].title == "Test Album"
            # assert albums[0].artist == artists[0] # Relation might be set
            
            assert len(tracks) == 1
            assert tracks[0].title == "Test Track"
            assert tracks[0].artist_rel == artists[0]
            assert tracks[0].album_rel == albums[0]

if __name__ == "__main__":
    print("Run with pytest")
