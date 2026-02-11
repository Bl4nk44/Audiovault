import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.download import Download
from app.schemas.download import DownloadCreate
from app.services.download_manager import DownloadManager


@pytest.fixture
def download_manager():
    return DownloadManager()


@pytest.mark.asyncio
async def test_dm_get_user_semaphore(download_manager):
    user_id = str(uuid.uuid4())
    sem = download_manager.get_user_semaphore(user_id, 5)
    assert isinstance(sem, asyncio.Semaphore)
    assert download_manager.user_semaphores[user_id]._value == 5


@pytest.mark.asyncio
async def test_dm_update_user_concurrency(download_manager):
    user_id = str(uuid.uuid4())
    download_manager.update_user_concurrency(user_id, 2)
    assert download_manager.user_semaphores[user_id]._value == 2

    # Update existing
    download_manager.update_user_concurrency(user_id, 10)
    assert download_manager.user_semaphores[user_id]._value == 10


@pytest.mark.asyncio
async def test_dm_ensure_permissions(download_manager):
    with patch("os.chmod") as mock_chmod:
        # Dir
        download_manager._ensure_permissions("/tmp/test_dir", is_file=False)
        mock_chmod.assert_called_with("/tmp/test_dir", 0o777)
        # File
        download_manager._ensure_permissions("/tmp/test_file", is_file=True)
        mock_chmod.assert_called_with("/tmp/test_file", 0o666)
        # Error (should be caught)
        mock_chmod.side_effect = OSError("Perm denied")
        download_manager._ensure_permissions("/tmp/error", is_file=False)


@pytest.mark.asyncio
async def test_dm_resume_pending_downloads(download_manager):
    db = AsyncMock()
    mock_download = Download(id=uuid.uuid4(), status="pending")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_download]
    db.execute.return_value = mock_result

    with patch.object(download_manager.queue, "put", new_callable=AsyncMock) as mock_put:
        await download_manager.resume_pending_downloads(db)
        assert mock_put.call_count == 1
        assert db.commit.called


@pytest.mark.asyncio
async def test_dm_add_download(download_manager):
    db = AsyncMock()
    user_id = uuid.uuid4()
    download_data = DownloadCreate(track_id=uuid.uuid4(), source="youtube")

    with patch.object(download_manager.queue, "put", new_callable=AsyncMock) as mock_put:
        download = await download_manager.add_download(db, user_id, download_data)
        assert download.track_id == download_data.track_id
        assert mock_put.call_count == 1
        assert db.add.called
        assert db.commit.called


@pytest.mark.asyncio
async def test_dm_pause_resume(download_manager):
    download_id = str(uuid.uuid4())
    download_manager.pause_download(download_id)
    assert download_id in download_manager.paused_downloads

    db = AsyncMock()
    mock_download = Download(id=uuid.UUID(download_id), status="paused")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_download
    db.execute.return_value = mock_result

    with patch.object(download_manager.queue, "put", new_callable=AsyncMock):
        await download_manager.resume_download(db, download_id)
        assert download_id not in download_manager.paused_downloads
        assert mock_download.status == "pending"
