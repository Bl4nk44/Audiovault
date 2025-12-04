# 📚 SPOTIZERR 3.0 - DOKUMENTACJA TECHNICZNA DLA DEVELOPERÓW

**Dokument:** Techniczna Specyfikacja Systemu  
**Wersja:** 1.0  
**Data:** Listopad 2025  
**Status:** Gotowe do wdrożenia  

---

## 📖 SPIS TREŚCI

1. [Quick Start](#1-quick-start)
2. [Architektura Systemu](#2-architektura-systemu)
3. [Backend Specyfikacja](#3-backend-specyfikacja)
4. [Frontend Specyfikacja](#4-frontend-specyfikacja)
5. [API Reference](#5-api-reference)
6. [Schematy Bazy Danych](#6-schematy-bazy-danych)
7. [WebSocket Events](#7-websocket-events)
8. [Authentication Flow](#8-authentication-flow)
9. [Error Handling](#9-error-handling)
10. [Development Setup](#10-development-setup)
11. [Testing Strategy](#11-testing-strategy)
12. [Deployment Guide](#12-deployment-guide)
13. [Best Practices](#13-best-practices)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. QUICK START

### Wymagania Systemowe

```
Minimum:
- Docker 25.x + Docker Compose
- 4GB RAM
- 10GB free disk space
- macOS 12+, Windows 10+, Linux (Ubuntu 20.04+)

Rekomendowane:
- Docker Desktop latest
- 8GB+ RAM
- 50GB+ SSD
- Node.js 20.x (local dev)
- Python 3.12+ (local dev)
```

### Uruchomienie (5 minut)

```bash
# 1. Klonuj repo
git clone https://github.com/yourusername/spotizerr-3.0.git
cd spotizerr-3.0

# 2. Konfiguracja
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. Edytuj .env (dodaj API keys)
# Spotify: https://developer.spotify.com/dashboard
# YouTube: https://console.cloud.google.com
# Deezer: https://developers.deezer.com/myapps

# 4. Start
docker-compose up -d

# 5. Migracje bazy
docker-compose exec backend alembic upgrade head

# 6. Dostęp
# Frontend:  http://localhost:3000
# API Docs:  http://localhost:8000/api/docs
# Admin:     http://localhost:8000/admin
```

---

## 2. ARCHITEKTURA SYSTEMU

### 2.1 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         SPOTIZERR 3.0                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CLIENT LAYER                                                   │
│  ├─ React Frontend (port 3000)                                  │
│  │  └─ TypeScript + Tailwind CSS                               │
│  ├─ Vite Dev Server (hot reload)                                │
│  └─ Socket.IO Client                                            │
│                                                                 │
│  API LAYER (FastAPI - port 8000)                               │
│  ├─ /api/v1/auth/* (JWT validation)                            │
│  ├─ /api/v1/spotify/* (Spotify integration)                    │
│  ├─ /api/v1/youtube/* (YouTube integration)                    │
│  ├─ /api/v1/deezer/* (Deezer integration)                      │
│  ├─ /api/v1/downloads/* (Download management)                  │
│  ├─ /api/v1/watchlist/* (Watchlist management)                 │
│  └─ /ws (WebSocket connection)                                 │
│                                                                 │
│  SERVICE LAYER                                                  │
│  ├─ Authentication Manager (JWT + OAuth2)                      │
│  ├─ Download Manager (async queue, resumable)                  │
│  ├─ Metadata Service (unified track model)                     │
│  ├─ Audio Processor (FFmpeg, ID3 tagging)                      │
│  ├─ Watchlist Engine (cron jobs, APScheduler)                  │
│  └─ Cache Manager (Redis)                                      │
│                                                                 │
│  INTEGRATION LAYER                                              │
│  ├─ Spotify API (REST) + librespot (download)                  │
│  ├─ YouTube Data API (REST) + yt-dlp (download)                │
│  ├─ Deezer API (REST) + deezspot (download)                    │
│  ├─ FFmpeg (audio conversion)                                  │
│  └─ Mutagen (ID3/MP4 tagging)                                  │
│                                                                 │
│  DATA LAYER                                                     │
│  ├─ PostgreSQL (port 5432) - Relational data                   │
│  ├─ Redis (port 6379) - Cache + Sessions                       │
│  └─ File System - Downloaded music                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow Diagram

```
USER REQUEST
    ↓
FRONTEND (React)
    ↓ HTTP/WebSocket
FASTAPI ROUTER
    ↓
MIDDLEWARE (Auth, CORS, Error)
    ↓
SERVICE LAYER
    ├─ Check Cache (Redis)
    ├─ Call Integration (Spotify/YouTube/Deezer)
    ├─ Normalize Response
    └─ Store in Cache
    ↓
DATABASE (PostgreSQL)
    ↓
RESPONSE JSON
    ↓
FRONTEND (React)
    ↓
USER SEES RESULT
```

### 2.3 Directory Structure

```
spotizerr-3.0/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   ├── dependencies.py       # FastAPI dependencies
│   │   │   └── constants.py          # App constants
│   │   │
│   │   ├── services/
│   │   │   ├── auth_manager.py       # Central auth
│   │   │   ├── spotify_service.py    # Spotify wrapper
│   │   │   ├── youtube_service.py    # YouTube wrapper
│   │   │   ├── deezer_service.py     # Deezer wrapper
│   │   │   ├── download_manager.py   # Async queue
│   │   │   ├── watchlist_engine.py   # Cron jobs
│   │   │   ├── metadata_service.py   # Unified model
│   │   │   ├── cache_manager.py      # Redis cache
│   │   │   ├── ai_service.py         # AI recommendations & analysis
│   │   │   └── socket_manager.py     # WebSocket manager
│   │   │
│   │   ├── models/
│   │   │   ├── user.py               # User model
│   │   │   ├── track.py              # Track model
│   │   │   ├── download.py           # Download model
│   │   │   ├── watchlist.py          # Watchlist model
│   │   │   ├── credentials.py        # Service credentials
│   │   │   └── schemas.py            # Pydantic schemas
│   │   │
│   │   ├── db/
│   │   │   ├── base.py               # Base model
│   │   │   ├── database.py           # Session + engine
│   │   │   └── migrations/           # Alembic migrations
│   │   │
│   │   ├── utils/
│   │   │   ├── audio_processor.py    # FFmpeg wrapper
│   │   │   ├── metadata_enricher.py  # ID3 tagging
│   │   │   ├── logger.py             # Logging setup
│   │   │   └── validators.py         # Input validation
│   │   │
│   │   └── __init__.py
│   │
│   ├── main.py                       # App entry point
│   ├── requirements.txt              # Python dependencies
│   ├── Dockerfile                    # Backend container
│   ├── .dockerignore
│   ├── .env.example
│   └── alembic.ini
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── Navbar.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Footer.tsx
│   │   │   │   └── NotificationToast.tsx
│   │   │   │
│   │   │   ├── auth/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   ├── RegisterForm.tsx
│   │   │   │   └── ProtectedRoute.tsx
│   │   │   │
│   │   │   ├── search/
│   │   │   │   ├── SearchBar.tsx
│   │   │   │   ├── SearchResults.tsx
│   │   │   │   └── TrackCard.tsx
│   │   │   │
│   │   │   ├── queue/
│   │   │   │   ├── DownloadQueue.tsx
│   │   │   │   ├── DownloadItem.tsx
│   │   │   │   └── ProgressBar.tsx
│   │   │   │
│   │   │   ├── watchlist/
│   │   │   │   ├── WatchlistManager.tsx
│   │   │   │   ├── WatchlistItem.tsx
│   │   │   │   └── AddWatchModal.tsx
│   │   │   │
│   │   │   └── settings/
│   │   │       ├── SettingsPanel.tsx
│   │   │       ├── APIKeyInput.tsx
│   │   │       └── PreferencesForm.tsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Search.tsx
│   │   │   ├── Queue.tsx
│   │   │   ├── Watchlist.tsx
│   │   │   ├── Settings.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── NotFound.tsx
│   │   │   ├── CreatePlaylist.tsx
│   │   │   ├── LikedSongs.tsx
│   │   │   └── NotFound.tsx
│   │   │
│   │   ├── services/
│   │   │   ├── api.ts                # Axios config
│   │   │   ├── websocket.ts          # Socket.IO client
│   │   │   └── auth.ts               # Auth service
│   │   │
│   │   ├── store/
│   │   │   ├── useStore.ts           # Zustand store
│   │   │   └── slices/               # Store slices
│   │   │
│   │   ├── types/
│   │   │   └── index.ts              # TypeScript types
│   │   │
│   │   ├── styles/
│   │   │   ├── globals.css
│   │   │   └── tailwind.config.ts
│   │   │
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── .env.example
│   └── tailwind.config.ts
│
├── docker-compose.yml
├── .gitignore
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## 3. BACKEND SPECYFIKACJA

### 3.1 Technology Stack

| Komponenta | Technologia | Wersja | Uwagi |
|-----------|-----------|---------|-------|
| Framework | FastAPI | 0.109+ | Async-first |
| Server | Uvicorn | 0.27+ | ASGI |
| ORM | SQLAlchemy | 2.0+ | Async support |
| Validation | Pydantic | 2.5+ | Type hints |
| Database | PostgreSQL | 16+ | Production |
| Cache | Redis | 7+ | Optional |
| Task Queue | APScheduler | - | Cron jobs |
| Spotify | spotipy + librespot | - | Dual approach |
| YouTube | yt-dlp + ytmusicapi | - | Audio extraction |
| Deezer | Custom wrapper | - | Direct API |
| Audio | FFmpeg | - | Conversion |
| Tags | Mutagen | - | ID3/MP4 |

### 3.2 Installation & Setup

```bash
# 1. Backend environment
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Environment variables
cp .env.example .env
# Edit .env with your configuration

# 4. Database initialization
alembic upgrade head

# 5. Run dev server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 6. API Documentation
# Visit: http://localhost:8000/api/docs
# Swagger: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### 3.3 Configuration (core/config.py)

```python
# Required environment variables:
DATABASE_URL=postgresql://user:password@localhost/spotizerr
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
JWT_SECRET_KEY=<generate-strong-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Spotify
SPOTIFY_CLIENT_ID=<your-client-id>
SPOTIFY_CLIENT_SECRET=<your-secret>
SPOTIFY_REDIRECT_URI=http://localhost:3000/auth/callback

# YouTube
YOUTUBE_API_KEY=<your-api-key>

# Deezer
DEEZER_API_KEY=<your-api-key>

# Downloads
DOWNLOAD_DIR=/downloads
MAX_PARALLEL_DOWNLOADS=3
STORAGE_QUOTA_GB=500

# Logging
LOG_LEVEL=INFO
```

### 3.4 Core Models

#### User Model

```python
class User(Base):
    __tablename__ = "users"
    
    id: UUID = Column(UUID, primary_key=True, default=uuid4)
    email: str = Column(String(255), unique=True, index=True)
    username: str = Column(String(50), unique=True, index=True)
    hashed_password: str = Column(String(255))
    is_active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    credentials = relationship("ServiceCredentials", back_populates="user")
    downloads = relationship("Download", back_populates="user")
    watchlist = relationship("Watchlist", back_populates="user")
    
    # Preferences (JSONB)
    preferences: dict = Column(JSON, default={
        "theme": "dark",
        "quality": "high",
        "auto_download": False,
        "language": "en"
    })
```

#### Track Model (Unified)

```python
class Track(Base):
    __tablename__ = "tracks"
    
    id: UUID = Column(UUID, primary_key=True, default=uuid4)
    title: str = Column(String(500), index=True)
    artist: str = Column(String(500), index=True)
    album: str = Column(String(500))
    duration_ms: int = Column(Integer)  # milliseconds
    
    # Service IDs (for cross-platform lookup)
    isrc: str = Column(String(20), unique=True, nullable=True)
    spotify_id: str = Column(String(100), nullable=True, unique=True)
    youtube_id: str = Column(String(100), nullable=True, unique=True)
    deezer_id: str = Column(String(100), nullable=True, unique=True)
    
    # Metadata
    metadata: dict = Column(JSON, default={
        "image_url": None,
        "album_art": None,
        "genre": None,
        "year": None,
        "popularity": 0
    })
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    downloads = relationship("Download", back_populates="track")
```

#### Download Model

```python
class Download(Base):
    __tablename__ = "downloads"
    
    id: UUID = Column(UUID, primary_key=True, default=uuid4)
    user_id: UUID = Column(UUID, ForeignKey("users.id"), index=True)
    track_id: UUID = Column(UUID, ForeignKey("tracks.id"))
    
    # Download details
    source: str = Column(String(20))  # spotify, youtube, deezer
    status: str = Column(String(20), default="pending")  
    # pending, downloading, processing, completed, failed
    
    # Progress
    progress: int = Column(Integer, default=0)  # 0-100
    file_path: str = Column(String(500), nullable=True)
    file_size: int = Column(Integer, default=0)  # bytes
    
    # Priority & Scheduling
    priority: int = Column(Integer, default=5)  # 1-10
    
    # Error tracking
    error_message: str = Column(String(1000), nullable=True)
    retry_count: int = Column(Integer, default=0)
    
    # Timestamps
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    started_at: datetime = Column(DateTime, nullable=True)
    completed_at: datetime = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="downloads")
    track = relationship("Track", back_populates="downloads")
```

#### Watchlist Model

```python
class Watchlist(Base):
    __tablename__ = "watchlist"
    
    id: UUID = Column(UUID, primary_key=True, default=uuid4)
    user_id: UUID = Column(UUID, ForeignKey("users.id"), index=True)
    
    # What to watch
    watch_type: str = Column(String(20))  # artist, playlist, channel
    source: str = Column(String(20))      # spotify, youtube, deezer
    source_id: str = Column(String(100))  # platform-specific ID
    source_name: str = Column(String(255))  # "The Weeknd", "Pop Hits"
    
    # Settings
    auto_download: bool = Column(Boolean, default=False)
    check_interval_hours: int = Column(Integer, default=24)
    
    # Status
    last_checked_at: datetime = Column(DateTime, nullable=True)
    new_items_count: int = Column(Integer, default=0)
    
    # Metadata
    metadata: dict = Column(JSON, default={})
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="watchlist")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'source_id', 'source', name='unique_watch'),
    )
```

---

## 4. FRONTEND SPECYFIKACJA

### 4.1 Technology Stack

| Komponenta | Technologia | Wersja |
|-----------|-----------|---------|
| Framework | React | 18.x |
| Bundler | Vite | 5.x |
| Language | TypeScript | 5.3+ |
| Styling | Tailwind CSS | 3.4+ |
| Components | shadcn/ui | Latest |
| State | Zustand | 4.x |
| HTTP | Axios | 1.6+ |
| WebSocket | Socket.IO | 4.7+ |
| Router | React Router | 6.x |
| Icons | Lucide React | Latest |
| Notifications | React Hot Toast | Latest |
| Forms | React Hook Form | Latest |
| Queries | TanStack Query | 5.x |

### 4.2 Installation & Setup

```bash
# 1. Frontend environment
cd frontend
npm create vite@latest . -- --template react-ts
npm install

# 2. Environment
cp .env.example .env
# Edit .env with API URL

# 3. Development
npm run dev
# Visit: http://localhost:5173

# 4. Build for production
npm run build
```

### 4.3 State Management (Zustand Store)

```typescript
// store/useStore.ts
interface AppState {
  // User
  user: User | null
  isAuthenticated: boolean
  setUser: (user: User) => void
  logout: () => void
  
  // Search
  searchResults: Track[]
  selectedSource: 'spotify' | 'youtube' | 'deezer' | 'all'
  setSearchResults: (results: Track[]) => void
  setSelectedSource: (source: string) => void
  
  // Queue
  downloadQueue: Download[]
  addToQueue: (track: Track, source: string) => void
  removeFromQueue: (downloadId: string) => void
  updateProgress: (downloadId: string, progress: number) => void
  
  // Watchlist
  watchlist: WatchlistItem[]
  addToWatchlist: (item: WatchlistItem) => void
  removeFromWatchlist: (watchId: string) => void
  
  // Notifications
  notifications: Toast[]
  showNotification: (message: string, type: 'success' | 'error' | 'info') => void
  
  // Settings
  theme: 'dark' | 'light'
  toggleTheme: () => void
}
```

### 4.4 API Service Layer (services/api.ts)

```typescript
// Axios instance
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 10000,
})

// Request interceptor - dodaj JWT token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor - obsługa błędów
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Refresh token or redirect to login
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API Functions
export const searchTracks = (query: string, source?: string) =>
  apiClient.get('/v1/search', { params: { q: query, source } })

export const getDownloadQueue = () =>
  apiClient.get('/v1/downloads/queue')

export const addDownload = (trackId: string, source: string, quality: string) =>
  apiClient.post('/v1/downloads/add', { track_id: trackId, source, quality })
```

### 4.5 WebSocket Integration (services/websocket.ts)

```typescript
import { io, Socket } from 'socket.io-client'

let socket: Socket | null = null

export const initializeWebSocket = () => {
  socket = io(import.meta.env.VITE_WS_URL || 'http://localhost:8000', {
    auth: {
      token: localStorage.getItem('access_token'),
    },
  })

  // Listen to events
  socket.on('download:progress', (data) => {
    store.updateProgress(data.download_id, data.progress)
  })

  socket.on('download:completed', (data) => {
    store.showNotification(`Download completed: ${data.filename}`, 'success')
  })

  socket.on('download:error', (data) => {
    store.showNotification(`Download failed: ${data.error}`, 'error')
  })

  socket.on('watchlist:update', (data) => {
    store.showNotification(`${data.count} new tracks in watchlist`, 'info')
  })
}

export const emitEvent = (event: string, data: any) => {
  socket?.emit(event, data)
}
```

---

## 5. API REFERENCE

### 5.1 Authentication Endpoints

#### Register User
```
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "username",
  "password": "secure_password"
}

Response (201 Created):
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "username",
  "created_at": "2025-11-27T12:00:00Z"
}
```

#### Login
```
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}

Response (200 OK):
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### Refresh Token
```
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>

Response (200 OK):
{
  "access_token": "new_token...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### Get Current User
```
GET /api/v1/auth/me
Authorization: Bearer <access_token>

Response (200 OK):
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "username",
  "preferences": {
    "theme": "dark",
    "quality": "high"
  }
}
```

### 5.2 Search Endpoints

#### Unified Search
```
GET /api/v1/search?q=blinding+lights&sources=spotify,youtube,deezer
Authorization: Bearer <token>

Response (200 OK):
{
  "query": "blinding lights",
  "results": [
    {
      "id": "track-uuid",
      "title": "Blinding Lights",
      "artist": "The Weeknd",
      "album": "After Hours",
      "duration_ms": 200040,
      "sources": [
        {
          "platform": "spotify",
          "id": "spotify-track-id",
          "score": 100
        },
        {
          "platform": "youtube",
          "id": "youtube-video-id",
          "score": 95
        },
        {
          "platform": "deezer",
          "id": "deezer-track-id",
          "score": 100
        }
      ],
      "image_url": "https://...",
      "best_source": "deezer"
    }
  ],
  "count": 15
}
```

#### Spotify Search
```
GET /api/v1/spotify/search?q=query
Authorization: Bearer <token>

Response: [List of Spotify tracks]
```

#### YouTube Search
```
GET /api/v1/youtube/search?q=query&type=song
Authorization: Bearer <token>

Response: [List of YouTube videos/music]
```

#### Deezer Search
```
GET /api/v1/deezer/search?q=query
Authorization: Bearer <token>

Response: [List of Deezer tracks]
```

### 5.3 Download Endpoints

#### Add Download
```
POST /api/v1/downloads/add
Authorization: Bearer <token>
Content-Type: application/json

{
  "track_id": "spotify-id",
  "source": "spotify",
  "quality": "high",
  "priority": 5
}

Response (201 Created):
{
  "id": "download-uuid",
  "status": "pending",
  "position_in_queue": 3
}
```

#### Get Download Queue
```
GET /api/v1/downloads/queue
Authorization: Bearer <token>

Response (200 OK):
{
  "downloading": [
    {
      "id": "uuid",
      "track": { ...track data },
      "status": "downloading",
      "progress": 45,
      "speed": "1.2MB/s",
      "eta_seconds": 150
    }
  ],
  "pending": [
    { ...download data },
    { ...download data }
  ],
  "total_queue_size": 12
}
```

#### Cancel Download
```
POST /api/v1/downloads/{download_id}/cancel
Authorization: Bearer <token>

Response (200 OK):
{
  "success": true,
  "message": "Download cancelled"
}
```

#### Batch Add Downloads
```
POST /api/v1/downloads/batch-add
Authorization: Bearer <token>
Content-Type: application/json

{
  "track_ids": ["spotify-id-1", "spotify-id-2"],
  "source": "spotify",
  "quality": "high"
}

Response (201 Created):
{
  "batch_id": "batch-uuid",
  "added_count": 2,
  "failed_count": 0,
  "downloads": [...]
}
```

### 5.4 Watchlist Endpoints

#### Add to Watchlist
```
POST /api/v1/watchlist/add
Authorization: Bearer <token>
Content-Type: application/json

{
  "source": "spotify",
  "source_id": "artist-id",
  "type": "artist",
  "auto_download": true
}

Response (201 Created):
{
  "id": "watchlist-uuid",
  "source": "spotify",
  "source_name": "The Weeknd",
  "auto_download": true
}
```

#### Get Watchlist
```
GET /api/v1/watchlist/list
Authorization: Bearer <token>

Response (200 OK):
{
  "items": [
    {
      "id": "uuid",
      "source": "spotify",
      "source_name": "The Weeknd",
      "type": "artist",
      "last_checked": "2025-11-27T12:00:00Z",
      "new_items_count": 3
    }
  ]
}
```

#### Check Watchlist Now
```
POST /api/v1/watchlist/{watch_id}/check
Authorization: Bearer <token>

Response (200 OK):
{
  "new_items": [
    { ...track data },
    { ...track data }
  ],
  "count": 2,
  "added_to_queue": 2
}
```

---

## 6. SCHEMATY BAZY DANYCH

### 6.1 PostgreSQL Schema

```sql
-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  username VARCHAR(50) UNIQUE NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  is_active BOOLEAN DEFAULT true,
  preferences JSONB DEFAULT '{"theme":"dark"}',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_email (email),
  INDEX idx_username (username)
);

-- Service credentials (encrypted)
CREATE TABLE service_credentials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  service VARCHAR(20) NOT NULL,
  encrypted_token TEXT NOT NULL,
  token_expires_at TIMESTAMP,
  refresh_token TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, service),
  INDEX idx_user_id (user_id)
);

-- Tracks (unified metadata)
CREATE TABLE tracks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(500) NOT NULL,
  artist VARCHAR(500) NOT NULL,
  album VARCHAR(500),
  duration_ms INTEGER,
  isrc VARCHAR(20) UNIQUE,
  spotify_id VARCHAR(100) UNIQUE,
  youtube_id VARCHAR(100) UNIQUE,
  deezer_id VARCHAR(100) UNIQUE,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_title (title),
  INDEX idx_artist (artist),
  INDEX idx_isrc (isrc)
);

-- Downloads
CREATE TABLE downloads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  track_id UUID NOT NULL REFERENCES tracks(id),
  source VARCHAR(20) NOT NULL,
  status VARCHAR(20) DEFAULT 'pending',
  progress INTEGER DEFAULT 0,
  file_path VARCHAR(500),
  file_size INTEGER DEFAULT 0,
  priority INTEGER DEFAULT 5,
  error_message VARCHAR(1000),
  retry_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  INDEX idx_user_status (user_id, status),
  INDEX idx_status (status)
);

-- Watchlist
CREATE TABLE watchlist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  watch_type VARCHAR(20) NOT NULL,
  source VARCHAR(20) NOT NULL,
  source_id VARCHAR(100) NOT NULL,
  source_name VARCHAR(255) NOT NULL,
  auto_download BOOLEAN DEFAULT false,
  check_interval_hours INTEGER DEFAULT 24,
  last_checked_at TIMESTAMP,
  new_items_count INTEGER DEFAULT 0,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, source_id, source),
  INDEX idx_user_id (user_id)
);

-- Download history
CREATE TABLE download_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  track_id UUID REFERENCES tracks(id),
  source VARCHAR(20),
  quality VARCHAR(20),
  file_size INTEGER,
  downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_date (user_id, downloaded_at DESC)
);
```

### 6.2 Indexes for Performance

```sql
-- Performance indexes
CREATE INDEX idx_downloads_pending 
  ON downloads(user_id, status) 
  WHERE status IN ('pending', 'downloading');

CREATE INDEX idx_tracks_spotify_id ON tracks(spotify_id);
CREATE INDEX idx_tracks_youtube_id ON tracks(youtube_id);
CREATE INDEX idx_tracks_deezer_id ON tracks(deezer_id);

CREATE INDEX idx_watchlist_user_type 
  ON watchlist(user_id, watch_type);
```

---

## 7. WEBSOCKET EVENTS

### 7.1 Server → Client Events

```typescript
// Download progress
socket.on('download:progress', (data) => {
  {
    download_id: string
    progress: number          // 0-100
    speed: string             // "1.2MB/s"
    eta_seconds: number
    bytes_transferred: number
  }
})

// Download completed
socket.on('download:completed', (data) => {
  {
    download_id: string
    track: Track
    file_path: string
    file_size: number
  }
})

// Download error
socket.on('download:error', (data) => {
  {
    download_id: string
    error_message: string
    retry_possible: boolean
  }
})

// Queue updated
socket.on('queue:updated', (data) => {
  {
    queue_size: number
    position_in_queue: number
  }
})

// Watchlist update notification
socket.on('watchlist:update', (data) => {
  {
    watch_id: string
    source: string
    new_items_count: number
    items: Track[]
  }
})

// New watchlist item
socket.on('watchlist:new-item', (data) => {
  {
    watch_id: string
    track: Track
    added_to_queue: boolean
  }
})
```

### 7.2 Client → Server Events

```typescript
// Subscribe to download updates
socket.emit('subscribe:download', {
  download_id: string
})

// Unsubscribe from download
socket.emit('unsubscribe:download', {
  download_id: string
})

// Subscribe to watchlist updates
socket.emit('subscribe:watchlist', {
  watch_id: string
})

// Ping (keep-alive)
socket.emit('ping', {})
```

---

## 8. AUTHENTICATION FLOW

### 8.1 JWT Flow

```
1. USER registers
   ↓
2. Password hashed (bcrypt)
3. User stored in database
   ↓
4. USER logs in (email + password)
   ↓
5. Password verified
6. JWT tokens generated:
   - access_token (15 minutes)
   - refresh_token (7 days)
   ↓
7. Tokens returned to frontend
8. Access token stored (localStorage or cookie)
9. Refresh token stored (secure httpOnly cookie)
   ↓
10. USER makes API request
    ↓
11. Access token sent in Authorization header
12. Backend validates token
13. Request proceeds
    ↓
14. If token expired:
    → Send refresh_token
    → Get new access_token
    → Retry original request
```

### 8.2 OAuth2 (Spotify/YouTube)

```
1. User clicks "Connect Spotify"
   ↓
2. Frontend redirects to Spotify OAuth endpoint
3. User authorizes in Spotify
   ↓
4. Spotify redirects back with code
5. Backend exchanges code for access_token
6. Access token encrypted and stored in database
   ↓
7. User can now search/download from Spotify
   ↓
8. On token expiry:
   → Use refresh_token to get new token
   → Store in database
   → User never needs to re-auth
```

### 8.3 API Keys (YouTube/Deezer)

```
1. User goes to Settings panel
   ↓
2. Pastes API key in text field
   ↓
3. Frontend validates format
4. Sends to backend: POST /api/v1/settings/api-keys
   ↓
5. Backend validates with API (test call)
6. If valid: encrypts and stores
7. If invalid: returns error
   ↓
8. User can now use that service
```

---

## 9. ERROR HANDLING

### 9.1 HTTP Status Codes

```
200 OK               - Success
201 Created          - Resource created
400 Bad Request      - Invalid input
401 Unauthorized     - Missing/invalid token
403 Forbidden        - Insufficient permissions
404 Not Found        - Resource not found
409 Conflict         - Resource already exists
429 Too Many Requests - Rate limit exceeded
500 Internal Server  - Server error
503 Service Unavail  - External service down
```

### 9.2 Error Response Format

```json
{
  "error": true,
  "code": "INVALID_INPUT",
  "message": "User-friendly error message",
  "details": {
    "field": "email",
    "reason": "already_exists"
  },
  "request_id": "req-123-456",
  "timestamp": "2025-11-27T12:00:00Z"
}
```

### 9.3 Common Errors

```
INVALID_CREDENTIALS
├─ message: "Email or password is incorrect"
└─ status: 401

TRACK_NOT_FOUND
├─ message: "Track not available on this platform"
└─ status: 404

QUOTA_EXCEEDED
├─ message: "Storage quota exceeded"
└─ status: 429

SERVICE_UNAVAILABLE
├─ message: "Spotify API is temporarily unavailable"
└─ status: 503

AUTH_TOKEN_EXPIRED
├─ message: "Session expired. Please login again"
└─ status: 401
```

---

## 10. DEVELOPMENT SETUP

### 10.1 Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Frontend (in separate terminal)
cd frontend
npm install
npm run dev

# Database (if not using Docker)
psql -U postgres
CREATE DATABASE spotizerr;

# Redis (if not using Docker)
redis-server
```

### 10.2 Docker Development

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Access containers
docker-compose exec backend bash
docker-compose exec frontend sh

# Stop services
docker-compose down

# Reset database
docker-compose down -v
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

### 10.3 Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new column"

# Review migration file (backend/alembic/versions/)

# Apply migration
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Check migration status
alembic current
alembic history
```

### 10.4 Testing

```bash
# Backend tests
cd backend
pytest tests/

# With coverage
pytest --cov=app tests/

# Specific test file
pytest tests/test_auth.py

# Frontend tests
cd frontend
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage
```

---

## 11. TESTING STRATEGY

### 11.1 Backend Testing

```python
# tests/test_auth.py
def test_user_registration():
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123"
    })
    assert response.status_code == 201
    assert "id" in response.json()

def test_user_login():
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

# tests/test_download.py
def test_add_download(auth_headers):
    response = client.post(
        "/api/v1/downloads/add",
        json={"track_id": "123", "source": "spotify", "quality": "high"},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"

# tests/test_search.py
def test_unified_search(auth_headers):
    response = client.get(
        "/api/v1/search?q=test&sources=spotify,youtube",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert "results" in response.json()
```

### 11.2 Frontend Testing

```typescript
// src/components/__tests__/SearchBar.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import SearchBar from '../SearchBar'

describe('SearchBar', () => {
  it('renders search input', () => {
    render(<SearchBar />)
    const input = screen.getByRole('textbox')
    expect(input).toBeInTheDocument()
  })

  it('calls onSearch when user types and presses Enter', async () => {
    const onSearch = jest.fn()
    render(<SearchBar onSearch={onSearch} />)
    const input = screen.getByRole('textbox')
    
    fireEvent.change(input, { target: { value: 'blinding lights' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    
    expect(onSearch).toHaveBeenCalledWith('blinding lights')
  })
})
```

---

## 12. DEPLOYMENT GUIDE

### 12.1 Systemowe Wymagania

```
Production Server:
- CPU: 4 cores (minimum), 8+ recommended
- RAM: 8GB (minimum), 16GB+ recommended
- Storage: 100GB+ SSD
- Network: 10Mbps+ upload/download
- OS: Ubuntu 20.04 LTS or CentOS 7+
- Docker: 25.x
```

### 12.2 Docker Compose Production

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      LOG_LEVEL: INFO
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./downloads:/downloads
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    restart: always
    ports:
      - "80:3000"
      - "443:3000"
    environment:
      VITE_API_URL: https://api.example.com
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:

networks:
  default:
    name: spotizerr-net
```

### 12.3 SSL/HTTPS

```bash
# Using Let's Encrypt + Nginx

# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --nginx -d api.example.com -d example.com

# Nginx config (frontend/nginx.conf)
server {
    listen 443 ssl;
    server_name api.example.com;
    
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    
    location / {
        proxy_pass http://backend:8000;
    }
}
```

### 12.4 Backup Strategy

```bash
# Daily PostgreSQL backup
0 2 * * * docker-compose exec -T postgres pg_dump -U user spotizerr > /backups/spotizerr_$(date +\%Y\%m\%d).sql

# Upload to cloud
0 3 * * * rclone sync /backups gs://my-bucket/backups/spotizerr/

# Retention: Keep 30 days
find /backups -type f -mtime +30 -delete
```

---

## 13. BEST PRACTICES

### 13.1 Code Quality

```
Backend:
✓ Use type hints (Python 3.12+)
✓ Follow PEP 8 (Black formatter)
✓ Async/await for all I/O
✓ Context managers for resources
✓ Comprehensive error handling
✓ Logging at all levels
✓ Unit tests (minimum 80% coverage)
✓ Docstrings for all functions

Frontend:
✓ TypeScript strict mode
✓ ESLint + Prettier
✓ Functional components
✓ Custom hooks for logic
✓ Error boundaries
✓ Loading/skeleton states
✓ Accessibility (WCAG 2.1)
✓ Component tests
✓ E2E tests for critical flows
```

### 13.2 Performance

```
Backend:
- Use database indexes properly
- Cache frequently accessed data (Redis)
- Batch operations when possible
- Async workers for heavy tasks
- Connection pooling
- Rate limiting
- Gzip compression

Frontend:
- Code splitting (lazy loading)
- Image optimization
- Bundle analysis
- Virtual scrolling (large lists)
- Debounce API calls
- Service worker caching
- Minimize re-renders
```

### 13.3 Security

```
- HTTPS everywhere (SSL/TLS)
- Validate all inputs
- Sanitize outputs
- Use CORS properly
- Rate limiting
- JWT secret rotation
- Encrypt sensitive data
- SQL injection prevention
- XSS protection
- CSRF tokens (if forms)
- Security headers
- Dependency scanning (Snyk)
```

### 13.4 Monitoring & Logging

```
Backend:
- Structured logging (JSON)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Request/response logging
- Performance metrics
- Error tracking (Sentry)
- Uptime monitoring

Frontend:
- Error boundary logging
- User session tracking
- API error monitoring
- Performance metrics (Core Web Vitals)
- User behavior analytics
```

---

## 14. TROUBLESHOOTING

### 14.1 Common Issues

#### Docker containers won't start

```bash
# Check logs
docker-compose logs

# Rebuild images
docker-compose down
docker-compose build --no-cache
docker-compose up

# Check disk space
docker system df

# Clean up
docker system prune -a
```

#### Database connection error

```bash
# Check database is running
docker-compose ps

# Check connection string in .env
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Reset database
docker-compose down -v
docker-compose up
docker-compose exec backend alembic upgrade head
```

#### API returns 401 Unauthorized

```
- Token expired: refresh token
- Invalid token format: check Authorization header
- Token not sent: verify axios interceptor
- JWT_SECRET_KEY mismatch: check backend .env
```

#### Downloads stuck in "downloading"

```bash
# Check backend logs
docker-compose logs backend | grep download

# Check FFmpeg installed
docker-compose exec backend ffmpeg -version

# Check disk space
docker-compose exec backend df -h

# Restart download manager
docker-compose restart backend
```

#### WebSocket connection fails

```bash
# Check frontend WS_URL
console.log(import.meta.env.VITE_WS_URL)

# Check backend WebSocket port
docker-compose ps | grep backend

# Check firewall
sudo ufw allow 8000

# Check browser console for errors
```

### 14.2 Performance Issues

```
Slow search:
- Add database index: CREATE INDEX idx_title ON tracks(title)
- Enable Redis caching
- Implement rate limiting

High memory usage:
- Check for memory leaks in download manager
- Limit concurrent downloads (MAX_PARALLEL=3)
- Monitor FFmpeg processes

High CPU usage:
- Reduce concurrent operations
- Optimize FFmpeg settings
- Check for infinite loops
```

### 14.3 Getting Help

```
Resources:
- GitHub Issues: https://github.com/yourusername/spotizerr-3.0/issues
- FastAPI Docs: https://fastapi.tiangolo.com
- React Docs: https://react.dev
- PostgreSQL Docs: https://www.postgresql.org/docs
- Docker Docs: https://docs.docker.com

Discord Community:
- Join our Discord server for real-time help
- Link: [your-discord-link]

Email Support:
- support@spotizerr.dev
```

---

## 📞 SUPPORT

**Dokumentacja:** https://docs.spotizerr.dev  
**Issues:** https://github.com/yourusername/spotizerr-3.0/issues  
**Discussions:** https://github.com/yourusername/spotizerr-3.0/discussions  
**Discord:** [Your Discord Link]  

---

**Dokument zaktualizowany:** Listopad 2025  
**Wersja:** 1.0  
**Status:** Gotowy do wdrożenia
