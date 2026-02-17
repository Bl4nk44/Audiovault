# 🔧 Technical Context: Stack & Configuration

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: SQLite (default) / PostgreSQL (supported)
- **Cache**: Redis (optional)
- **ORM**: SQLAlchemy 2.x (Async)
- **Scheduler**: APScheduler (background tasks)
- **Download Engine**: yt-dlp
- **Audio Processing**: mutagen (ID3 tags)
- **Authentication**: JWT tokens
- **WebSocket**: For real-time progress updates

### Frontend
- **Framework**: React 18+ with TypeScript
- **Styling**: TailwindCSS v4
- **Animations**: Framer Motion
- **State Management**: React Query + Context API
- **Build Tool**: Vite
- **HTTP Client**: Axios
- **i18n**: react-i18next

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Reverse Proxy**: Nginx/Traefik compatible
- **CI/CD**: GitHub Actions
- **Testing**: pytest (backend), Jest/React Testing Library (frontend)
- **Code Quality**: Semgrep, SonarQube, Snyk, Trivy
- **Linting**: Ruff (Python), ESLint (TypeScript)
- **Formatting**: Black (Python), Prettier (JS/TS)

## Architecture Overview

### High-Level Architecture
```
Frontend (React) <--> FastAPI Backend <--> Database (SQLite/PostgreSQL)
                          |
                          ├─> Redis (Caching)
                          ├─> yt-dlp (Downloads)
                          ├─> APScheduler (Jobs)
                          └─> External APIs (Spotify, YouTube, etc.)
```

### Directory Structure
```
Audiovault/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes
│   │   ├── core/         # Config, security, utils
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   └── main.py       # Application entry
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API clients
│   │   ├── hooks/        # Custom hooks
│   │   ├── utils/        # Utilities
│   │   └── App.tsx       # Root component
│   └── package.json
├── docker/               # Dockerfile templates
├── docs/                 # Documentation
├── .github/workflows/    # CI/CD
└── docker-compose.yml    # Deployment config
```

## Key Configuration Files

### Backend
- **`backend/app/core/config.py`**: Environment variables, settings
- **`backend/requirements.txt`**: Python dependencies
- **`backend/pyproject.toml`**: Project metadata, tool configs
- **`.env`**: Secrets (API keys, database URLs)

### Frontend
- **`frontend/package.json`**: Node dependencies, scripts
- **`frontend/vite.config.ts`**: Vite configuration
- **`frontend/tailwind.config.js`**: TailwindCSS setup
- **`frontend/tsconfig.json`**: TypeScript config

### Infrastructure
- **`docker-compose.yml`**: Multi-container orchestration
- **`docker/Dockerfile.backend`**: Backend container
- **`docker/Dockerfile.frontend`**: Frontend container
- **`.github/workflows/ci.yml`**: CI/CD pipeline

## Environment Variables

### Required
```bash
# Database
DATABASE_URL=sqlite:///./audiovault.db

# Security
SECRET_KEY=<random-secret-key>
ADMIN_PASSWORD=<admin-password>

# CORS
BACKEND_CORS_ORIGINS=http://localhost:2137

# Streaming Platform APIs
SPOTIFY_CLIENT_ID=<spotify-client-id>
SPOTIFY_CLIENT_SECRET=<spotify-client-secret>
```

### Optional
```bash
# Last.fm
LASTFM_API_KEY=<lastfm-key>
LASTFM_API_SECRET=<lastfm-secret>

# Redis
REDIS_URL=redis://redis:6379/0

# Reverse Proxy
ALLOWED_HOSTS=audiovault.example.com,localhost
```

## API Standards

### RESTful Conventions
- **GET** `/api/playlists` - List resources
- **GET** `/api/playlists/{id}` - Get single resource
- **POST** `/api/playlists` - Create resource
- **PUT** `/api/playlists/{id}` - Update resource
- **DELETE** `/api/playlists/{id}` - Delete resource

### Response Format
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed",
  "timestamp": "2026-02-17T13:52:00Z"
}
```

### Error Format
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid playlist ID",
    "details": { ... }
  },
  "timestamp": "2026-02-17T13:52:00Z"
}
```

## Development Workflow

### Local Development
1. Clone repository
2. Copy `.env.example` to `.env`
3. Run `docker compose up -d --build`
4. Backend: http://localhost:8000
5. Frontend: http://localhost:2137

### Testing
```bash
# Backend
cd backend
pytest tests/

# Frontend
cd frontend
npm test
```

### Code Quality
```bash
# Linting
ruff check backend/
npm run lint

# Formatting
black backend/
npm run format

# Security
semgrep --config=.semgrep.yml
trivy fs .
```

## Deployment

### Docker (Recommended)
```bash
docker compose up -d
```

### Reverse Proxy (Nginx Example)
```nginx
server {
    listen 80;
    server_name audiovault.example.com;

    location / {
        proxy_pass http://localhost:2137;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Performance Considerations

- **Database**: Index on `playlist_id`, `service_name`, `download_status`
- **Caching**: Redis for frequent queries (playlist metadata)
- **Downloads**: Rate limiting to avoid IP bans
- **WebSocket**: Compress messages for large progress updates
- **Frontend**: Code splitting, lazy loading, image optimization

## Security

- **Authentication**: JWT with refresh tokens
- **CORS**: Strict origin whitelist
- **Input Validation**: Pydantic schemas
- **SQL Injection**: SQLAlchemy ORM (parameterized queries)
- **Secrets**: Never commit to repo, use .env
- **Dependencies**: Regular updates, vulnerability scanning
