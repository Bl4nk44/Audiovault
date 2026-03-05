"""
Tests for WatchlistItemProcessor.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.schemas.metadata import PlaylistMetadata, TrackMetadata
from app.services.watchlist.processor import WatchlistItemProcessor


@pytest.fixture
def mock_provider_manager():
    return MagicMock()


@pytest.fixture
def mock_spotify_service():
    return AsyncMock()


@pytest.fixture
def mock_youtube_service():
    return MagicMock()


@pytest.fixture
def processor(mock_provider_manager, mock_spotify_service, mock_youtube_service):
    return WatchlistItemProcessor(mock_provider_manager, mock_spotify_service, mock_youtube_service)


@pytest.mark.asyncio
async def test_fetch_playlist_tracks_success(processor, mock_provider_manager):
    # Setup
    item = MagicMock()
    item.watch_type = "playlist"
    item.source = "spotify"
    item.source_id = "playlist_id"

    mock_provider = AsyncMock()
    mock_provider_manager.get_provider_by_name.return_value = mock_provider

    track = TrackMetadata(
        source_id="t1",
        title="Track 1",
        artist="Artist 1",
        album="Album 1",
        duration_ms=1000,
        image_url="http://img.com",
        isrc="ISRC1",
        source_url="http://src.com",
    )
    mock_provider.extract_playlist.return_value = PlaylistMetadata(
        source_id="playlist_id", title="Playlist", tracks=[track]
    )

    # Execute
    tracks = await processor.fetch_tracks_for_item(item)

    # Assert
    assert len(tracks) == 1
    assert tracks[0]["title"] == "Track 1"
    assert tracks[0]["id"] == "t1"
    mock_provider_manager.get_provider_by_name.assert_called_with("spotify")
    mock_provider.extract_playlist.assert_called_with("playlist_id")


@pytest.mark.asyncio
async def test_fetch_playlist_tracks_no_provider(processor, mock_provider_manager):
    item = MagicMock()
    item.watch_type = "playlist"
    item.source = "unknown"
    mock_provider_manager.get_provider_by_name.return_value = None

    tracks = await processor.fetch_tracks_for_item(item)
    assert tracks == []


@pytest.mark.asyncio
async def test_fetch_spotify_artist_tracks(processor, mock_spotify_service):
    item = MagicMock()
    item.watch_type = "artist"
    item.source = "spotify"
    item.source_id = "artist_id"
    item.source_name = "Test Artist"

    mock_spotify_service.get_artist_albums.return_value = [{"id": "a1"}]
    mock_spotify_service.get_album_tracks.return_value = [{"id": "t1", "title": "S1", "artist": "test artist"}]

    tracks = await processor.fetch_tracks_for_item(item)

    assert len(tracks) == 1
    assert tracks[0]["id"] == "t1"
    mock_spotify_service.get_artist_albums.assert_called_with("artist_id")
    mock_spotify_service.get_album_tracks.assert_called_with("a1")


@pytest.mark.asyncio
async def test_fetch_youtube_artist_tracks(processor, mock_youtube_service):
    item = MagicMock()
    item.watch_type = "channel"
    item.source = "youtube"
    item.source_id = "channel_id"
    item.source_name = "Test Channel"

    mock_youtube_service.get_artist_tracks.return_value = [{"id": "t1", "title": "S1", "artist": "test channel"}]

    tracks = await processor.fetch_tracks_for_item(item)

    assert len(tracks) == 1
    assert tracks[0]["id"] == "t1"
    mock_youtube_service.get_artist_tracks.assert_called_with("channel_id")


@pytest.mark.asyncio
async def test_fetch_deezer_artist_not_implemented(processor):
    item = MagicMock()
    item.watch_type = "artist"
    item.source = "deezer"

    tracks = await processor.fetch_tracks_for_item(item)
    assert tracks == []


@pytest.mark.asyncio
async def test_fetch_tracks_error_handling(processor, mock_provider_manager):
    item = MagicMock()
    item.watch_type = "playlist"
    item.source = "spotify"
    item.source_name = "Test Item"

    mock_provider_manager.get_provider_by_name.side_effect = Exception("Boom")

    tracks = await processor.fetch_tracks_for_item(item)
    assert tracks == []


@pytest.mark.asyncio
async def test_fetch_playlist_empty_metadata(processor, mock_provider_manager):
    """Test when provider returns None for playlist metadata."""
    item = MagicMock()
    item.watch_type = "playlist"
    item.source = "spotify"

    mock_provider = AsyncMock()
    mock_provider_manager.get_provider_by_name.return_value = mock_provider
    mock_provider.extract_playlist.return_value = None  # Provider returns None

    tracks = await processor.fetch_tracks_for_item(item)
    assert tracks == []


@pytest.mark.asyncio
async def test_fetch_playlist_malformed_track(processor, mock_provider_manager):
    """Test handling of tracks with missing essential fields (simulated via Mock)."""
    item = MagicMock()
    item.watch_type = "playlist"
    item.source = "spotify"
    item.source_name = "Bad Playlist"

    mock_provider = AsyncMock()
    mock_provider_manager.get_provider_by_name.return_value = mock_provider

    # Simulate a Metadata object that returns a track missing 'source_id'
    # We use a Mock object that LOOKS like PlaylistMetadata to bypass Pydantic validation in test setup
    malformed_metadata = MagicMock()
    malformed_track = MagicMock()
    # Ensure accessing source_id raises AttributeError or returns None if strictly checked?
    # The code accesses it directly: t.source_id
    # We want to simulate it MISSING.
    del malformed_track.source_id

    malformed_metadata.tracks = [malformed_track]
    mock_provider.extract_playlist.return_value = malformed_metadata

    # The processor wraps execution in try/except Exception
    # Accessing malformed_track.source_id should raise AttributeError

    tracks = await processor.fetch_tracks_for_item(item)
    assert tracks == []  # Should be empty due to exception catch inside fetch_tracks_for_item


@pytest.mark.asyncio
async def test_fetch_artist_spotify_sync_mock(processor, mock_spotify_service):
    """Verify Spotify service calls are handled correctly."""
    item = MagicMock()
    item.watch_type = "artist"
    item.source = "spotify"
    item.source_id = "a1"
    item.source_name = "Test Artist"

    mock_spotify_service.get_artist_albums.return_value = [{"id": "alb1"}]
    mock_spotify_service.get_album_tracks.return_value = [{"id": "t1", "title": "T1", "artist": "test artist"}]

    tracks = await processor.fetch_tracks_for_item(item)
    assert len(tracks) == 1
    assert tracks[0]["id"] == "t1"
