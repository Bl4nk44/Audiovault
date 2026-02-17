# 🏗️ System Patterns: Architecture Guidelines

## Core Architectural Principles

### 1. Separation of Concerns
- **Backend**: Business logic, data access, external integrations
- **Frontend**: UI/UX, state management, user interactions
- **Never mix**: Frontend should not contain business logic

### 2. API-First Design
- All backend functionality exposed via REST API
- Frontend communicates exclusively through API
- Third-party integrations possible via documented endpoints

### 3. Stateless Services
- Backend API is stateless (except WebSocket connections)
- Session state stored in JWT tokens
- Persistent data in database, transient data in Redis

### 4. Fail-Safe Operations
- Graceful degradation when services unavailable
- Comprehensive error handling with user-friendly messages
- Retry logic with exponential backoff

## Backend Patterns

### Service Layer Pattern
```python
# app/services/playlist_service.py
class PlaylistService:
    """Handles all playlist-related business logic"""
    
    def __init__(self, db: AsyncSession, downloader: DownloadService):
        self.db = db
        self.downloader = downloader
    
    async def import_playlist(self, url: str, user_id: int) -> Playlist:
        # 1. Validate URL
        # 2. Fetch metadata from streaming service
        # 3. Create playlist record
        # 4. Queue tracks for download
        # 5. Return playlist object
        pass
```

### Repository Pattern
```python
# app/repositories/playlist_repository.py
class PlaylistRepository:
    """Database access for playlists"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, playlist_id: int) -> Optional[Playlist]:
        result = await self.db.execute(
            select(Playlist).where(Playlist.id == playlist_id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, playlist_data: PlaylistCreate) -> Playlist:
        playlist = Playlist(**playlist_data.dict())
        self.db.add(playlist)
        await self.db.commit()
        await self.db.refresh(playlist)
        return playlist
```

### Dependency Injection
```python
# app/api/routes/playlists.py
from fastapi import Depends
from app.core.deps import get_db, get_current_user

@router.post("/playlists/import")
async def import_playlist(
    url: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    service = PlaylistService(db)
    return await service.import_playlist(url, user.id)
```

### Error Handling
```python
# app/core/exceptions.py
class AudiovaultException(Exception):
    """Base exception for Audiovault"""
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(self.message)

class PlaylistNotFoundError(AudiovaultException):
    def __init__(self, playlist_id: int):
        super().__init__(
            message=f"Playlist {playlist_id} not found",
            code="PLAYLIST_NOT_FOUND"
        )

# app/core/handlers.py
@app.exception_handler(AudiovaultException)
async def audiovault_exception_handler(request, exc: AudiovaultException):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message
            }
        }
    )
```

## Frontend Patterns

### Component Structure
```typescript
// src/components/PlaylistCard/PlaylistCard.tsx
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
      {/* Component implementation */}
    </div>
  );
};
```

### Custom Hooks
```typescript
// src/hooks/usePlaylist.ts
import { useQuery, useMutation } from '@tanstack/react-query';
import { playlistApi } from '@/services/api';

export const usePlaylist = (playlistId: number) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['playlist', playlistId],
    queryFn: () => playlistApi.getById(playlistId)
  });

  const deleteMutation = useMutation({
    mutationFn: playlistApi.delete,
    onSuccess: () => {
      // Invalidate queries
    }
  });

  return {
    playlist: data,
    isLoading,
    error,
    deletePlaylist: deleteMutation.mutate
  };
};
```

### API Service Pattern
```typescript
// src/services/api/playlistApi.ts
import axios from 'axios';
import { Playlist, PlaylistCreate } from '@/types';

const API_URL = import.meta.env.VITE_API_URL;

export const playlistApi = {
  async getAll(): Promise<Playlist[]> {
    const { data } = await axios.get(`${API_URL}/playlists`);
    return data.data;
  },

  async getById(id: number): Promise<Playlist> {
    const { data } = await axios.get(`${API_URL}/playlists/${id}`);
    return data.data;
  },

  async create(playlist: PlaylistCreate): Promise<Playlist> {
    const { data } = await axios.post(`${API_URL}/playlists`, playlist);
    return data.data;
  },

  async delete(id: number): Promise<void> {
    await axios.delete(`${API_URL}/playlists/${id}`);
  }
};
```

## Download Fallback Pattern

### Intelligent Fallback Chain
```python
# app/services/download_service.py
class DownloadService:
    async def download_track(self, track: Track) -> DownloadResult:
        strategies = [
            self._download_from_primary_source,
            self._try_alternative_query,
            self._try_cross_platform,
            self._try_with_proxy
        ]
        
        for strategy in strategies:
            try:
                result = await strategy(track)
                if result.success:
                    return result
            except Exception as e:
                logger.warning(f"Strategy {strategy.__name__} failed: {e}")
                continue
        
        return DownloadResult(success=False, error="All strategies exhausted")
    
    async def _download_from_primary_source(self, track: Track):
        # Try original URL
        pass
    
    async def _try_alternative_query(self, track: Track):
        # Try "Official Audio", "Lyrics Video" queries
        pass
    
    async def _try_cross_platform(self, track: Track):
        # Search on SoundCloud, Deezer if YouTube fails
        pass
    
    async def _try_with_proxy(self, track: Track):
        # Use Invidious proxy for geo-restricted content
        pass
```

## Testing Patterns

### Unit Tests (Backend)
```python
# backend/tests/services/test_playlist_service.py
import pytest
from app.services.playlist_service import PlaylistService

@pytest.mark.asyncio
async def test_import_playlist_success(db_session, mock_downloader):
    service = PlaylistService(db_session, mock_downloader)
    
    playlist = await service.import_playlist(
        url="https://spotify.com/playlist/123",
        user_id=1
    )
    
    assert playlist.id is not None
    assert playlist.service_name == "spotify"
    assert len(playlist.tracks) > 0
```

### Component Tests (Frontend)
```typescript
// frontend/src/components/PlaylistCard/PlaylistCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { PlaylistCard } from './PlaylistCard';

describe('PlaylistCard', () => {
  const mockPlaylist = {
    id: 1,
    name: 'Test Playlist',
    service_name: 'spotify',
    track_count: 10
  };

  it('renders playlist information', () => {
    render(<PlaylistCard playlist={mockPlaylist} onPlay={jest.fn()} onDelete={jest.fn()} />);
    
    expect(screen.getByText('Test Playlist')).toBeInTheDocument();
    expect(screen.getByText('10 tracks')).toBeInTheDocument();
  });

  it('calls onPlay when play button clicked', () => {
    const onPlay = jest.fn();
    render(<PlaylistCard playlist={mockPlaylist} onPlay={onPlay} onDelete={jest.fn()} />);
    
    fireEvent.click(screen.getByRole('button', { name: /play/i }));
    expect(onPlay).toHaveBeenCalledWith(1);
  });
});
```

## Code Style Guidelines

### Python (Backend)
- **Formatting**: Black (line length 100)
- **Linting**: Ruff with strict rules
- **Type Hints**: Required for all function signatures
- **Docstrings**: Google style for public APIs
- **Imports**: Absolute imports, sorted by isort

### TypeScript (Frontend)
- **Formatting**: Prettier (2-space indentation)
- **Linting**: ESLint with TypeScript rules
- **Naming**: PascalCase for components, camelCase for functions/variables
- **Exports**: Named exports preferred over default
- **Props**: Interface definitions for all components

### Commit Conventions
- **Format**: `type(scope): description`
- **Types**: feat, fix, docs, style, refactor, test, chore
- **Examples**:
  - `feat(playlist): add Tidal integration`
  - `fix(download): handle geo-restricted content`
  - `docs(readme): update installation instructions`

## Performance Best Practices

### Database Optimization
- Use async SQLAlchemy for I/O-bound operations
- Index frequently queried columns
- Eager loading for relationships to avoid N+1 queries
- Connection pooling for concurrent requests

### Frontend Optimization
- Code splitting by route
- Lazy loading for non-critical components
- Image optimization (WebP, lazy loading)
- Debounce search inputs
- Virtual scrolling for large lists

### Caching Strategy
- **Redis**: Playlist metadata (TTL: 1 hour)
- **Browser**: Static assets (aggressive caching)
- **API**: ETags for conditional requests
- **Query Cache**: React Query for client-side caching
