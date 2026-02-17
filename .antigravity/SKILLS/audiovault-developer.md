# Skill: Audiovault Developer

## Core Expertise
You are an expert Audiovault developer with deep knowledge of music library management, multi-platform integration, and self-hosted applications.

## Domain Knowledge

### Music Platforms Supported
1. **Spotify** - OAuth, playlist/album/liked songs import
2. **YouTube** - Playlist/video/channel import, geo-restriction handling
3. **Deezer** - Native search, artist profiles
4. **SoundCloud** - Tracks, playlists, user libraries
5. **Apple Music** - Playlist and library import
6. **Tidal** - High-quality audio focus
7. **Amazon Music** - Playlist integration

### Download Architecture
- **Primary Engine**: yt-dlp (1000+ site support)
- **Fallback Strategy**: 
  1. Try original URL
  2. Try alternative search queries ("Official Audio", "Lyrics Video")
  3. Try cross-platform (e.g., SoundCloud if YouTube fails)
  4. Use proxies (Invidious) for geo-restrictions
- **Quality Options**: MP3 (128/192/320kbps), FLAC (lossless)
- **Post-Processing**: Mutagen for ID3 tagging

### Key Services

#### Backend Services (app/services/)
- `download_service.py`: Core download logic and orchestration
- `extractors/`: Platform-specific URL extractors
- `metadata_service.py`: ID3 tagging and file management
- `watchlist_service.py`: Auto-sync scheduler
- `subsonic_service.py`: Subsonic API implementation

#### API Endpoints (app/api/endpoints/)
- `downloads.py`: Download requests and status
- `library.py`: Browse and manage library
- `subsonic.py`: Subsonic protocol (for mobile apps)
- `auth.py`: JWT authentication
- `recommendations.py`: Last.fm integration

### Database Schema (SQLAlchemy)
- **Track**: Metadata, file path, source platform
- **Playlist**: User-created or imported collections
- **DownloadHistory**: Deduplication and audit trail
- **Watchlist**: Auto-sync configurations
- **User**: Authentication and preferences

### Frontend Components
- **Library View**: Hierarchical (Service → Playlist → Tracks)
- **Audio Player**: HTML5 + Web Audio API visualizer
- **Download Queue**: Real-time WebSocket updates
- **Search**: Universal multi-platform search
- **Settings**: Theme, quality, API keys

## Development Patterns

### Adding a New Platform
1. Create extractor in `app/services/extractors/new_platform.py`
2. Implement `extract_tracks()` method
3. Register in `app/services/download_service.py`
4. Add platform enum to models
5. Update frontend platform selector
6. Add tests

### Adding an API Endpoint
```python
# app/api/endpoints/new_feature.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

router = APIRouter()

@router.get("/new-feature")
async def get_new_feature(db: AsyncSession = Depends(get_db)):
    # Async database operations
    return {"status": "success"}
```

### WebSocket Progress Updates
```python
from app.websocket.manager import manager

await manager.send_progress(
    user_id=user.id,
    task_id=task_id,
    progress=50,
    message="Downloading track..."
)
```

## Common Tasks

### Debugging Download Failures
1. Check `DownloadHistory` for previous attempts
2. Test yt-dlp directly: `yt-dlp -F <url>`
3. Verify geo-restrictions (try proxy)
4. Check extractor implementation
5. Review fallback logic execution

### Optimizing Database Queries
```python
# ❌ Bad: N+1 query problem
tracks = await session.execute(select(Track))
for track in tracks:
    playlist = await session.get(Playlist, track.playlist_id)

# ✅ Good: Eager loading
tracks = await session.execute(
    select(Track).options(selectinload(Track.playlist))
)
```

### Testing Subsonic Compatibility
1. Enable legacy auth in client
2. Test endpoint: `/rest/ping.view`
3. Verify range request support for streaming
4. Check transcoding if needed

## Code Style Guidelines
- **Backend**: Black formatter, isort, type hints everywhere
- **Frontend**: Prettier, ESLint, strict TypeScript
- **Naming**: snake_case (Python), camelCase (TypeScript)
- **Async**: Always use async/await in backend
- **Error Handling**: Specific exceptions, proper HTTP status codes

## Security Considerations
- JWT tokens with expiration
- Rate limiting on download endpoints
- Input validation with Pydantic
- SQL injection prevention (SQLAlchemy ORM)
- CORS configuration for allowed origins
- Secrets in environment variables only

## Performance Best Practices
- Use Redis for caching API responses
- Limit concurrent downloads (configurable)
- Stream large files (don't load into memory)
- Index database columns used in WHERE clauses
- Lazy load frontend components
- Debounce search inputs
