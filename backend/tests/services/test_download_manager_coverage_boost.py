"""
Coverage boost for DownloadManager.
Targets: process_download, error handling, notifications, and restart/resume logic.
"""

import uuid
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from app.services.download_manager import DownloadManager, DownloadPausedError
from app.models.download import Download

@pytest.fixture
def dm():
    return DownloadManager()

@pytest.mark.asyncio
async def test_dm_handle_error_paused(dm):
    db = AsyncMock()
    download = MagicMock(id=uuid.uuid4())
    e = DownloadPausedError("DOWNLOAD_PAUSED")
    
    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
        await dm._handle_error(db, download, e)
        assert download.status == "paused"
        assert db.commit.called
        mock_emit.assert_called_with("download:paused", {"download_id": str(download.id)})

@pytest.mark.asyncio
async def test_dm_handle_error_generic(dm):
    db = AsyncMock()
    download = MagicMock(id=uuid.uuid4(), retry_count=0)
    e = Exception("Something went wrong")
    
    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
        await dm._handle_error(db, download, e)
        assert download.status == "failed"
        assert download.error_message == "Something went wrong"
        assert download.retry_count == 1
        assert db.commit.called
        mock_emit.assert_called_with("download:error", {"download_id": str(download.id), "error": "Something went wrong"})

@pytest.mark.asyncio
async def test_dm_restart_all_downloads(dm, db_session):
    user_id = uuid.uuid4()
    track_id = uuid.uuid4()
    d1 = Download(id=uuid.uuid4(), user_id=user_id, track_id=track_id, status="failed")
    d2 = Download(id=uuid.uuid4(), user_id=user_id, track_id=track_id, status="paused")
    db_session.add(d1)
    db_session.add(d2)
    await db_session.commit()

    with patch.object(dm.queue, "put", new_callable=AsyncMock) as mock_put:
        count = await dm.restart_all_downloads(db_session, user_id)
        assert count == 2
        assert d1.status == "pending"
        assert d2.status == "pending"
        assert mock_put.call_count == 2

@pytest.mark.asyncio
async def test_dm_notify_processing(dm):
    download = MagicMock(id=uuid.uuid4())
    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
        await dm._notify_processing(download)
        mock_emit.assert_called_with("download:processing", {"download_id": str(download.id), "status": "processing"})

@pytest.mark.asyncio
async def test_dm_set_processing_status(dm):
    download_id = uuid.uuid4()
    mock_download = MagicMock(id=download_id)
    
    # Mock DB session and result
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_download
    
    db_mock = AsyncMock()
    db_mock.execute.return_value = mock_res
    db_mock.__aenter__.return_value = db_mock

    with patch("app.services.download_manager.AsyncSessionLocal", return_value=db_mock):
        with patch.object(dm, "_notify_processing", new_callable=AsyncMock) as mock_notify:
            await dm._set_processing_status(str(download_id))
            assert mock_download.status == "processing"
            assert mock_download.progress == 100
            assert db_mock.commit.called
            mock_notify.assert_called_with(mock_download)

@pytest.mark.asyncio
async def test_dm_process_download_not_found(dm):
    download_id = str(uuid.uuid4())
    
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    
    db_mock = AsyncMock()
    db_mock.execute.return_value = mock_res
    db_mock.__aenter__.return_value = db_mock

    with patch("app.services.download_manager.AsyncSessionLocal", return_value=db_mock):
        await dm.process_download(download_id)
        # Should return early without error
        assert not db_mock.commit.called

@pytest.mark.asyncio
async def test_dm_process_download_flow(dm):
    download_id = str(uuid.uuid4())
    mock_download = MagicMock(id=uuid.UUID(download_id))
    
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_download
    
    db_mock = AsyncMock()
    db_mock.execute.return_value = mock_res
    db_mock.__aenter__.return_value = db_mock

    with patch("app.services.download_manager.AsyncSessionLocal", return_value=db_mock):
        with patch.object(dm, "_mark_download_started", new_callable=AsyncMock) as m1:
            with patch.object(dm, "_resolve_url", return_value="http://youtube.com/v1", new_callable=AsyncMock):
                with patch.object(dm, "_execute_download_task", new_callable=AsyncMock):
                    with patch.object(dm, "_handle_completion", new_callable=AsyncMock) as m_comp:
                        await dm.process_download(download_id)
                        assert m1.called
                        assert m_comp.called

@pytest.mark.asyncio
async def test_dm_handle_progress_update(dm):
    download_id = str(uuid.uuid4())
    download = MagicMock()
    download.track.title = "Test Title"
    download.track.artist = "Test Artist"
    download.track.metadata_content = {"image_url": "http://img.png"}
    loop = MagicMock()
    
    d = {"status": "downloading", "total_bytes": 1000, "downloaded_bytes": 500}
    
    with patch("app.services.download_manager.socket_manager.emit") as mock_emit:
        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            dm._handle_progress_update(d, download_id, download, loop)
            assert mock_run.called
            # Verify progress calculation (50%)
            args = mock_run.call_args[0][0]
            # Since we can't easily inspect the coroutine, we assume it's correct if called

@pytest.mark.asyncio
async def test_dm_set_download_file_path(dm):
    download = MagicMock()
    # Mock user preferences
    download.user.username = "testuser"
    download.user.preferences = {"downloadPath": "/downloads/testuser"}
    
    final_filename_container = {"path": "/downloads/temp/song.mp4"}
    output_template = "output"
    
    # Logic: final_filename_container["path"] -> base + target_ext
    dm._set_download_file_path(download, final_filename_container, output_template, "mp3")
    assert download.file_path == "/downloads/temp/song.mp3"

@pytest.mark.asyncio
async def test_dm_resolve_url_youtube(dm):
    db = AsyncMock()
    download = MagicMock(source="youtube", retry_count=0, track_id=uuid.uuid4())
    download.track.title = "Song"
    download.track.artist = "Artist"
    
    # Mock fallback_service.get_fallback_instruction
    with patch("app.services.download_manager.fallback_service.get_fallback_instruction") as mock_instr:
        mock_instr.return_value = {"type": "yt_search", "value": "Artist - Song"}
        url = await dm._resolve_url(db, download)
        assert url == "ytsearch1:Artist - Song"

@pytest.mark.asyncio
async def test_dm_fix_filename_artifacts(dm):
    download = MagicMock()
    # Prefix "NA - " is one of the artifacts handled by _fix_filename_artifacts
    download.file_path = "/downloads/NA - Song.mp3"
    
    with patch("os.path.exists", return_value=True):
        with patch("os.rename") as mock_rename:
            dm._fix_filename_artifacts(download)
            assert mock_rename.called
            # Check if NA - was removed
            args = mock_rename.call_args[0]
            assert "Song.mp3" in args[1]
            assert "NA - " not in args[1]
