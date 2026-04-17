import os
import shutil
import uuid

import anyio
from unittest.mock import AsyncMock, patch

import pytest
from app.models.download import Download
from app.models.track import Track
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.services.sync_manager import SyncManager


@pytest.mark.asyncio
async def test_sync_manager_analyze_safety_warning(db_session):
    manager = SyncManager()
    user_id = uuid.uuid4()
    watchlist_id = uuid.uuid4()

    watchlist = Watchlist(
        id=watchlist_id, user_id=user_id, watch_type="playlist", source="spotify", source_name="Safety Test"
    )
    db_session.add(watchlist)

    # Add many local tracks
    for i in range(30):
        track = Track(id=uuid.uuid4(), title=f"Track {i}", spotify_id=f"s{i}")
        db_session.add(track)
        await db_session.flush()
        wi = WatchlistItem(watchlist_id=watchlist_id, track_id=track.id)
        db_session.add(wi)

    await db_session.commit()

    # Mock remote to return 0 tracks -> should trigger safety warning
    with patch.object(manager, "_fetch_remote_tracks", new_callable=AsyncMock) as mock_remote:
        mock_remote.return_value = []

        report = await manager.analyze_watchlist(db_session, user_id, watchlist_id)
        assert report["safety_warning"] is True
        assert "Remote playlist is empty" in report["warning_message"]


@pytest.mark.asyncio
async def test_sync_manager_execute_success(db_session):
    manager = SyncManager()
    user_id = uuid.uuid4()
    watchlist_id = uuid.uuid4()
    track_id = uuid.uuid4()

    # Setup report in internal state
    token = "test-token"
    manager._pending_reports[token] = {
        "watchlist_id": str(watchlist_id),
        "to_remove_items": [{"track_id": str(track_id)}],
    }

    # Setup DB
    wi = WatchlistItem(watchlist_id=watchlist_id, track_id=track_id)
    db_session.add(wi)

    # Setup download and file
    temp_dir = f"/tmp/sync_test_{uuid.uuid4()}"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, "test.mp3")
    await anyio.Path(file_path).write_text("test")

    download = Download(user_id=user_id, track_id=track_id, status="completed", file_path=file_path)
    db_session.add(download)
    await db_session.commit()

    # Mock settings.DOWNLOAD_DIR
    try:
        with patch("app.core.config.settings.DOWNLOAD_DIR", temp_dir):
            result = await manager.execute_sync(db_session, user_id, token, [str(track_id)])
            assert result["status"] == "success"
            assert result["removed_from_playlist"] == 1
            assert result["files_soft_deleted"] == 1

            # Verify file moved to .trash
            trash_dir = os.path.join(temp_dir, ".trash")
            assert os.path.exists(trash_dir)
            assert len(os.listdir(trash_dir)) == 1
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_soft_delete_fail(db_session):
    manager = SyncManager()
    # Test with non-existent dir or permission error
    with patch("app.core.config.settings.DOWNLOAD_DIR", "/non/existent/dir/at/all/hopefully"):
        result = manager._soft_delete_file("/any/path")
        assert result is False
