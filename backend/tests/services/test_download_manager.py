import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.download_manager import DownloadManager
from app.models.download import Download
from app.models.track import Track
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

@pytest.fixture
def manager():
    return DownloadManager()

@pytest.mark.asyncio
async def test_process_download_success(db_session: AsyncSession, manager: DownloadManager):
    user_id = uuid.uuid4()
    user = User(id=user_id, email="dm_test@example.com", username="dm_user", hashed_password="pw", is_active=True)
    db_session.add(user)
    
    track = Track(title="DL Track", artist="DL Artist", duration_ms=2000)
    db_session.add(track)
    await db_session.flush()
    
    download_id = uuid.uuid4()
    dl = Download(
        id=download_id,
        user_id=user.id,
        track_id=track.id,
        status="pending",
        source="youtube",
        playlist_name=None
    )
    db_session.add(dl)
    await db_session.commit()
    
    # Mock dependencies
    # 1. AsyncSessionLocal used in process_download
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=db_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    
    # 2. socket_manager
    # 3. yt_dlp
    
    with patch("app.services.download_manager.AsyncSessionLocal", return_value=mock_session_ctx), \
         patch("app.services.download_manager.socket_manager") as mock_socket, \
         patch("app.services.download_manager.yt_dlp.YoutubeDL"), \
         patch.object(manager, '_execute_download_task', new_callable=AsyncMock) as mock_exec, \
         patch.object(manager, '_resolve_url', new_callable=AsyncMock) as mock_resolve:
        
        mock_socket.emit = AsyncMock()
        # Setup mocks
        mock_resolve.return_value = "http://youtube.com/watch?v=123"
        
        # Simulate final_filename_container update in _handle_completion hooks or side_effect
        # But _handle_completion is called after _execute_download_task.
        # We also mock _handle_completion to simplify or let it run?
        # Let's let it run but mock os.path.exists/rename logic inside it if needed.
        # Check _handle_completion logic: it calls _set_download_file_path.
        
        with patch("app.services.download_manager.os.path.exists", return_value=False), \
             patch("app.services.download_manager.os.makedirs"):
             
            # Call process_download directly (bypassing queue loop)
            await manager.process_download(dl.id)
            
            # Assertions
            await db_session.refresh(dl)
            assert dl.status == "completed"
            assert dl.progress == 100
            
            mock_socket.emit.assert_called()
            mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_process_download_failure(db_session: AsyncSession, manager: DownloadManager):
    user_id = uuid.uuid4()
    user = User(id=user_id, email="fail_test@example.com", username="fail_user", hashed_password="pw", is_active=True)
    db_session.add(user)
    
    track = Track(title="Fail Track", artist="Fail Artist", duration_ms=2000)
    db_session.add(track)
    await db_session.flush()
    
    download_id = uuid.uuid4()
    dl = Download(
        id=download_id,
        user_id=user.id,
        track_id=track.id,
        status="pending",
        source="youtube"
    )
    db_session.add(dl)
    await db_session.commit()
    
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=db_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.download_manager.AsyncSessionLocal", return_value=mock_session_ctx), \
         patch("app.services.download_manager.socket_manager") as mock_socket, \
         patch.object(manager, '_resolve_url', side_effect=ValueError("Resolution failed")):
         
         mock_socket.emit = AsyncMock()
         await manager.process_download(dl.id)
         
         await db_session.refresh(dl)
         assert dl.status == "failed"
         assert "Resolution failed" in dl.error_message
         
         mock_socket.emit.assert_called_with('download:error', {
            'download_id': str(dl.id),
            'error': "Resolution failed"
         })

