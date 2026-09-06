from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scheduler import SchedulerService


@pytest.fixture
def scheduler_svc():
    svc = SchedulerService()
    svc.scheduler = MagicMock()
    return svc


# ─── start / stop ─────────────────────────────────────────────────────────────


def test_start_registers_jobs_and_starts(scheduler_svc):
    scheduler_svc.scheduler.running = False

    scheduler_svc.start()

    assert scheduler_svc.scheduler.add_job.call_count == 4
    scheduler_svc.scheduler.start.assert_called_once()


def test_start_skips_when_already_running(scheduler_svc):
    scheduler_svc.scheduler.running = True

    scheduler_svc.start()

    scheduler_svc.scheduler.add_job.assert_not_called()
    scheduler_svc.scheduler.start.assert_not_called()


def test_stop_shuts_down_when_running(scheduler_svc):
    scheduler_svc.scheduler.running = True

    scheduler_svc.stop()

    scheduler_svc.scheduler.shutdown.assert_called_once()


def test_stop_skips_when_not_running(scheduler_svc):
    scheduler_svc.scheduler.running = False

    scheduler_svc.stop()

    scheduler_svc.scheduler.shutdown.assert_not_called()


# ─── scheduled_watchlist_sync ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scheduled_watchlist_sync_no_redis(scheduler_svc):
    with patch("app.services.scheduler.cache_manager") as mock_cache:
        mock_cache.redis = None
        # Should return early without error
        await scheduler_svc.scheduled_watchlist_sync()


@pytest.mark.asyncio
async def test_scheduled_watchlist_sync_already_locked(scheduler_svc):
    with patch("app.services.scheduler.cache_manager") as mock_cache:
        mock_cache.redis = AsyncMock()
        mock_cache.redis.get = AsyncMock(return_value=b"1")

        await scheduler_svc.scheduled_watchlist_sync()

        mock_cache.redis.set.assert_not_called()


def _setup_watchlist_sync_mocks(mock_cache, mock_session_cls, users: list):
    """Wire up cache redis + async DB session mocks for scheduled_watchlist_sync tests."""
    mock_cache.redis = AsyncMock()
    mock_cache.redis.get = AsyncMock(return_value=None)
    mock_cache.redis.set = AsyncMock()
    mock_cache.redis.delete = AsyncMock()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = users
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_db


@pytest.mark.asyncio
async def test_scheduled_watchlist_sync_success(scheduler_svc):
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "testuser"

    with (
        patch("app.services.scheduler.cache_manager") as mock_cache,
        patch("app.services.scheduler.AsyncSessionLocal") as mock_session_cls,
        patch("app.services.scheduler.watchlist_engine") as mock_engine,
        patch("app.services.scheduler.select"),
    ):
        mock_db = _setup_watchlist_sync_mocks(mock_cache, mock_session_cls, [mock_user])
        mock_engine.check_for_updates = AsyncMock(return_value=3)

        await scheduler_svc.scheduled_watchlist_sync()

        mock_cache.redis.set.assert_called_once()
        mock_cache.redis.delete.assert_called_once_with(scheduler_svc.lock_key)
        mock_engine.check_for_updates.assert_called_once_with(mock_db, 1)


@pytest.mark.asyncio
async def test_scheduled_watchlist_sync_user_error_continues(scheduler_svc):
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "baduser"

    with (
        patch("app.services.scheduler.cache_manager") as mock_cache,
        patch("app.services.scheduler.AsyncSessionLocal") as mock_session_cls,
        patch("app.services.scheduler.watchlist_engine") as mock_engine,
        patch("app.services.scheduler.select"),
    ):
        _setup_watchlist_sync_mocks(mock_cache, mock_session_cls, [mock_user])
        mock_engine.check_for_updates = AsyncMock(side_effect=RuntimeError("boom"))

        await scheduler_svc.scheduled_watchlist_sync()

        mock_cache.redis.delete.assert_called_once()


# ─── scheduled_recommendation_refresh ────────────────────────────────────────


@pytest.mark.asyncio
async def test_scheduled_recommendation_refresh_success(scheduler_svc):
    mock_user = MagicMock()
    mock_user.username = "user1"

    with (
        patch("app.services.scheduler.AsyncSessionLocal") as mock_session_cls,
        patch("app.services.scheduler.HybridRecommendationEngine") as mock_engine_cls,
        patch("app.services.scheduler.select"),
        patch("app.services.scheduler.or_"),
    ):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_engine = AsyncMock()
        mock_engine_cls.for_user = AsyncMock(return_value=mock_engine)

        await scheduler_svc.scheduled_recommendation_refresh()

        mock_engine.get_recommendations.assert_called_once_with(mock_user, force_refresh=True)


@pytest.mark.asyncio
async def test_scheduled_recommendation_refresh_user_error_continues(scheduler_svc):
    mock_user = MagicMock()
    mock_user.username = "failuser"

    with (
        patch("app.services.scheduler.AsyncSessionLocal") as mock_session_cls,
        patch("app.services.scheduler.HybridRecommendationEngine") as mock_engine_cls,
        patch("app.services.scheduler.select"),
        patch("app.services.scheduler.or_"),
    ):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_engine = AsyncMock()
        mock_engine.get_recommendations = AsyncMock(side_effect=RuntimeError("rec error"))
        mock_engine_cls.for_user = AsyncMock(return_value=mock_engine)

        await scheduler_svc.scheduled_recommendation_refresh()  # must not raise


@pytest.mark.asyncio
async def test_scheduled_recommendation_refresh_db_error(scheduler_svc):
    with (
        patch("app.services.scheduler.AsyncSessionLocal") as mock_session_cls,
        patch("app.services.scheduler.HybridRecommendationEngine"),
    ):
        mock_session_cls.return_value.__aenter__ = AsyncMock(side_effect=RuntimeError("db error"))
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await scheduler_svc.scheduled_recommendation_refresh()  # must not raise


# ─── scheduled_retry_downloads ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scheduled_retry_downloads_success(scheduler_svc):
    with (
        patch("app.services.scheduler.AsyncSessionLocal") as mock_session_cls,
        patch("app.services.scheduler.download_manager") as mock_dm,
    ):
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_dm.retry_failed_downloads = AsyncMock()

        await scheduler_svc.scheduled_retry_downloads()

        mock_dm.retry_failed_downloads.assert_called_once_with(mock_db)


@pytest.mark.asyncio
async def test_scheduled_retry_downloads_error_does_not_raise(scheduler_svc):
    with (
        patch("app.services.scheduler.AsyncSessionLocal") as mock_session_cls,
        patch("app.services.scheduler.download_manager"),
    ):
        mock_session_cls.return_value.__aenter__ = AsyncMock(side_effect=RuntimeError("db down"))
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await scheduler_svc.scheduled_retry_downloads()  # must not raise


# ─── check_stuck_downloads ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_stuck_downloads_is_noop(scheduler_svc):
    result = await scheduler_svc.check_stuck_downloads()
    assert result is None


@pytest.mark.asyncio
async def test_scheduled_watchlist_sync_calls_auto_sync_deletions(scheduler_svc):
    """auto_sync_all_deletions called per user; non-empty result triggers logger.info branch."""
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "testuser"

    deletion_result = {"synced": [{"watchlist_name": "P1", "removed_count": 2, "files_deleted": 0}], "skipped": []}

    with (
        patch("app.services.scheduler.cache_manager") as mock_cache,
        patch("app.services.scheduler.AsyncSessionLocal") as mock_session_cls,
        patch("app.services.scheduler.watchlist_engine") as mock_engine,
        patch("app.services.scheduler.sync_manager") as mock_sync,
        patch("app.services.scheduler.select"),
    ):
        mock_db = _setup_watchlist_sync_mocks(mock_cache, mock_session_cls, [mock_user])
        mock_engine.check_for_updates = AsyncMock(return_value=0)
        mock_sync.auto_sync_all_deletions = AsyncMock(return_value=deletion_result)

        await scheduler_svc.scheduled_watchlist_sync()

        mock_sync.auto_sync_all_deletions.assert_called_once_with(mock_db, 1, only_auto=True)
