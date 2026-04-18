import redis.asyncio as redis
from app.core.config import settings


class CacheManager:
    def __init__(self):
        self.redis: redis.Redis | None = None

    async def connect(self):
        self.redis = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

    async def close(self):
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> str | None:
        if self.redis is None:
            await self.connect()
        assert self.redis is not None
        return await self.redis.get(key)

    async def set(self, key: str, value: str, expire: int = 3600):
        if self.redis is None:
            await self.connect()
        assert self.redis is not None
        await self.redis.set(key, value, ex=expire)

    async def delete(self, key: str):
        if self.redis is None:
            await self.connect()
        assert self.redis is not None
        await self.redis.delete(key)


cache_manager = CacheManager()
