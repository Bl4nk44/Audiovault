import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.sync_manager import SyncManager
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.models.track import Track
from app.models.download import Download
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

@pytest.fixture
def sync_manager():
    return SyncManager()

@pytest.mark.asyncio
async def test_analyze_watchlist_success(sync_manager):
    watchlist_id = str(uuid.uuid4())
    user_id = "user123"
    watchlist = Watchlist(id=watchlist_id, user_id=user_id, source="spotify", source_name="My PL", watch_type="playlist")
    
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = watchlist
    
    track = Track(id=str(uuid.uuid4()), title="Local Song", artist="Artist", spotify_id="sp1")
    item = WatchlistItem(watchlist_id=watchlist_id, track=track)
    mock_local_res = MagicMock()
    mock_local_res.scalars.return_value.all.return_value = [item]
    
    db_mock = AsyncMock(spec=AsyncSession)
    db_mock.execute.side_effect = [mock_res, mock_local_res]
    
    with patch.object(SyncManager, "_fetch_remote_tracks", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [{"id": "sp2", "title": "Remote Song", "artist": "Artist"}]
        report = await sync_manager.analyze_watchlist(db_mock, user_id, watchlist_id)
        assert report["to_remove_count"] == 1

@pytest.mark.asyncio
async def test_execute_sync_success(sync_manager):
    user_id = "user123"
    token = "test_token"
    track_uuid = str(uuid.uuid4())
    
    sync_manager._pending_reports[token] = {"watchlist_id": "wl123", "to_remove_items": [{"track_id": track_uuid}]}
    
    db_mock = AsyncMock(spec=AsyncSession)
    m_ref = MagicMock()
    m_ref.scalar.return_value = 0
    m_dl = MagicMock()
    m_dl.scalar_one_or_none.return_value = Download(user_id=user_id, track_id=track_uuid, file_path="/tmp/s.mp3")
    
    db_mock.execute.side_effect = [MagicMock(), m_ref, m_dl]
    
    with patch.object(SyncManager, "_soft_delete_file", return_value=True), \
         patch("os.path.exists", return_value=True):
        res = await sync_manager.execute_sync(db_mock, user_id, token, [track_uuid])
        assert res["status"] == "success"
        assert res["removed_from_playlist"] == 1
        assert res["files_soft_deleted"] == 1

@pytest.mark.asyncio
async def test_soft_delete_file_logic(sync_manager):
    with patch("os.makedirs"), patch("shutil.move") as mock_move, patch("os.path.exists", return_value=True):
        res = sync_manager._soft_delete_file("/path/to/song.mp3")
        assert res is True
        assert mock_move.called
