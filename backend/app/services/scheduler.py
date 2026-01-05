from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.cache import cache_manager
from app.db.database import AsyncSessionLocal
from app.services.watchlist_engine import watchlist_engine
from sqlalchemy import select
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.lock_key = "watchlist_sync_lock"
        self.lock_timeout = 3000  # 50 minutes (should be less than interval)

    def start(self):
        if not self.scheduler.running:
            # Schedule watchlist sync every 60 minutes
            self.scheduler.add_job(
                self.scheduled_watchlist_sync,
                trigger=IntervalTrigger(minutes=60),
                id="watchlist_sync",
                replace_existing=True,
                max_instances=1
            )
            # Schedule active downloads check every 5 minutes (as a safety net for stuck downloads)
            self.scheduler.add_job(
                self.check_stuck_downloads,
                trigger=IntervalTrigger(minutes=5),
                id="stuck_downloads_check",
                replace_existing=True
            )
            self.scheduler.start()
            logger.info("🚀 Scheduler started. Watchlist sync interval: 60 min.")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("🛑 Scheduler stopped.")

    async def scheduled_watchlist_sync(self):
        """
        Background task to sync watchlists.
        Uses Redis to ensure single execution across potential multiple workers 
        (though currently we run single worker).
        """
        if not cache_manager.redis:
            logger.warning("Redis not available, skipping scheduled sync.")
            return

        # Try to acquire lock
        is_locked = await cache_manager.redis.get(self.lock_key)
        if is_locked:
            logger.info("🔒 Sync job already in progress (locked). Skipping this cycle.")
            return

        try:
            # Set lock with expiry
            await cache_manager.redis.set(self.lock_key, "1", ex=self.lock_timeout)
            logger.info("⏰ Starting scheduled watchlist sync...")
            
            async with AsyncSessionLocal() as db:
                # Get all users (in future might want to shard this)
                stmt = select(User)
                result = await db.execute(stmt)
                users = result.scalars().all()
                
                total_new = 0
                for user in users:
                    try:
                        logger.info(f"Syncing for user: {user.username}")
                        new_count = await watchlist_engine.check_for_updates(db, user.id)
                        total_new += new_count
                    except Exception as e:
                        logger.error(f"Error syncing for user {user.username}: {e}")
                
            logger.info(f"✅ Scheduled sync completed. Total new items queued: {total_new}")

        except Exception as e:
            logger.error(f"🔥 Critical error in scheduled_sync: {e}")
        finally:
            # Release lock
            if cache_manager.redis:
                await cache_manager.redis.delete(self.lock_key)

    async def check_stuck_downloads(self):
        """Check for downloads stuck in 'downloading' or 'processing' state for too long"""
        # Logic to be implemented or expanded later.
        # For now, just a placeholder or simple logic could go here.
        # This prevents the 'black hole' of downloads that crashed the worker silently.
        pass

scheduler_service = SchedulerService()
