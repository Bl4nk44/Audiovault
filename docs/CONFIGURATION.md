# Configuration Guide

Complete reference for Audiovault configuration options. All configuration is done through environment variables in the `.env` file.

## Environment Variables

### Admin & Security

```bash
# Admin user credentials (required on first run)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=SecurePassword123!  # Change this!

# Secret key for JWT tokens
JWT_SECRET_KEY=your-super-secret-key-here  # Generate: openssl rand -hex 32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Security headers
ALLOWED_HOSTS=localhost,127.0.0.1,audiovault.example.com
BACKEND_CORS_ORIGINS=["http://localhost:2137", "https://audiovault.example.com"]
```

### Database & Storage

```bash
# PostgreSQL (required — no SQLite in production)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/audiovault
# Redis
REDIS_URL=redis://redis:6379/0

# Storage
DOWNLOAD_DIR=/downloads
MAX_PARALLEL_DOWNLOADS=3
STORAGE_QUOTA_GB=500
```

### Integrations

```bash
# Spotify (optional — built-in anonymous fallback works out of the box)
# See SPOTIFY_INTEGRATION.md for full details
SPOTIFY_CLIENT_ID=your_client_id          # Override embedded credentials
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_SP_DC=your_sp_dc_cookie_value     # Free account cookie (~1yr TTL)
SPOTIFY_HOST_PROXY=http://host.docker.internal:8765  # Host proxy for embed scraping

# Last.fm — see LASTFM_INTEGRATION.md
LASTFM_API_KEY=your_lastfm_api_key
LASTFM_API_SECRET=your_lastfm_api_secret

# Genius (lyrics)
GENIUS_API_TOKEN=your_genius_api_token
```

### Other

```bash
LOG_LEVEL=INFO   # DEBUG | INFO | WARNING | ERROR | CRITICAL
TIMEZONE=UTC
```

See detailed guides for:
- [Spotify Integration](SPOTIFY_INTEGRATION.md) (zero-config, no keys needed)
- [Last.fm Integration](LASTFM_INTEGRATION.md)
- [Platform Support & Fallbacks](PLATFORM_SUPPORT.md)
- [Automation & Watchlists](AUTOMATION.md)

## Docker Compose Setup

The canonical setup uses PostgreSQL 16 + Redis 8. SQLite is used only in automated tests, not in production.
The `docker-compose.yml` in the repo root is the reference configuration; snippets below show the most common customisations.

### Standard Setup (from repo)

```bash
cp .env.example .env
# Edit .env: set ADMIN_PASSWORD and JWT_SECRET_KEY at minimum
docker compose up -d --build
```

The `docker-compose.yml` wires up:
- `db` — PostgreSQL 16 (`postgres:16-alpine`)
- `redis` — Redis 8 (`redis:8-alpine`)
- `backend` — FastAPI on port `8000`; Spotify OAuth callback on port `9900`
- `frontend` — Nginx on port `2137` (internal `8080`)

### Production Overrides (docker-compose.override.yml)

Use an override file instead of editing `docker-compose.yml` directly:

```yaml
services:
  backend:
    environment:
      - ALLOWED_HOSTS=audiovault.example.com
      - BACKEND_CORS_ORIGINS=https://audiovault.example.com
      - LOG_LEVEL=WARNING
    mem_limit: 4g

  db:
    environment:
      - POSTGRES_PASSWORD=strong_password_here
    ports: []  # Don't expose DB port publicly
```

## Network & Remote Access

For reverse proxy configurations (Nginx, Traefik, Caddy, etc.) see the [Reverse Proxy Guide](REVERSE_PROXY.md).

> **Remember**: When exposing through a reverse proxy, update `ALLOWED_HOSTS` and `BACKEND_CORS_ORIGINS` to include your domain.
