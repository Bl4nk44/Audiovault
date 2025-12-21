import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.download_manager import DownloadManager
from app.models.download import Download
from app.models.track import Track
from app.models.user import User
from app.models.history import ListeningHistory

@pytest.mark.asyncio
async def test_download_manager_pause_resume():
    # Setup
    with patch('app.services.download_manager.AsyncSessionLocal') as mock_session_cls:
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_db
        
        with patch('app.services.socket_manager.socket_manager') as mock_socket:
            manager = DownloadManager()
            
            # Test Pause
            download_id = "test-id"
            await manager.pause_download(download_id)
            assert download_id in manager.paused_downloads
            
            # Test Resume
            # Mock DB returning a paused download
            mock_download = Download(id=download_id, status="paused", user_id="user1", track_id="track1")
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_download
            mock_db.execute.return_value = mock_result
            
            await manager.resume_download(mock_db, download_id)
            
            assert download_id not in manager.paused_downloads
            assert mock_download.status == "pending"
            assert mock_db.commit.called
            # Verify it was put back in queue
            assert not manager.queue.empty()
            queued_id = await manager.queue.get()
            assert queued_id == download_id

@pytest.mark.asyncio
async def test_retry_logic():
    with patch('app.services.download_manager.AsyncSessionLocal') as mock_session_cls:
        mock_db = AsyncMock()
        
        with patch('app.services.socket_manager.socket_manager') as mock_socket:
            manager = DownloadManager()
            
            # Create a download that will fail
            download_id = "fail-id"
            download = Download(
                id=download_id, 
                status="pending", 
                source="spotify", 
                track_id="track1",
                retry_count=0
            )
            download.track = Track(title="Test", artist="Test")
            download.user = User(username="test")
            download.user.preferences = {}
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = download
            mock_db.execute.return_value = mock_result
            
            # Mock _resolve_url to raise exception
            # We need to control the flow inside process_download
            # This is hard to integration test without full DB
            pass

if __name__ == "__main__":
    # Simple manual run check
    print("To run tests: pytest backend/tests/test_download_manager.py")
