# Technical Context: Audiovault

## Architecture Overview

### System Design
- **Pattern**: Monolithic application with clear separation of concerns
- **Deployment**: Docker Compose multi-container setup
- **Database**: SQLite (default) or PostgreSQL (production)
- **Cache**: Redis for session management and task queuing
- **Storage**: Local filesystem for music files

### Backend Stack
- **Framework**: FastAPI (Python 3.11+)
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Task Scheduler**: APScheduler
- **Download Engine**: yt-dlp
- **Audio Processing**: Mutagen (ID3 tags)
- **API Protocol**: REST + WebSocket (real-time updates)
- **Authentication**: JWT tokens

### Frontend Stack
- **Framework**: React 18
- **Language**: TypeScript
- **Styling**: TailwindCSS v4
- **Animation**: Framer Motion
- **State Management**: React Query + Context API
- **Build Tool**: Vite
- **Audio**: HTML5 Audio API + Web Audio API (visualizer)

## Key Technical Decisions

### Why FastAPI?
- Native async support for concurrent downloads
- Automatic OpenAPI documentation
- Type safety with Pydantic
- High performance (on par with Node.js)

### Why yt-dlp?
- Supports 1000+ sites including all major music platforms
- Active maintenance and updates
- Built-in format selection and post-processing
- Proxy support for geo-restrictions

### Why SQLite?
- Zero configuration for self-hosters
- Sufficient for single-user workloads
- Easy backup (single file)
- PostgreSQL optional for scale

## Critical Code Paths

### Download Pipeline
1. **Request Validation** (`app/api/endpoints/downloads.py`)
2. **URL Extraction** (`app/services/extractors/*`)
3. **Duplicate Check** (`app/services/download_service.py`)
4. **yt-dlp Execution** (with fallback logic)
5. **Metadata Tagging** (`app/services/metadata_service.py`)
6. **Database Record** (track + download history)
7. **WebSocket Notification** (progress updates)

### Subsonic API
- **Implementation**: `app/api/endpoints/subsonic.py`
- **Version**: Subsonic v1.16.1
- **Auth**: Token-based or legacy plaintext
- **Streaming**: Range request support
- **Tested With**: Sonixd, Amperfy, DSub, Symfonium

## Performance Characteristics

### Bottlenecks
1. **yt-dlp Execution**: CPU-bound (ffmpeg transcoding)
2. **Metadata Extraction**: IO-bound (file reads)
3. **Database Queries**: Minimal (properly indexed)

### Optimization Strategies
- Async/await throughout backend
- Parallel downloads (configurable limit)
- Redis caching for API responses
- Lazy loading in frontend (React.lazy)
- Audio file chunking for streaming

## Dependencies to Watch
- **yt-dlp**: Breaking changes in extractors
- **FastAPI/Pydantic**: v2 migration complete
- **SQLAlchemy**: Using 2.0 async patterns
- **TailwindCSS**: v4 alpha (bleeding edge)

## Testing Strategy
- **Backend**: pytest + pytest-asyncio (80%+ coverage goal)
- **API Tests**: TestClient (FastAPI)
- **Frontend**: Vitest + React Testing Library
- **E2E**: Planned (Playwright)
- **Security**: Semgrep, Trivy, Snyk, GitGuardian

## Deployment Considerations
- **Reverse Proxy**: Nginx/Traefik compatible
- **Environment Variables**: 20+ configuration options
- **Volume Mounts**: `/app/data` (database), `/app/downloads` (music)
- **Networking**: Frontend must reach backend (BACKEND_URL config)
- **Security**: HTTPS required for production, CORS configured
