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
│   │   │   ├── playlists.py
│   │   │   ├── tracks.py
│   │   │   ├── auth.py
│   │   │   └── subsonic.py
│   │   └── __init__.py
│   ├── core/
│   │   ├── config.py         # Settings (env vars)
│   │   ├── security.py       # JWT, password hashing
│   │   ├── deps.py           # Dependency injection
│   │   └── exceptions.py     # Custom exceptions
│   ├── models/
│   │   ├── user.py           # SQLAlchemy models
│   │   ├── playlist.py
│   │   ├── track.py
│   │   └── base.py           # Base model class
│   ├── schemas/
│   │   ├── user.py           # Pydantic schemas
│   │   ├── playlist.py
│   │   └── track.py
│   ├── services/
│   │   ├── playlist_service.py    # Business logic
│   │   ├── download_service.py
│   │   ├── spotify_service.py
│   │   └── youtube_service.py
│   ├── db/
│   │   ├── session.py        # Database session
│   │   └── init_db.py        # Database initialization
│   └── main.py               # FastAPI app entry point
├── alembic/                  # Database migrations
│   ├── versions/
│   └── env.py
├── tests/
│   ├── conftest.py           # pytest fixtures
│   ├── test_api/
│   └── test_services/
├── requirements.txt
├── pyproject.toml
└── alembic.ini
```

## 📜 Core Patterns

### 1. Async SQLAlchemy Session

```python
# app/db/session.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    "sqlite+aiosqlite:///./audiovault.db",
    echo=False,
    future=True
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

### 2. SQLAlchemy Models

```python
# app/models/playlist.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import Base

class Playlist(Base):
    __tablename__ = "playlists"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    service_name = Column(String, nullable=False, index=True)  # spotify, youtube, etc.
    external_id = Column(String, unique=True, nullable=False, index=True)
    url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tracks = relationship("Track", back_populates="playlist", cascade="all, delete-orphan")
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="playlists")
```

### 3. Pydantic Schemas

```python
# app/schemas/playlist.py
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional, List

class PlaylistBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    service_name: str = Field(..., pattern="^(spotify|youtube|deezer|soundcloud)$")
    url: Optional[HttpUrl] = None

class PlaylistCreate(PlaylistBase):
    external_id: str

class PlaylistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)

class PlaylistResponse(PlaylistBase):
    id: int
    external_id: str
    created_at: datetime
    updated_at: datetime
    track_count: int = 0
    
    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)
```

### 4. Service Layer

```python
# app/services/playlist_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.models.playlist import Playlist
from app.schemas.playlist import PlaylistCreate, PlaylistUpdate
from app.core.exceptions import PlaylistNotFoundError

class PlaylistService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all(self, user_id: int) -> List[Playlist]:
        """Get all playlists for a user."""
        result = await self.db.execute(
            select(Playlist)
            .where(Playlist.user_id == user_id)
            .order_by(Playlist.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_by_id(self, playlist_id: int, user_id: int) -> Playlist:
        """Get a single playlist by ID."""
        result = await self.db.execute(
            select(Playlist)
            .where(Playlist.id == playlist_id, Playlist.user_id == user_id)
        )
        playlist = result.scalar_one_or_none()
        if not playlist:
            raise PlaylistNotFoundError(playlist_id)
        return playlist
    
    async def create(self, playlist_data: PlaylistCreate, user_id: int) -> Playlist:
        """Create a new playlist."""
        playlist = Playlist(**playlist_data.dict(), user_id=user_id)
        self.db.add(playlist)
        await self.db.commit()
        await self.db.refresh(playlist)
        return playlist
    
    async def update(self, playlist_id: int, playlist_data: PlaylistUpdate, user_id: int) -> Playlist:
        """Update an existing playlist."""
        playlist = await self.get_by_id(playlist_id, user_id)
        
        for field, value in playlist_data.dict(exclude_unset=True).items():
            setattr(playlist, field, value)
        
        await self.db.commit()
        await self.db.refresh(playlist)
        return playlist
    
    async def delete(self, playlist_id: int, user_id: int) -> None:
        """Delete a playlist."""
        playlist = await self.get_by_id(playlist_id, user_id)
        await self.db.delete(playlist)
        await self.db.commit()
```

### 5. API Routes

```python
# app/api/routes/playlists.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.playlist import PlaylistCreate, PlaylistUpdate, PlaylistResponse
from app.services.playlist_service import PlaylistService

router = APIRouter(prefix="/playlists", tags=["playlists"])

@router.get("/", response_model=List[PlaylistResponse])
async def list_playlists(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all playlists for the current user."""
    service = PlaylistService(db)
    return await service.get_all(current_user.id)

@router.get("/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single playlist by ID."""
    service = PlaylistService(db)
    return await service.get_by_id(playlist_id, current_user.id)

@router.post("/", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    playlist: PlaylistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new playlist."""
    service = PlaylistService(db)
    return await service.create(playlist, current_user.id)

@router.put("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: int,
    playlist: PlaylistUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing playlist."""
    service = PlaylistService(db)
    return await service.update(playlist_id, playlist, current_user.id)

@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a playlist."""
    service = PlaylistService(db)
    await service.delete(playlist_id, current_user.id)
```

### 6. Exception Handling

```python
# app/core/exceptions.py
class AudiovaultException(Exception):
    """Base exception for Audiovault."""
    def __init__(self, message: str, code: str, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

class PlaylistNotFoundError(AudiovaultException):
    def __init__(self, playlist_id: int):
        super().__init__(
            message=f"Playlist {playlist_id} not found",
            code="PLAYLIST_NOT_FOUND",
            status_code=404
        )

class DownloadFailedError(AudiovaultException):
    def __init__(self, track_name: str, reason: str):
        super().__init__(
            message=f"Failed to download {track_name}: {reason}",
            code="DOWNLOAD_FAILED",
            status_code=500
        )

# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

@app.exception_handler(AudiovaultException)
async def audiovault_exception_handler(request: Request, exc: AudiovaultException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message
            }
        }
    )
```

## 🛡️ Security Best Practices

### Password Hashing

```python
# app/core/security.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### JWT Authentication

```python
# app/core/security.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "your-secret-key-from-env"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Fetch user from database
    # ...
    return user
```

## 🧪 Testing

### Pytest Configuration

```python
# backend/tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import get_db
from app.models.base import Base

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session
    
    await engine.dispose()

@pytest_asyncio.fixture
async def client(db_session):
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers():
    token = create_access_token({"sub": 1})
    return {"Authorization": f"Bearer {token}"}
```

### Example Test

```python
# backend/tests/test_api/test_playlists.py
import pytest

@pytest.mark.asyncio
async def test_create_playlist(client, auth_headers):
    response = await client.post(
        "/api/playlists",
        json={
            "name": "Test Playlist",
            "service_name": "spotify",
            "external_id": "abc123",
            "url": "https://spotify.com/playlist/abc123"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Playlist"
    assert data["service_name"] == "spotify"
    assert "id" in data

@pytest.mark.asyncio
async def test_get_playlist_not_found(client, auth_headers):
    response = await client.get("/api/playlists/999", headers=auth_headers)
    
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PLAYLIST_NOT_FOUND"
```

## 🚀 Performance Optimization

### Eager Loading (Avoid N+1 Queries)

```python
from sqlalchemy.orm import selectinload

# BAD: N+1 query problem
playlists = await db.execute(select(Playlist))
for playlist in playlists.scalars():
    print(playlist.tracks)  # Triggers separate query for each playlist!

# GOOD: Eager loading
playlists = await db.execute(
    select(Playlist).options(selectinload(Playlist.tracks))
)
for playlist in playlists.scalars():
    print(playlist.tracks)  # No additional queries
```

### Connection Pooling

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # Max connections
    max_overflow=10,       # Extra connections when pool full
    pool_timeout=30,       # Wait timeout (seconds)
    pool_recycle=3600,     # Recycle connections after 1 hour
)
```

### Background Tasks

```python
from fastapi import BackgroundTasks

async def send_email(email: str, message: str):
    # Simulate slow email sending
    await asyncio.sleep(5)

@router.post("/playlists/import")
async def import_playlist(
    url: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    service = PlaylistService(db)
    playlist = await service.import_playlist(url)
    
    # Send confirmation email in background
    background_tasks.add_task(send_email, "user@example.com", "Import complete")
    
    return playlist
```

## 📝 Documentation

FastAPI auto-generates documentation:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

Add docstrings to routes for better docs:

```python
@router.post("/playlists/", response_model=PlaylistResponse)
async def create_playlist(
    playlist: PlaylistCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new playlist.
    
    - **name**: Playlist name (required)
    - **service_name**: Platform (spotify, youtube, deezer, soundcloud)
    - **external_id**: Platform-specific playlist ID
    - **url**: Optional playlist URL
    
    Returns the created playlist with assigned ID.
    """
    service = PlaylistService(db)
    return await service.create(playlist)
```

---

**Remember:** Always follow async patterns, use dependency injection, and write tests for critical paths.
