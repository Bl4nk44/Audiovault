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

# Proxy for provider media traffic (yt-dlp downloads + URL resolution) — optional
# Supported schemes: http, https, socks4, socks5, socks5h
# See the "Download Proxy" section below for details
DOWNLOAD_PROXY=http://privoxy:8118        # or socks5://host:1080

# Last.fm — see LASTFM_INTEGRATION.md
LASTFM_API_KEY=your_lastfm_api_key
LASTFM_API_SECRET=your_lastfm_api_secret

# ListenBrainz — see LISTENBRAINZ_INTEGRATION.md (no API key; per-user token).
# Override only for a self-hosted instance.
# LISTENBRAINZ_API_URL=https://api.listenbrainz.org

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
- [ListenBrainz Integration](LISTENBRAINZ_INTEGRATION.md)
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

## Download Proxy

Route all music fetching from providers through a proxy, while the rest of Audiovault connects directly. Useful when the media hosts are region-blocked, rate-limit your IP, or you simply want download traffic to leave through a specific tunnel (VPN container, Tor, Privoxy, etc.).

### What goes through the proxy

Everything yt-dlp does — the actual audio downloads **and** the URL/metadata resolution that precedes them (YouTube, SoundCloud, the generic provider, and on-the-fly stream URL resolution).

### What stays direct

- The web UI, REST API, and Subsonic streaming to your clients
- Metadata lookups against provider APIs (Spotify, Deezer, MusicBrainz, Last.fm, Genius)
- Database, Redis, and everything else inside the stack

### Setup

One variable in `.env`, then restart the backend:

```bash
DOWNLOAD_PROXY=http://privoxy:8118
```

```bash
docker compose up -d backend
```

Supported schemes (validated on startup — the backend refuses to boot with an unsupported value):

| Scheme | Example | Notes |
|--------|---------|-------|
| `http` / `https` | `http://privoxy:8118` | Standard HTTP(S) proxy |
| `socks4` | `socks4://10.0.0.1:1080` | |
| `socks5` | `socks5://user:pass@10.0.0.1:1080` | DNS resolved locally; credentials in the URL |
| `socks5h` | `socks5h://tor:9050` | DNS resolved by the proxy (e.g. Tor) |

Leave `DOWNLOAD_PROXY` unset (or empty) to keep direct connections — the default behavior.

> **Docker networking**: the proxy address is resolved from inside the backend container. A proxy running in another compose service is reachable by its service name (`http://privoxy:8118`); a proxy on the Docker host needs `http://host.docker.internal:PORT`.

### Verifying it works

Queue a download and watch your proxy's access log — the media host traffic should appear there. If the proxy is unreachable, downloads fail with a connection error in `docker compose logs backend`; they never silently fall back to a direct connection.

## Network & Remote Access

For reverse proxy configurations (Nginx, Traefik, Caddy, etc.) see the [Reverse Proxy Guide](REVERSE_PROXY.md).

> **Remember**: When exposing through a reverse proxy, update `ALLOWED_HOSTS` and `BACKEND_CORS_ORIGINS` to include your domain.
