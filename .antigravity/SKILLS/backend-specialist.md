# Skill: Backend Specialist (Python/FastAPI)

## Role
You are an expert backend developer specializing in FastAPI, async Python, and SQLAlchemy.

## Core Competencies

### FastAPI Mastery
- Async route handlers and dependencies
- Request/response models with Pydantic v2
- Dependency injection system
- Background tasks and lifespan events
- WebSocket connections
- OpenAPI documentation
- Exception handlers and middleware

### SQLAlchemy 2.0 (Async)
```python
# Modern async pattern
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

async def get_track_with_playlist(db: AsyncSession, track_id: int):
    result = await db.execute(
        select(Track)
        .options(selectinload(Track.playlist))
        .where(Track.id == track_id)
    )
    return result.scalar_one_or_none()
```

### Database Best Practices
- Use async sessions consistently
- Eager load relationships to avoid N+1
- Index foreign keys and filter columns
- Use `select()` instead of `.query()`
- Close sessions properly (context managers)
- Migrations with Alembic

### Error Handling
```python
from fastapi import HTTPException, status

class TrackNotFoundError(Exception):
    pass

@app.exception_handler(TrackNotFoundError)
async def track_not_found_handler(request, exc):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Track not found"
    )
```

### Background Tasks
```python
from fastapi import BackgroundTasks

@router.post("/download")
async def start_download(
    url: str,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(download_track, url)
    return {"status": "queued"}
```

### APScheduler Integration
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=60)
async def sync_watchlist():
    # Auto-sync logic
    pass

scheduler.start()
```

## Common Patterns

### CRUD Operations
```python
class TrackCRUD:
    @staticmethod
    async def create(db: AsyncSession, track_data: TrackCreate):
        track = Track(**track_data.dict())
        db.add(track)
        await db.commit()
        await db.refresh(track)
        return track
    
    @staticmethod
    async def get(db: AsyncSession, track_id: int):
        result = await db.execute(
            select(Track).where(Track.id == track_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update(db: AsyncSession, track_id: int, data: TrackUpdate):
        track = await TrackCRUD.get(db, track_id)
        if not track:
            raise TrackNotFoundError
        for key, value in data.dict(exclude_unset=True).items():
            setattr(track, key, value)
        await db.commit()
        return track
```

### Dependency Injection
```python
from app.core.security import get_current_user

@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return current_user
```

### Testing
```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_track():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/tracks",
            json={"title": "Test", "artist": "Artist"}
        )
    assert response.status_code == 201
```

## Debugging Tips
- Use FastAPI's interactive docs (`/docs`)
- Log SQL queries: `echo=True` in engine config
- Profile slow endpoints with `time` decorators
- Check async context (avoid blocking calls)
- Monitor database connection pool

## Performance Optimization
- Use connection pooling
- Cache frequent queries with Redis
- Batch database operations
- Use `yield` for streaming responses
- Limit result sets with pagination
