"""
Additional tests for SyncManager to improve coverage.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.sync_manager import SyncManager


@pytest.fixture
def sync_mgr():
    return SyncManager()


# =============================================================================
# Soft Delete File
# =============================================================================


def test_soft_delete_file_success(sync_mgr):
    """Test successful soft delete moves file to trash."""
    file_path = "/downloads/test.mp3"

    with (
        patch("os.makedirs") as mock_makedirs,
        patch("shutil.move") as mock_move,
        patch("os.path.basename", return_value="test.mp3"),
    ):
        result = sync_mgr._soft_delete_file(file_path)

        assert result is True
        mock_makedirs.assert_called_once()
        mock_move.assert_called_once()


def test_soft_delete_file_failure(sync_mgr):
    """Test soft delete returns False on error."""
    file_path = "/downloads/test.mp3"

    with patch("os.makedirs", side_effect=Exception("Permission denied")):
        result = sync_mgr._soft_delete_file(file_path)
        assert result is False


# =============================================================================
# Fetch Remote Tracks
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_remote_tracks_playlist(sync_mgr):
    """Test fetching remote tracks for playlist."""
    watchlist = MagicMock()
    watchlist.watch_type = "playlist"
    watchlist.source = "spotify"
    watchlist.source_id = "playlist123"

    mock_track = MagicMock()
    mock_track.source_id = "track1"
    mock_track.title = "Song"
    mock_track.artist = "Artist"

    mock_metadata = MagicMock()
    mock_metadata.tracks = [mock_track]

    mock_provider = AsyncMock()
    mock_provider.extract_playlist.return_value = mock_metadata

    with patch("app.services.sync_manager.provider_manager.get_provider_by_name", return_value=mock_provider):
        tracks = await sync_mgr._fetch_remote_tracks(watchlist)

        assert len(tracks) == 1
        assert tracks[0]["id"] == "track1"


@pytest.mark.asyncio
async def test_fetch_remote_tracks_artist_spotify(sync_mgr):
    """Test fetching remote tracks for artist from Spotify."""
    watchlist = MagicMock()
    watchlist.watch_type = "artist"
    watchlist.source = "spotify"
    watchlist.source_id = "artist123"

    with patch("app.services.sync_manager.SpotifyService") as MockSpotify:
        instance = MockSpotify.return_value
        instance.get_artist_albums.return_value = [{"id": "album1"}]
        instance.get_album_tracks.return_value = [{"id": "t1", "title": "S1"}]

        tracks = await sync_mgr._fetch_remote_tracks(watchlist)

        assert len(tracks) == 1


@pytest.mark.asyncio
async def test_fetch_remote_tracks_channel_youtube(sync_mgr):
    """Test fetching remote tracks for YouTube channel."""
    watchlist = MagicMock()
    watchlist.watch_type = "channel"
    watchlist.source = "youtube"
    watchlist.source_id = "channel123"

    with patch("app.services.sync_manager.YouTubeService") as MockYT:
        instance = MockYT.return_value
        instance.get_artist_tracks.return_value = [{"id": "v1"}]

        tracks = await sync_mgr._fetch_remote_tracks(watchlist)

        # Returns the list directly
        assert tracks == [{"id": "v1"}]


@pytest.mark.asyncio
async def test_fetch_remote_tracks_error(sync_mgr):
    """Test fetch remote tracks handles errors gracefully."""
    watchlist = MagicMock()
    watchlist.watch_type = "playlist"
    watchlist.source = "spotify"

    with patch("app.services.sync_manager.provider_manager.get_provider_by_name", side_effect=Exception("API Error")):
        tracks = await sync_mgr._fetch_remote_tracks(watchlist)
        assert tracks == []


# =============================================================================
# Analyze Watchlist
# =============================================================================


@pytest.mark.asyncio
async def test_analyze_watchlist_not_found(sync_mgr):
    """Test analyze with non-existent watchlist."""
    db_mock = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db_mock.execute.return_value = mock_result

    with pytest.raises(ValueError, match="Watchlist not found"):
        await sync_mgr.analyze_watchlist(db_mock, str(uuid.uuid4()), str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_analyze_watchlist_high_deletion_warning(sync_mgr):
    """Test analyze generates safety warning for high deletion ratio."""
    db_mock = AsyncMock()

    # Mock watchlist
    watchlist = MagicMock()
    watchlist.id = uuid.uuid4()
    watchlist.source = "spotify"
    watchlist.source_name = "Test Playlist"
    watchlist.watch_type = "playlist"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = watchlist

    # Mock local items (10 items)
    local_items = []
    for i in range(10):
        item = MagicMock()
        item.track = MagicMock()
        item.track.id = uuid.uuid4()
        item.track.spotify_id = f"spotify_{i}"
        item.track.metadata_content = {}
        local_items.append(item)

    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = local_items

    db_mock.execute.side_effect = [mock_result, mock_items_result]

    # Remote has only 3 tracks matching
    with patch.object(
        sync_mgr, "_fetch_remote_tracks", return_value=[{"id": "spotify_0"}, {"id": "spotify_1"}, {"id": "spotify_2"}]
    ):
        report = await sync_mgr.analyze_watchlist(db_mock, str(uuid.uuid4()), str(watchlist.id))

        assert report["safety_warning"] is True
        assert report["to_remove_count"] == 7


# =============================================================================
# Execute Sync
# =============================================================================


@pytest.mark.asyncio
async def test_execute_sync_invalid_token(sync_mgr):
    """Test execute with invalid token raises error."""
    db_mock = AsyncMock()

    with pytest.raises(ValueError, match="Invalid or expired sync token"):
        await sync_mgr.execute_sync(db_mock, str(uuid.uuid4()), "bad_token", [])


@pytest.mark.asyncio
async def test_execute_sync_success(sync_mgr):
    """Test successful sync execution."""
    db_mock = AsyncMock()

    # Setup pending report
    token = "valid_token"
    sync_mgr._pending_reports[token] = {"watchlist_id": str(uuid.uuid4()), "to_remove_items": []}

    # Mock ref count = 0 (no other references)
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 0

    # Mock download
    mock_download = MagicMock()
    mock_download.file_path = "/downloads/file.mp3"
    mock_dl_result = MagicMock()
    mock_dl_result.scalar_one_or_none.return_value = mock_download

    db_mock.execute.side_effect = [
        MagicMock(),  # delete WatchlistItem
        mock_count_result,
        mock_dl_result,
    ]

    with patch.object(sync_mgr, "_soft_delete_file", return_value=True), patch("os.path.exists", return_value=True):
        result = await sync_mgr.execute_sync(db_mock, str(uuid.uuid4()), token, [str(uuid.uuid4())])

        assert result["status"] == "success"
        assert result["removed_from_playlist"] == 1
        assert token not in sync_mgr._pending_reports
