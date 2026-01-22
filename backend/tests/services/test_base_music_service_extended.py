"""
Extended tests for BaseMusicService to increase code coverage.
Tests base class functionality for generic music extraction.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.base_music_service import BaseMusicService


class TestMusicService(BaseMusicService):
    """Concrete implementation for testing."""
    
    def __init__(self):
        super().__init__()
        self.source_name = "test"
    
    def can_handle(self, url: str) -> bool:
        return "test.com" in url


@pytest.fixture
def base_service():
    """Create test implementation of BaseMusicService."""
    return TestMusicService()


# =============================================================================
# can_handle
# =============================================================================

def test_can_handle_base_class():
    """Test that base class raises NotImplementedError."""
    service = BaseMusicService()
    
    with pytest.raises(NotImplementedError):
        service.can_handle("http://example.com")


def test_can_handle_concrete_implementation(base_service):
    """Test concrete implementation of can_handle."""
    assert base_service.can_handle("https://test.com/track") is True
    assert base_service.can_handle("https://other.com/track") is False


# =============================================================================
# _extract_info
# =============================================================================

@pytest.mark.asyncio
async def test_extract_info_success(base_service):
    """Test successful info extraction."""
    mock_info = {"id": "123", "title": "Test"}
    
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = mock_info
        mock_ydl.return_value = mock_instance
        
        result = await base_service._extract_info("http://test.com/track")
        
        assert result == mock_info


@pytest.mark.asyncio
async def test_extract_info_with_extra_opts(base_service):
    """Test info extraction with extra options."""
    mock_info = {"id": "123"}
    
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = mock_info
        mock_ydl.return_value = mock_instance
        
        result = await base_service._extract_info("http://test.com/track", {"format": "best"})
        
        assert result == mock_info


@pytest.mark.asyncio
async def test_extract_info_error(base_service):
    """Test info extraction with error."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.side_effect = Exception("Error")
        
        result = await base_service._extract_info("http://test.com/track")
        
        assert result is None


# =============================================================================
# get_tracks
# =============================================================================

@pytest.mark.asyncio
async def test_get_tracks_single_track(base_service):
    """Test extracting single track."""
    mock_info = {
        "_type": "video",
        "id": "t1",
        "title": "Test Track",
        "artist": "Test Artist",
        "duration": 200,
        "thumbnail": "http://thumb.jpg"
    }
    
    with patch.object(base_service, "_extract_info", return_value=mock_info):
        tracks = await base_service.get_tracks("http://test.com/track")
        
        assert len(tracks) == 1
        assert tracks[0]["title"] == "Test Track"
        assert tracks[0]["artist"] == "Test Artist"
        assert tracks[0]["source"] == "test"


@pytest.mark.asyncio
async def test_get_tracks_playlist(base_service):
    """Test extracting playlist tracks."""
    mock_info = {
        "_type": "playlist",
        "title": "Playlist",
        "entries": [
            {"id": "1", "title": "T1", "uploader": "A", "duration": 100},
            {"id": "2", "title": "T2", "artist": "B", "duration": 150}
        ]
    }
    
    with patch.object(base_service, "_extract_info", return_value=mock_info):
        tracks = await base_service.get_tracks("http://test.com/playlist")
        
        assert len(tracks) == 2
        assert tracks[0]["artist"] == "A"  # Uses uploader
        assert tracks[1]["artist"] == "B"  # Uses artist


@pytest.mark.asyncio
async def test_get_tracks_no_info(base_service):
    """Test get_tracks when no info returned."""
    with patch.object(base_service, "_extract_info", return_value=None):
        tracks = await base_service.get_tracks("http://test.com/track")
        
        assert tracks == []


@pytest.mark.asyncio
async def test_get_tracks_null_entries(base_service):
    """Test get_tracks with null entries."""
    mock_info = {
        "_type": "playlist",
        "entries": [
            None,
            {"id": "1", "title": "Valid", "uploader": "A", "duration": 100},
            None
        ]
    }
    
    with patch.object(base_service, "_extract_info", return_value=mock_info):
        tracks = await base_service.get_tracks("http://test.com/playlist")
        
        assert len(tracks) == 1


@pytest.mark.asyncio
async def test_get_tracks_no_title(base_service):
    """Test get_tracks skips entries without title."""
    mock_info = {
        "_type": "playlist",
        "entries": [
            {"id": "1", "uploader": "A"},  # No title
            {"id": "2", "title": "Has Title", "uploader": "B"}
        ]
    }
    
    with patch.object(base_service, "_extract_info", return_value=mock_info):
        tracks = await base_service.get_tracks("http://test.com/playlist")
        
        assert len(tracks) == 1
        assert tracks[0]["title"] == "Has Title"


@pytest.mark.asyncio
async def test_get_tracks_fallback_artist(base_service):
    """Test artist fallback to Unknown Artist."""
    mock_info = {
        "id": "1",
        "title": "No Artist Track",
        "duration": 100
    }
    
    with patch.object(base_service, "_extract_info", return_value=mock_info):
        tracks = await base_service.get_tracks("http://test.com/track")
        
        assert tracks[0]["artist"] == "Unknown Artist"


@pytest.mark.asyncio
async def test_get_tracks_album_fallback(base_service):
    """Test album fallback to playlist title."""
    mock_info = {
        "_type": "playlist",
        "title": "Album Title",
        "entries": [
            {"id": "1", "title": "Track", "artist": "A", "duration": 100}
        ]
    }
    
    with patch.object(base_service, "_extract_info", return_value=mock_info):
        tracks = await base_service.get_tracks("http://test.com/album")
        
        assert tracks[0]["album"] == "Album Title"


# =============================================================================
# get_playlist_info
# =============================================================================

@pytest.mark.asyncio
async def test_get_playlist_info_success(base_service):
    """Test getting playlist info."""
    mock_info = {
        "_type": "playlist",
        "title": "My Playlist",
        "thumbnails": [{"url": "http://thumb.jpg"}],
        "playlist_count": 25
    }
    
    with patch.object(base_service, "_extract_info", return_value=mock_info):
        info = await base_service.get_playlist_info("http://test.com/playlist")
        
        assert info is not None
        assert info["title"] == "My Playlist"
        assert info["image_url"] == "http://thumb.jpg"
        assert info["track_count"] == 25


@pytest.mark.asyncio
async def test_get_playlist_info_count_from_entries(base_service):
    """Test playlist info with count from entries."""
    mock_info = {
        "_type": "playlist",
        "title": "Playlist",
        "entries": [{}, {}, {}]
    }
    
    with patch.object(base_service, "_extract_info", return_value=mock_info):
        info = await base_service.get_playlist_info("http://test.com/playlist")
        
        assert info["track_count"] == 3


@pytest.mark.asyncio
async def test_get_playlist_info_not_playlist(base_service):
    """Test get_playlist_info with non-playlist."""
    mock_info = {"_type": "video", "title": "Single"}
    
    with patch.object(base_service, "_extract_info", return_value=mock_info):
        info = await base_service.get_playlist_info("http://test.com/track")
        
        assert info is None


@pytest.mark.asyncio
async def test_get_playlist_info_no_info(base_service):
    """Test get_playlist_info when no info."""
    with patch.object(base_service, "_extract_info", return_value=None):
        info = await base_service.get_playlist_info("http://test.com/playlist")
        
        assert info is None


@pytest.mark.asyncio
async def test_get_playlist_info_no_thumbnails(base_service):
    """Test playlist info without thumbnails."""
    mock_info = {
        "_type": "playlist",
        "title": "No Thumb Playlist"
    }
    
    with patch.object(base_service, "_extract_info", return_value=mock_info):
        info = await base_service.get_playlist_info("http://test.com/playlist")
        
        assert info["image_url"] is None
