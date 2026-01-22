"""
Extended tests for SchedulerService.
Covers: start, stop, scheduled jobs (watchlist sync, retry downloads).
"""
import pytest
import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.scheduler import SchedulerService

@pytest.fixture
def scheduler_service():
    return SchedulerService()

def test_start_scheduler(scheduler_service):
    """Test starting the scheduler."""
    with patch.object(scheduler_service.scheduler, "start") as mock_start:
        with patch.object(scheduler_service.scheduler, "add_job") as mock_add_job:
            scheduler_service.start()
            
            assert mock_start.called
            assert mock_add_job.call_count >= 3  # sync, retry, stuck checks

def test_stop_scheduler(scheduler_service):
    """Test stopping the scheduler."""
    # Create a mock for the scheduler that allows property setting
    scheduler_mock = MagicMock()
    type(scheduler_mock).running = pytest.mark.property(lambda self: True)
    
    # Simpler approach: usage is just if self.scheduler.running:
    # We can patch the instance attribute
    scheduler_service.scheduler = MagicMock()
    scheduler_service.scheduler.running = True
    
    with patch.object(scheduler_service.scheduler, "shutdown") as mock_shutdown:
        scheduler_service.stop()
        assert mock_shutdown.called

@pytest.mark.asyncio
async def test_scheduled_watchlist_sync_no_redis(scheduler_service):
    """Test sync skips if redis is missing."""
    with patch("app.services.scheduler.cache_manager.redis", None):
        await scheduler_service.scheduled_watchlist_sync()
        # Should just return without error

@pytest.mark.asyncio
async def test_scheduled_watchlist_sync_locked(scheduler_service):
    """Test sync skips if locked."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "1"  # Locked
    
    with patch("app.services.scheduler.cache_manager.redis", mock_redis):
        await scheduler_service.scheduled_watchlist_sync()
        
        mock_redis.get.assert_called_with(scheduler_service.lock_key)
        mock_redis.set.assert_not_called()

@pytest.mark.asyncio
async def test_scheduled_watchlist_sync_execution(scheduler_service):
    """Test sync execution."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Not locked
    
    # Mock DB users
    mock_user = MagicMock()
    mock_user.username = "testuser"
    mock_user.id = uuid.uuid4()
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_user]
    mock_db.execute.return_value = mock_result
    
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_ctx.__aexit__ = AsyncMock()
    
    with patch("app.services.scheduler.cache_manager.redis", mock_redis):
        with patch("app.services.scheduler.AsyncSessionLocal", return_value=mock_ctx):
            with patch("app.services.scheduler.watchlist_engine.check_for_updates", new_callable=AsyncMock) as mock_check:
                mock_check.return_value = 5  # 5 new items
                
                await scheduler_service.scheduled_watchlist_sync()
                
                # Verify lock set and released
                mock_redis.set.assert_called()
                mock_redis.delete.assert_called()
                
                # Verify logic
                mock_check.assert_called_with(mock_db, mock_user.id)

@pytest.mark.asyncio
async def test_scheduled_retry_downloads(scheduler_service):
    """Test retry downloads task."""
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    
    # We patch the Class, so instantiated object should be our mock
    # App usage: async with AsyncSessionLocal() as db:
    # So AsyncSessionLocal() -> mock_ctx -> enter -> mock_db
    
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_ctx.__aexit__ = AsyncMock()
    
    with patch("app.services.scheduler.AsyncSessionLocal", return_value=mock_ctx):
        with patch("app.services.scheduler.download_manager.retry_failed_downloads", new_callable=AsyncMock) as mock_retry:
            await scheduler_service.scheduled_retry_downloads()
            
            mock_retry.assert_called_with(mock_db)
