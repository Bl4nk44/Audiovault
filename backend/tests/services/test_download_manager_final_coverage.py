"""
Final coverage boost for DownloadManager.
Targets: process_with_semaphore logic, and interrupted download resumption.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.download import Download
from app.services.download_manager import DownloadManager


@pytest.fixture
def dm():
    return DownloadManager()


@pytest.mark.asyncio
async def test_dm_process_with_semaphore_full_flow(dm):
    download_id = uuid.uuid4()
    mock_download = MagicMock(id=download_id, user_id=uuid.uuid4())
    mock_download.user.preferences = {"max_parallel_downloads": 2}

    # Mock DB result
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_download

    db_mock = AsyncMock()
    db_mock.execute.return_value = mock_res
    db_mock.__aenter__.return_value = db_mock

    # Mock semaphore and process_download
    with (
        patch("app.services.download_manager.AsyncSessionLocal", return_value=db_mock),
        patch.object(dm, "process_download", new_callable=AsyncMock) as mock_proc,
    ):
        # Add to queue first so task_done() doesn't fail
        await dm.queue.put(str(download_id))
        await dm.queue.get()  # Simulate worker picking it up

        # Trigger the semaphore wrapper
        await dm._process_with_semaphore(str(download_id))

        assert mock_proc.called
        assert str(dm.user_semaphores[str(mock_download.user_id)]._value) == "2"


@pytest.mark.asyncio
async def test_dm_resume_interrupted_downloads(dm, db_session):
    user_id = uuid.uuid4()
    track_id = uuid.uuid4()

    # Create downloads in 'downloading' and 'processing' states (interrupted)
    d1 = Download(id=uuid.uuid4(), user_id=user_id, track_id=track_id, status="downloading", progress=50)
    d2 = Download(id=uuid.uuid4(), user_id=user_id, track_id=track_id, status="processing", progress=100)
    db_session.add_all([d1, d2])
    await db_session.commit()

    with patch.object(dm.queue, "put", new_callable=AsyncMock) as mock_put:
        await dm.resume_pending_downloads(db_session)

        # Verify status reset to pending
        assert d1.status == "pending"
        assert d1.progress == 0
        assert d2.status == "pending"
        assert d2.progress == 0
        assert mock_put.call_count == 2


@pytest.mark.asyncio
async def test_dm_resume_no_pending(dm, db_session):
    # Ensure no pending downloads exist
    await db_session.execute(__import__("sqlalchemy").delete(Download))
    await db_session.commit()

    with patch.object(dm.queue, "put", new_callable=AsyncMock) as mock_put:
        with patch("app.services.download_manager.logger.info") as mock_log:
            await dm.resume_pending_downloads(db_session)
            assert mock_put.call_count == 0
            # Look for "No pending downloads found" in logs
            assert any("No pending downloads found" in str(args[0]) for args in mock_log.call_args_list)
