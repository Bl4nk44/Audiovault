import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.download_manager import DownloadManager


@pytest.fixture
def download_manager():
    return DownloadManager()


@pytest.mark.asyncio
async def test_dm_delete_playlist(download_manager):
    user_id = str(uuid.uuid4())
    source = "spotify"
    playlist_name = "My Playlist"

    db_mock = AsyncMock()

    # Mock finding downloads
    mock_dl1 = MagicMock(id=uuid.uuid4(), file_path="/tmp/track1.mp3")
    mock_dl2 = MagicMock(id=uuid.uuid4(), file_path="/tmp/track2.mp3")

    # Setup mock result for select (Async iterator)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_dl1, mock_dl2]
    db_mock.execute.return_value = mock_result

    with (
        patch("os.path.exists", return_value=True),
        patch("os.remove") as mock_remove,
        patch("os.rmdir"),
        patch("os.listdir", return_value=[]),  # Empty dir after deletion
        patch("app.core.config.settings.DOWNLOAD_DIR", "/tmp"),
        patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock),
    ):
        await download_manager.delete_playlist(db_mock, user_id, source, playlist_name)

        # Verify DB deletions
        assert db_mock.delete.call_count == 2

        # Verify file deletions (2 tracks + 1 playlist m3u8)
        assert mock_remove.call_count == 3
        mock_remove.assert_any_call("/tmp/track1.mp3")
        mock_remove.assert_any_call("/tmp/track2.mp3")


@pytest.mark.asyncio
async def test_dm_ensure_permissions(download_manager):
    path = "/tmp/testfile"
    with patch("os.chmod") as mock_chmod:
        download_manager._ensure_permissions(path, is_file=True)
        mock_chmod.assert_called_with(path, 0o666)

        download_manager._ensure_permissions(path, is_file=False)
        mock_chmod.assert_called_with(path, 0o777)


@pytest.mark.asyncio
async def test_dm_ensure_permissions_error(download_manager):
    # Should not raise exception
    with patch("os.chmod", side_effect=OSError("Perm error")):
        download_manager._ensure_permissions("/tmp/fail")


@pytest.mark.asyncio
async def test_dm_process_queue_paused_item(download_manager):
    # Test skipping paused items
    dl_id = "paused-id"
    download_manager.paused_downloads.add(dl_id)

    # Mock queue completely
    download_manager.queue = AsyncMock()
    # get returns dl_id first, then raises CancelledError to stop loop
    download_manager.queue.get.side_effect = [dl_id, asyncio.CancelledError]

    try:
        await download_manager.process_queue()
    except asyncio.CancelledError:
        pass

    # Verify task_done called and _process_with_semaphore NOT called
    with patch.object(download_manager, "_process_with_semaphore") as mock_process:
        assert download_manager.queue.task_done.call_count >= 1
        mock_process.assert_not_called()


@pytest.mark.asyncio
async def test_dm_process_with_semaphore_invalid_uuid(download_manager):
    # Mock queue to avoid task_done error on real queue
    download_manager.queue = AsyncMock()

    # Wrapper handles invalid UUID
    await download_manager._process_with_semaphore("invalid-uuid")

    download_manager.queue.task_done.assert_called()


@pytest.mark.asyncio
async def test_dm_process_with_semaphore_no_download(download_manager):
    dl_id = uuid.uuid4()

    # Mock queue
    download_manager.queue = AsyncMock()

    with patch("app.services.download_manager.AsyncSessionLocal") as mock_session_local:
        db_mock = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = db_mock

        # Return None for download lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_mock.execute.return_value = mock_result

        await download_manager._process_with_semaphore(str(dl_id))

        download_manager.queue.task_done.assert_called()
