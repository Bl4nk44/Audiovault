
import asyncio
from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal as SessionLocal
from app.models.track import Track
from app.models.download import Download
from app.models.user import User

async def check_stats():
    async with SessionLocal() as db:
        # User count
        users = await db.execute(select(User))
        user_list = users.scalars().all()
        print(f"Total Users: {len(user_list)}")
        for u in user_list:
            print(f" - {u.username} (ID: {u.id})")

        # Track count
        tracks = await db.execute(select(func.count(Track.id)))
        print(f"Total Tracks: {tracks.scalar()}")

        # Download count
        downloads = await db.execute(select(func.count(Download.id)))
        print(f"Total Downloads: {downloads.scalar()}")

        # Status distribution
        status_result = await db.execute(select(Download.status, func.count(Download.id)).group_by(Download.status))
        print("Download Statuses:")
        for status, count in status_result:
            print(f" - {status}: {count}")

        # Downloads per user
        for u in user_list:
            u_dl = await db.execute(select(func.count(Download.id)).where(Download.user_id == u.id, Download.status == 'completed'))
            print(f"Completed Downloads for {u.username}: {u_dl.scalar()}")

if __name__ == "__main__":
    asyncio.run(check_stats())
