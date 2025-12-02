from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.watchlist import Watchlist
from app.models.schemas import UserCreate
from typing import List

class WatchlistEngine:
    async def add_to_watchlist(self, db: AsyncSession, user_id: str, item: dict) -> Watchlist:
        # Check if exists
        result = await db.execute(
            select(Watchlist).where(
                Watchlist.user_id == user_id,
                Watchlist.source_id == item['source_id'],
                Watchlist.source == item['source']
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        watchlist_item = Watchlist(
            user_id=user_id,
            watch_type=item['watch_type'],
            source=item['source'],
            source_id=item['source_id'],
            source_name=item['source_name'],
            auto_download=item.get('auto_download', False)
        )
        db.add(watchlist_item)
        await db.commit()
        await db.refresh(watchlist_item)
        return watchlist_item

    async def get_watchlist(self, db: AsyncSession, user_id: str) -> List[Watchlist]:
        result = await db.execute(select(Watchlist).where(Watchlist.user_id == user_id))
        return result.scalars().all()

    async def remove_from_watchlist(self, db: AsyncSession, watchlist_id: str, user_id: str):
        result = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == user_id))
        item = result.scalar_one_or_none()
        if item:
            await db.delete(item)
            await db.commit()
            return True
        return False

watchlist_engine = WatchlistEngine()
