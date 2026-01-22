"""
Extended tests for SyncManager service.
Covers: analyze_watchlist, execute_sync, soft_delete_file, fetch_remote_tracks.
"""
import pytest
import uuid
import os
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.sync_manager import SyncManager
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.models.track import Track
from app.models.download import Download
from sqlalchemy.future import select

@pytest.fixture
def sync_manager():
    return SyncManager()

@pytest.fixture
def mock_remote_tracks(sync_manager):
    """Mock the _fetch_remote_tracks method."""
    mock = AsyncMock()
    sync_manager._fetch_remote_tracks = mock
    return mock

# =============================================================================
# analyze_watchlist
# =============================================================================

@pytest.mark.asyncio
async def test_analyze_watchlist_no_changes(db_session, sync_manager, admin_user, mock_remote_tracks):
    """Test analysis when local and remote are in sync."""
    wl = Watchlist(user_id=admin_user.id, source_id="p1", source="spotify", source_name="Playlist")
    db_session.add(wl)
    await db_session.flush()

    track = Track(id=uuid.uuid4(), title="Track 1", spotify_id="s1")
    db_session.add(track)
    await db_session.flush()

    wli = WatchlistItem(watchlist_id=wl.id, track_id=track.id)
    db_session.add(wli)
    await db_session.commit()

    # Remote has same track
    mock_remote_tracks.return_value = [{"id": "s1", "title": "Track 1", "artist": "A"}]

    report = await sync_manager.analyze_watchlist(db_session, admin_user.id, wl.id)

    assert report["to_remove_count"] == 0
    assert report["to_add_count"] == 0
    assert report["safety_warning"] is False

@pytest.mark.asyncio
async def test_analyze_watchlist_removals(db_session, sync_manager, admin_user, mock_remote_tracks):
    """Test analysis detecting removals."""
    wl = Watchlist(user_id=admin_user.id, source_id="p1", source="spotify", source_name="Playlist")
    db_session.add(wl)
    await db_session.flush()

    # Local has 2 tracks
    t1 = Track(id=uuid.uuid4(), title="Keep", spotify_id="k1")
    t2 = Track(id=uuid.uuid4(), title="Remove", spotify_id="r1")
    db_session.add_all([t1, t2])
    await db_session.flush()

    db_session.add(WatchlistItem(watchlist_id=wl.id, track_id=t1.id))
    db_session.add(WatchlistItem(watchlist_id=wl.id, track_id=t2.id))
    await db_session.commit()

    # Remote only has "Keep"
    mock_remote_tracks.return_value = [{"id": "k1", "title": "Keep", "artist": "A"}]

    report = await sync_manager.analyze_watchlist(db_session, admin_user.id, wl.id)

    assert report["to_remove_count"] == 1
    assert report["to_remove_items"][0]["track_id"] == str(t2.id)

@pytest.mark.asyncio
async def test_analyze_watchlist_safety_warning(db_session, sync_manager, admin_user, mock_remote_tracks):
    """Test safety warning on mass deletion."""
    wl = Watchlist(user_id=admin_user.id, source_id="p1", source="spotify", source_name="Playlist")
    db_session.add(wl)
    await db_session.flush()

    # Local has 30 tracks
    for i in range(30):
        t = Track(id=uuid.uuid4(), title=f"T{i}", spotify_id=f"id{i}")
        db_session.add(t)
        await db_session.flush()
        db_session.add(WatchlistItem(watchlist_id=wl.id, track_id=t.id))
    await db_session.commit()

    # Remote empty
    mock_remote_tracks.return_value = []

    report = await sync_manager.analyze_watchlist(db_session, admin_user.id, wl.id)

    assert report["safety_warning"] is True
    # The "Remote empty" warning takes precedence in logic order
    assert "Remote playlist is empty" in report["warning_message"]

# =============================================================================
# execute_sync
# =============================================================================

@pytest.mark.asyncio
async def test_execute_sync_removal(db_session, sync_manager, admin_user):
    """Test partial removal execution."""
    wl = Watchlist(user_id=admin_user.id, source_id="p1", source="spotify")
    db_session.add(wl)
    await db_session.flush()

    t = Track(id=uuid.uuid4(), title="To Remove", spotify_id="r1")
    db_session.add(t)
    await db_session.flush()

    wli = WatchlistItem(watchlist_id=wl.id, track_id=t.id)
    db_session.add(wli)

    dl = Download(user_id=admin_user.id, track_id=t.id, status="completed", file_path="dummy.mp3")
    db_session.add(dl)
    await db_session.commit()

    # Setup pending report
    token = "token123"
    sync_manager._pending_reports[token] = {
        "watchlist_id": wl.id,
        "to_remove_items": [{"track_id": str(t.id)}]
    }

    # Mock soft delete to succeed
    with patch.object(sync_manager, "_soft_delete_file", return_value=True):
        with patch("os.path.exists", return_value=True):
            result = await sync_manager.execute_sync(db_session, admin_user.id, token, [t.id])

        assert result["status"] == "success"
        assert result["removed_from_playlist"] == 1
        assert result["files_soft_deleted"] == 1
        
        # Verify WLI removed
        res = await db_session.execute(select(WatchlistItem).where(WatchlistItem.track_id == t.id))
        assert res.scalar_one_or_none() is None

        # Verify Download removed (since no other refs)
        res = await db_session.execute(select(Download).where(Download.track_id == t.id))
        assert res.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_execute_sync_ref_counting(db_session, sync_manager, admin_user):
    """Test execution where track is kept because of other playlist."""
    # Two watchlists
    wl1 = Watchlist(user_id=admin_user.id, source_id="p1", source="spotify")
    wl2 = Watchlist(user_id=admin_user.id, source_id="p2", source="spotify")
    db_session.add_all([wl1, wl2])
    await db_session.flush()

    t = Track(id=uuid.uuid4(), title="Shared", spotify_id="s1")
    db_session.add(t)
    await db_session.flush()

    # Link to BOTH
    db_session.add(WatchlistItem(watchlist_id=wl1.id, track_id=t.id))
    db_session.add(WatchlistItem(watchlist_id=wl2.id, track_id=t.id))
    
    dl = Download(user_id=admin_user.id, track_id=t.id, status="completed")
    db_session.add(dl)
    await db_session.commit()

    # Sync Remove from wl1
    token = "token_ref"
    sync_manager._pending_reports[token] = {
        "watchlist_id": wl1.id,
        "to_remove_items": [{"track_id": str(t.id)}]
    }

    result = await sync_manager.execute_sync(db_session, admin_user.id, token, [t.id])

    assert result["removed_from_playlist"] == 1
    assert result["files_soft_deleted"] == 0  # Should NOT delete file
    
    # Download should still exist
    res = await db_session.execute(select(Download).where(Download.track_id == t.id))
    assert res.scalar_one_or_none() is not None

# =============================================================================
# Helper methods
# =============================================================================

def test_soft_delete_file(sync_manager):
    """Test file moving logic."""
    with patch("os.makedirs"):
        with patch("os.path.exists", return_value=True):
            with patch("shutil.move") as mock_move:
                result = sync_manager._soft_delete_file("path/to/file.mp3")
                assert result is True
                mock_move.assert_called()

def test_soft_delete_file_exception(sync_manager):
    """Test exception handling in soft delete."""
    with patch("shutil.move", side_effect=Exception("error")):
         with patch("os.path.exists", return_value=True):
            result = sync_manager._soft_delete_file("file.mp3")
            assert result is False
