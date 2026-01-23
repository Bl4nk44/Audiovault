"""
Additional coverage tests for DownloadManager.
Targets: progress hooks, cancellation, queue processing, restarts.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.download import Download
from app.services.download_manager import DownloadManager, DownloadPausedError


@pytest.fixture
def download_manager():
    return DownloadManager()


@pytest.fixture
def mock_download():
    dl = MagicMock(spec=Download)
    dl.id = uuid.uuid4()
    dl.user_id = uuid.uuid4()
    dl.track_id = uuid.uuid4()
    dl.status = "pending"
    dl.track = MagicMock()
    dl.track.title = "Test"
    dl.track.artist = "Artist"
    dl.track.metadata_content = {}
    dl.user = MagicMock()
    dl.user.username = "user"
    dl.user.preferences = {}
    return dl


# =============================================================================
# Progress Hooks & Status Updates
# =============================================================================


@pytest.mark.asyncio
async def test_progress_hook_downloading(download_manager, mock_download):
    """Test progress hook in downloading state."""
    download_id = str(mock_download.id)
    loop = asyncio.get_running_loop()
    container = {}

    hook = download_manager._create_progress_hook(download_id, mock_download, loop, container)

    data = {"status": "downloading", "total_bytes": 1000, "downloaded_bytes": 500}

    with patch.object(download_manager, "_handle_progress_update") as mock_handle:
        hook(data)
        mock_handle.assert_called_once_with(data, download_id, mock_download, loop)


@pytest.mark.asyncio
async def test_progress_hook_paused_error(download_manager, mock_download):
    """Test progress hook raises DownloadPausedError when paused."""
    download_id = str(mock_download.id)
    loop = asyncio.get_running_loop()
    container = {}

    download_manager.paused_downloads.add(download_id)
    hook = download_manager._create_progress_hook(download_id, mock_download, loop, container)

    data = {"status": "downloading"}

    with pytest.raises(DownloadPausedError):
        hook(data)


@pytest.mark.asyncio
async def test_progress_hook_finished(download_manager, mock_download):
    """Test progress hook in finished state."""
    download_id = str(mock_download.id)
    loop = asyncio.get_running_loop()
    container = {"path": None}

    hook = download_manager._create_progress_hook(download_id, mock_download, loop, container)
    data = {"status": "finished", "filename": "/tmp/file.mp3"}

    with patch.object(download_manager, "_set_processing_status", new_callable=AsyncMock):
        # Calls run_coroutine_threadsafe, so we need to wait a bit or mock it
        # Since we can't easily await threadsafe in sync hook, checking if it was called
        # We'll mock run_coroutine_threadsafe
        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            hook(data)
            assert container["path"] == "/tmp/file.mp3"
            mock_run.assert_called()


@pytest.mark.asyncio
async def test_set_processing_status(download_manager):
    """Test setting processing status in DB."""
    download_id = str(uuid.uuid4())
    db_mock = AsyncMock()
    mock_dl = MagicMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_dl
    db_mock.execute.return_value = mock_result

    with patch("app.services.download_manager.AsyncSessionLocal", return_value=db_mock):
        # Need to handle __aenter__
        db_mock.__aenter__.return_value = db_mock

        with patch.object(download_manager, "_notify_processing", new_callable=AsyncMock) as mock_notify:
            await download_manager._set_processing_status(download_id)

            assert mock_dl.status == "processing"
            assert mock_dl.progress == 100
            db_mock.commit.assert_called_once()
            mock_notify.assert_called_once_with(mock_dl)


@pytest.mark.asyncio
async def test_handle_progress_update(download_manager, mock_download):
    """Test handling progress update dict."""
    download_id = str(mock_download.id)
    loop = asyncio.get_running_loop()

    data = {"total_bytes": 100, "downloaded_bytes": 50}

    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock):
        with patch.object(download_manager, "update_progress_db", new_callable=AsyncMock):
            with patch("asyncio.run_coroutine_threadsafe") as mock_run:
                download_manager._handle_progress_update(data, download_id, mock_download, loop)

                # Should emit progress socket
                # run_coroutine_threadsafe is called twice (emit and db update)
                assert mock_run.call_count >= 1


# =============================================================================
# Cancellation & Restart
# =============================================================================


@pytest.mark.asyncio
async def test_cancel_download_active(download_manager):
    """Test cancelling an active download task."""
    download_id = str(uuid.uuid4())
    mock_task = MagicMock()
    download_manager.active_tasks[download_id] = mock_task
    download_manager.paused_downloads.add(download_id)

    db_mock = AsyncMock()
    mock_dl = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_dl
    db_mock.execute.return_value = mock_result

    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock):
        await download_manager.cancel_download(db_mock, download_id)

        # Should remove from paused
        assert download_id not in download_manager.paused_downloads
        # Should cancel task
        mock_task.cancel.assert_called_once()
        # Should delete from DB
        db_mock.delete.assert_called_once_with(mock_dl)


@pytest.mark.asyncio
async def test_restart_all_downloads(download_manager):
    """Test restarting failed downloads."""
    db_mock = AsyncMock()
    user_id = str(uuid.uuid4())

    d1 = MagicMock(status="failed", id=uuid.uuid4())
    d2 = MagicMock(status="cancelled", id=uuid.uuid4())

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [d1, d2]
    db_mock.execute.return_value = mock_result

    with patch.object(download_manager, "start_worker", new_callable=AsyncMock) as mock_start:
        count = await download_manager.restart_all_downloads(db_mock, user_id)

        assert count == 2
        assert d1.status == "pending"
        assert d1.retry_count == 0
        assert download_manager.queue.qsize() == 2
        mock_start.assert_called_once()
