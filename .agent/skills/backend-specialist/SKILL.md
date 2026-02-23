---
name: backend-specialist
description: Expert in Python, FastAPI, SQLAlchemy, and async backend development for Audiovault
---

# Backend Specialist Skill

## 🎯 Purpose

This skill provides expert knowledge for backend development in Audiovault, focusing on Python 3.11+, FastAPI, async SQLAlchemy, and related technologies.

## 🔧 Technology Stack

### Core Technologies
- **Python**: 3.11+ (use modern type hints, async/await)
- **Framework**: FastAPI (async ASGI)
- **ORM**: SQLAlchemy 2.x (async engine)
- **Database**: SQLite (default), PostgreSQL (production)
- **Cache**: Redis (optional, for high-traffic deployments)
- **Validation**: Pydantic v2
- **Authentication**: JWT (PyJWT)
- **Downloads**: yt-dlp
- **Scheduler**: APScheduler
- **Testing**: pytest, pytest-asyncio, httpx

### Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/           # API endpoints
│   │   └── __init__.py
│   ├── core/
│   │   ├── config.py         # Settings (env vars)
│   │   ├── security.py       # JWT, password hashing
│   │   ├── deps.py           # Dependency injection
│   │   └── exceptions.py     # Custom exceptions
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── db/
│   └── main.py
├── alembic/
├── tests/
├── requirements.txt
├── pyproject.toml
└── alembic.ini
```

## 📜 Core Patterns

### 1. Async SQLAlchemy Session

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

engine = create_async_engine("sqlite+aiosqlite:///./audiovault.db", echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

### 2. SQLAlchemy Models

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class Playlist(Base):
    __tablename__ = "playlists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    service_name = Column(String, nullable=False, index=True)
    external_id = Column(String, unique=True, nullable=False, index=True)
    url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tracks = relationship("Track", back_populates="playlist", cascade="all, delete-orphan")
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="playlists")
```

### 3. Pydantic Schemas

```python
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional

class PlaylistBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    service_name: str = Field(..., pattern="^(spotify|youtube|deezer|soundcloud)$")
    url: Optional[HttpUrl] = None

class PlaylistCreate(PlaylistBase):
    external_id: str

class PlaylistResponse(PlaylistBase):
    id: int
    external_id: str
    created_at: datetime
    updated_at: datetime
    track_count: int = 0

    class Config:
        from_attributes = True
```

### 4. Service Layer

```python
class PlaylistService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, user_id: int):
        result = await self.db.execute(
            select(Playlist).where(Playlist.user_id == user_id).order_by(Playlist.created_at.desc())
        )
        return result.scalars().all()

    async def create(self, playlist_data: PlaylistCreate, user_id: int) -> Playlist:
        playlist = Playlist(**playlist_data.dict(), user_id=user_id)
        self.db.add(playlist)
        await self.db.commit()
        await self.db.refresh(playlist)
        return playlist
```

### 5. Exception Handling

```python
class AudiovaultException(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

class PlaylistNotFoundError(AudiovaultException):
    def __init__(self, playlist_id: int):
        super().__init__(f"Playlist {playlist_id} not found", "PLAYLIST_NOT_FOUND", 404)
```

## 🛡️ Security Best Practices

### JWT Authentication

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt

SECRET_KEY = "your-secret-key-from-env"
ALGORITHM = "HS256"

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

## 🪤 Performance

### Eager Loading (Avoid N+1)

```python
# GOOD
playlists = await db.execute(
    select(Playlist).options(selectinload(Playlist.tracks))
)

# BAD
for playlist in playlists.scalars():
    print(playlist.tracks)  # Separate query per row!
```

### Connection Pooling

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
)
```

## 🧪 Testing

```python
@pytest.mark.asyncio
async def test_create_playlist(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/playlists",
        json={"name": "Test", "service_name": "spotify", "external_id": "abc123"},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test"
```

**Remember:** Always follow async patterns, use dependency injection, and write tests for critical paths.
