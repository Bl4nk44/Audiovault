---
name: audiovault-developer
description: Expert knowledge of Audiovault architecture, features, and development practices
---

# Audiovault Developer Skill

## 🎯 Purpose

This skill transforms you into an expert Audiovault developer with deep knowledge of the project's architecture, features, and conventions.

## 📚 Project Knowledge

### What is Audiovault?

Audiovault is a **self-hosted music library manager** that imports playlists from 7+ streaming platforms (Spotify, YouTube, Deezer, SoundCloud, Apple Music, Tidal, Amazon Music) and downloads tracks locally with intelligent fallback mechanisms.

**Key Features:**
- Multi-platform playlist import
- Robust download fallback system (cross-platform search, proxy support)
- Personal streaming server (Subsonic API)
- Watchlist with auto-sync (60-minute intervals)
- Beautiful glassmorphism UI with audio visualizer
- Last.fm integration (scrobbling, recommendations)

### Architecture Overview

```
Frontend (React + TypeScript)
    ↓
    REST API + WebSocket
    ↓
Backend (FastAPI + Python)
    ├─> SQLite/PostgreSQL (Data)
    ├─> Redis (Cache)
    ├─> yt-dlp (Downloads)
    ├─> APScheduler (Background jobs)
    └─> External APIs (Spotify, YouTube, etc.)
```

### Directory Structure (Critical Paths)

```
Audiovault/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # API endpoints
│   │   ├── services/         # Business logic
│   │   ├── models/           # Database models
│   │   ├── schemas/          # Pydantic validation
│   │   ├── core/             # Config, security
│   │   └── main.py           # App entry point
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   ├── services/api/     # API clients
│   │   └── hooks/            # Custom hooks
│   └── package.json
├── memory-bank/          # AI agent memory
├── .agent/               # AI agent config
└── docker-compose.yml    # Deployment
```

## 🔑 Key Concepts

### 1. Download Fallback Chain

When a track download fails, Audiovault tries multiple strategies:

1. **Primary Source**: Original URL from platform
2. **Alternative Queries**: "Official Audio", "Lyrics Video"
3. **Cross-Platform**: Try SoundCloud if YouTube fails
4. **Proxy**: Use Invidious for geo-restricted content

Implementation: `backend/app/services/download_service.py`

### 2. Service Layer Pattern

Business logic lives in services, NOT in API routes:

```python
# CORRECT
@router.post("/playlists/import")
async def import_playlist(
    url: str,
    db: AsyncSession = Depends(get_db)
):
    service = PlaylistService(db)
    return await service.import_playlist(url)

# WRONG (logic in route)
@router.post("/playlists/import")
async def import_playlist(url: str, db: AsyncSession = Depends(get_db)):
    # ... 50 lines of business logic ...
```

### 3. Async Everything

Backend uses async SQLAlchemy and async FastAPI:

```python
# CORRECT
async def get_playlist(db: AsyncSession, playlist_id: int):
    result = await db.execute(select(Playlist).where(Playlist.id == playlist_id))
    return result.scalar_one_or_none()

# WRONG (blocking)
def get_playlist(db: Session, playlist_id: int):
    return db.query(Playlist).filter(Playlist.id == playlist_id).first()
```

### 4. React Query for State

Frontend uses React Query for server state:

```typescript
// CORRECT
const { data: playlists, isLoading } = useQuery({
  queryKey: ['playlists'],
  queryFn: playlistApi.getAll
});

// WRONG (manual state management for server data)
const [playlists, setPlaylists] = useState([]);
useEffect(() => {
  fetch('/api/playlists').then(res => res.json()).then(setPlaylists);
}, []);
```

### 5. WebSocket for Real-Time Updates

Download progress uses WebSocket notifications:

```python
# Backend
await websocket_manager.broadcast({
    "type": "download_progress",
    "playlist_id": 123,
    "progress": 45
})
```

```typescript
// Frontend
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'download_progress') {
    updateProgress(data.playlist_id, data.progress);
  }
};
```

## 🛠️ Development Workflows

### Adding a New Streaming Platform

1. Create service in `backend/app/services/<platform>_service.py`
2. Implement:
   - `parse_url(url: str) -> ParsedURL`
   - `fetch_playlist(url: str) -> PlaylistData`
   - `search_track(query: str) -> TrackURL`
3. Register in `backend/app/services/platform_registry.py`
4. Add UI components in `frontend/src/components/platforms/`
5. Add platform logo and styling
6. Update documentation

### Adding a New API Endpoint

1. Define Pydantic schema in `backend/app/schemas/`
2. Implement service method in `backend/app/services/`
3. Create route in `backend/app/api/routes/`
4. Add frontend API client in `frontend/src/services/api/`
5. Write tests in `backend/tests/` and `frontend/src/__tests__/`

### Database Migration

1. Modify model in `backend/app/models/`
2. Generate migration:
   ```bash
   cd backend
   alembic revision --autogenerate -m "description"
   ```
3. Review generated migration in `backend/alembic/versions/`
4. Test migration:
   ```bash
   alembic upgrade head  # Apply
   alembic downgrade -1  # Rollback
   ```
5. Commit migration file

## 🧑‍💻 Code Conventions

### Backend (Python)

- **Formatting**: Black (line length 100)
- **Linting**: Ruff
- **Type Hints**: Required for all function signatures
- **Docstrings**: Google style for public APIs
- **Imports**: Absolute imports, sorted

```python
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.playlist import PlaylistCreate, PlaylistResponse
from app.services.playlist_service import PlaylistService


router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.post("/", response_model=PlaylistResponse)
async def create_playlist(
    playlist: PlaylistCreate,
    db: AsyncSession = Depends(get_db)
) -> PlaylistResponse:
    """Create a new playlist.
    
    Args:
        playlist: Playlist data
        db: Database session
        
    Returns:
        Created playlist with ID
    """
    service = PlaylistService(db)
    return await service.create(playlist)
```

### Frontend (TypeScript)

- **Formatting**: Prettier (2-space indentation)
- **Linting**: ESLint with TypeScript rules
- **Components**: Functional components with TypeScript
- **Props**: Interface definitions
- **Exports**: Named exports preferred

```typescript
import React from 'react';
import { Playlist } from '@/types';

interface PlaylistCardProps {
  playlist: Playlist;
  onPlay: (id: number) => void;
  onDelete: (id: number) => void;
}

export const PlaylistCard: React.FC<PlaylistCardProps> = ({
  playlist,
  onPlay,
  onDelete
}) => {
  return (
    <div className="playlist-card">
      <h3>{playlist.name}</h3>
      <button onClick={() => onPlay(playlist.id)}>Play</button>
      <button onClick={() => onDelete(playlist.id)}>Delete</button>
    </div>
  );
};
```

### Commit Messages

```bash
feat(playlist): add Bandcamp integration
fix(download): handle geo-restricted content
docs(readme): update installation instructions
refactor(backend): improve service layer structure
test(frontend): add PlaylistCard component tests
```

## 🧑‍🔬 Testing Strategy

### Backend Tests

- **Location**: `backend/tests/`
- **Framework**: pytest with pytest-asyncio
- **Coverage**: Aim for 80%+
- **Fixtures**: Reusable in `conftest.py`

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_playlist(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/playlists",
        json={"name": "Test Playlist", "service": "spotify"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Test Playlist"
```

### Frontend Tests

- **Location**: `frontend/src/__tests__/` or `Component.test.tsx`
- **Framework**: Jest + React Testing Library
- **Focus**: User interactions, not implementation

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { PlaylistCard } from './PlaylistCard';

test('renders playlist name', () => {
  const playlist = { id: 1, name: 'My Playlist', trackCount: 10 };
  render(<PlaylistCard playlist={playlist} onPlay={jest.fn()} onDelete={jest.fn()} />);
  
  expect(screen.getByText('My Playlist')).toBeInTheDocument();
});
```

## 🔗 Integration Points

### Streaming Platform APIs

- **Spotify**: OAuth 2.0, requires client ID/secret
- **YouTube**: yt-dlp handles extraction
- **Deezer**: Public API, no authentication needed
- **SoundCloud**: Client ID required
- **Apple Music**: MusicKit JS (browser-based)

### Subsonic API

- **Version**: v1.16.1
- **Authentication**: Legacy (plaintext password) or token-based
- **Endpoints**: `/rest/ping`, `/rest/getPlaylists`, `/rest/stream`
- **Clients**: Verified with Sonixd, Amperfy

### Last.fm API

- **OAuth**: 3-legged authentication
- **Scrobbling**: Track submission after 50% played
- **Recommendations**: Based on user's listening history

## ⚡ Performance Tips

1. **Database Queries**: Always use `selectinload()` for relationships to avoid N+1
2. **React Rendering**: Use `React.memo()` for expensive components
3. **API Calls**: Batch requests where possible (e.g., bulk track imports)
4. **Downloads**: Rate limit to avoid IP bans (configurable per platform)
5. **WebSocket**: Throttle progress updates (max 10/second per playlist)

## 🐛 Common Pitfalls

❌ **Forgetting to await async functions** → Returns coroutine object, not result  
❌ **Not handling download failures** → Use try/except with fallback chain  
❌ **Modifying database models without migration** → Database out of sync  
❌ **Storing secrets in code** → Use .env file  
❌ **Not validating user input** → Use Pydantic schemas  
❌ **Mixing sync and async code** → Backend must be fully async  

## 📌 Quick Commands

```bash
# Start development environment
docker compose up -d --build

# Backend logs
docker compose logs -f backend

# Frontend logs
docker compose logs -f frontend

# Run backend tests
docker compose exec backend pytest

# Run frontend tests
docker compose exec frontend npm test

# Database shell
docker compose exec backend alembic current

# Format code
cd backend && black . && ruff check --fix .
cd frontend && npm run format && npm run lint --fix
```

## 📄 Documentation

- **Main README**: `README.md`
- **Contributing**: `CONTRIBUTING.md`
- **API Docs**: Auto-generated at `/docs` (FastAPI Swagger UI)
- **Wiki**: GitHub Wiki (Getting Started, Configuration, Usage)
- **Changelog**: `CHANGELOG.md` (maintained via cliff.toml)

---

**Remember:** Always read `memory-bank/` files first to understand current project state before making changes.
