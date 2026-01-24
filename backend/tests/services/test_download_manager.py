import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.schemas.download import DownloadCreate
from app.services.download_manager import DownloadManager


@pytest.fixture
def download_manager():
    dm = DownloadManager()
    return dm


@pytest.mark.asyncio
async def test_dm_add_download(download_manager):
    user_id = str(uuid.uuid4())
    track_id = uuid.uuid4()
    download_data = DownloadCreate(track_id=track_id, source="spotify")
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()

    with patch("app.services.download_manager.DownloadManager.start_worker", new_callable=AsyncMock) as mock_start:
        download = await download_manager.add_download(db_mock, user_id, download_data)

        assert download.user_id == user_id
        assert download.track_id == track_id or download.track_id == str(track_id)
        assert download.status == "pending"
        assert mock_start.called
        assert download_manager.queue.qsize() == 1


@pytest.mark.asyncio
async def test_dm_pause_resume_download(download_manager):
    download_id = str(uuid.uuid4())
    download_manager.pause_download(download_id)
    assert download_id in download_manager.paused_downloads

    with patch("app.services.download_manager.DownloadManager.start_worker", new_callable=AsyncMock):
        # We need a db mock for resume
        db_mock = MagicMock()
        db_mock.execute = AsyncMock()
        db_mock.commit = AsyncMock()
        db_mock.refresh = AsyncMock()
        mock_result = MagicMock()
        mock_download = MagicMock(status="paused")
        mock_result.scalar_one_or_none.return_value = mock_download
        db_mock.execute.return_value = mock_result

        # NOTE: db.commit is async in AsyncSession, but db.add is synchronous.
        # Here we only use execute/commit which are async in previous code context?
        # Actually in SQLAlchemy asyncio, execute is awaitable.

        await download_manager.resume_download(db_mock, download_id)
        assert download_id not in download_manager.paused_downloads
        assert mock_download.status == "pending"


@pytest.mark.asyncio
async def test_dm_cancel_download(download_manager):
    download_id = str(uuid.uuid4())
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    db_mock.delete = AsyncMock()
    db_mock.commit = AsyncMock()
    mock_result = MagicMock()
    mock_download = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_download
    db_mock.execute.return_value = mock_result

    # Mocking active task
    mock_task = MagicMock()
    download_manager.active_tasks[download_id] = mock_task

    with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
        await download_manager.cancel_download(db_mock, download_id)

        assert mock_task.cancel.called
        assert db_mock.delete.called
        assert mock_emit.called


@pytest.mark.asyncio
async def test_dm_restart_all_downloads(download_manager):
    user_id = str(uuid.uuid4())
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()

    with patch("app.services.download_manager.DownloadManager.start_worker", new_callable=AsyncMock):
        # Result mock
        mock_result = MagicMock()
        mock_download = MagicMock(id=uuid.uuid4(), user_id=user_id, status="failed")
        mock_result.scalars.return_value.all.return_value = [mock_download]
        db_mock.execute.return_value = mock_result

        count = await download_manager.restart_all_downloads(db_mock, user_id)
        assert count == 1
        assert mock_download.status == "pending"
        assert download_manager.queue.qsize() == 1


async def test_dm_process_download_fail_resolution(download_manager):
    download_id = str(uuid.uuid4())

    with patch("app.services.download_manager.AsyncSessionLocal") as mock_session_local:
        db_mock = MagicMock()
        db_mock.execute = AsyncMock()
        db_mock.commit = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = db_mock

        mock_result = MagicMock()
        mock_download = MagicMock(id=download_id, status="pending", retry_count=0)
        mock_result.scalar_one_or_none.return_value = mock_download
        db_mock.execute.return_value = mock_result

        with patch(
            "app.services.download_manager.DownloadManager._resolve_url", side_effect=Exception("Resolution failed")
        ):
            with patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock) as mock_emit:
                await download_manager.process_download(download_id)

                assert mock_download.status == "failed"
                assert mock_download.error_message == "Resolution failed"
                assert mock_download.retry_count == 1
                assert mock_emit.called


@pytest.mark.asyncio
async def test_dm_user_semaphore(download_manager):
    user_id = "user1"
    sem1 = download_manager.get_user_semaphore(user_id, max_concurrent=2)
    assert sem1._value == 2

    sem2 = download_manager.get_user_semaphore(user_id)
    assert sem1 is sem2

    download_manager.update_user_concurrency(user_id, 5)
    sem3 = download_manager.get_user_semaphore(user_id)
    assert sem3._value == 5
    assert sem3 is not sem1


@pytest.mark.asyncio
async def test_dm_cache_resolution(download_manager):
    url = "ytsearch1:test query"
    ydl_opts = {}
    download_id = "dl1"
    loop = asyncio.get_event_loop()

    with (
        patch("app.services.download_manager.cache_manager.get", new_callable=AsyncMock) as mock_get,
        patch("app.services.download_manager.cache_manager.set", new_callable=AsyncMock) as mock_set,
        patch("yt_dlp.YoutubeDL") as mock_ydl,
    ):
        # Case 1: Cache hit
        mock_get.return_value = "https://youtube.com/watch?v=cached"
        await download_manager._execute_download_task(loop, ydl_opts, url, download_id)
        assert mock_get.called
        # Check that it didn't call extract_info (via executor) - difficult with
        # run_in_executor but we can check ydl inside mock

        # Case 2: Cache miss
        mock_get.return_value = None
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {"entries": [{"webpage_url": "https://youtube.com/watch?v=new"}]}
        mock_ydl.return_value.__enter__.return_value = mock_instance

        # Mocking run_in_executor to return our info
        with patch.object(loop, "run_in_executor", AsyncMock(return_value=mock_instance.extract_info.return_value)):
            await download_manager._execute_download_task(loop, ydl_opts, url, download_id)
            assert mock_set.called
            # Verify cache key
            args, _ = mock_set.call_args
            assert "metadata_resolve" in args[0]


@pytest.mark.asyncio
async def test_dm_progress_hook_pause(download_manager):
    download_id = "paused_dl"
    download_manager.pause_download(download_id)

    loop = asyncio.get_event_loop()
    hook = download_manager._create_progress_hook(download_id, MagicMock(), loop, {})

    with pytest.raises(Exception) as exc:  # DownloadPausedError is internal
        hook({"status": "downloading"})
    assert "DOWNLOAD_PAUSED" in str(exc.value)


@pytest.mark.asyncio
async def test_dm_handle_completion_metadata(download_manager):
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    db_mock.commit = AsyncMock()
    download = MagicMock(id="dl1", file_path="/tmp/test.mp3", source="spotify")
    download.track.id = "track1"
    download.track.metadata_content = {}
    download.user.username = "testuser"

    container = {"path": "/tmp/test.mp3"}

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.getsize", return_value=1234),
        patch("app.services.download_manager.socket_manager.emit", new_callable=AsyncMock),
        patch(
            "app.services.library_scanner.library_scanner_service._parse_audio_metadata_sync",
            return_value=("Title", "Artist", "Album", "Genre", 5000),
        ),
        patch(
            "app.services.library_scanner.library_scanner_service.resolve_artist_and_album",
            new_callable=AsyncMock,
            return_value=("a1", "alb1"),
        ),
    ):
        await download_manager._handle_completion(db_mock, download, container, "tmpl")

        assert download.status == "completed"
        assert download.file_size == 1234
        assert download.track.title == "Title"
        assert download.track.artist_id == "a1"
        assert db_mock.commit.called
