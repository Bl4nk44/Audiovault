# Configuration Guide 🔧

Complete reference for all Audiovault configuration options.

## Environment Variables

All configuration is done through environment variables in the `.env` file.

### Admin & Security

```bash
# Admin user credentials
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=SecurePassword123!  # Set strong password!

# Secret key for JWT tokens (generates if not set)
SECRET_KEY=your-super-secret-key-here

# Security headers
ALLOWED_HOSTS=localhost,127.0.0.1,audiovault.example.com
BACKEND_CORS_ORIGINS=http://localhost:3000,https://audiovault.example.com
```

### Database Configuration

```bash
# SQLite (default, simplest setup)
DATABASE_URL=sqlite:///./audiovault.db

# PostgreSQL (recommended for production)
DATABASE_URL=postgresql://audiovault:password@postgres:5432/audiovault

# PostgreSQL with asyncpg (faster)
DATABASE_URL=postgresql+asyncpg://audiovault:password@postgres:5432/audiovault
```

### Storage Configuration

```bash
# Music library storage path
MUSIC_LIBRARY_PATH=/path/to/music/library

# Maximum file size for uploads (in MB)
MAX_UPLOAD_SIZE=500

# Concurrent downloads allowed
CONCURRENT_DOWNLOADS=3
```

### ![Spotify](https://img.shields.io/badge/Spotify-1ED760?style=flat-square&logo=spotify&logoColor=white) Integration

```bash
# Get credentials: https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_CACHE_EXPIRE_MINUTES=60
```

### ![Genius](https://img.shields.io/badge/Genius-ffff00?style=flat-square&logo=genius&logoColor=black) Lyrics

```bash
# Get API token: https://genius.com/api-clients
# Create an "API Client" and use the "Client Access Token" (NOT Client ID/Secret)
GENIUS_API_TOKEN=your_genius_access_token_here
```

### ![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=flat-square&logo=youtube&logoColor=white) Integration

```bash
# Get API key: https://console.cloud.google.com/
YOUTUBE_API_KEY=your_api_key

# Use Invidious proxy to bypass regional restrictions
YOUTUBE_PROXY_ENABLED=true
YOUTUBE_PROXY_URL=https://invidious.example.com

# Preferred video quality (22=720p, 18=360p)
YTDLP_FORMAT=22
```

### Scheduler & Automation

```bash
# Auto-sync check interval (minutes)
AUTO_SYNC_INTERVAL=60

# Enable background tasks
ENABLE_SCHEDULER=true

# Remove deleted tracks from local library
AUTO_PURGE_ENABLED=true
AUTO_PURGE_DAYS=7
```

### API & Subsonic Configuration

```bash
# Enable Subsonic API
ENABLE_SUBSONIC_API=true
SUBSONIC_API_VERSION=1.16.1

# Legacy authentication (for older Subsonic clients)
# NOTE: Even with this enabled, you MUST enable "Legacy Auth" / "Use plaintext password"
# in your client app settings (Amperfy, Symfonium, etc.)
SUBSONIC_LEGACY_AUTH=true
```

### Advanced Configuration

```bash
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Number of worker processes
WORKERS=4

# Cache configuration
REDIS_URL=redis://redis:6379/0
USE_REDIS=true
```

## Docker Compose Configuration

### Basic Setup (SQLite)

```yaml
version: "3.8"

services:
  backend:
    image: audiovault:latest
    ports:
      - "8000:8000"
    volumes:
      - ./music_library:/app/music_library
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///./data/audiovault.db
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=YourPassword123!
    restart: unless-stopped

  frontend:
    image: audiovault-frontend:latest
    ports:
      - "2137:80"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped
```

### Production Setup (PostgreSQL + Redis)

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: audiovault
      POSTGRES_USER: audiovault
      POSTGRES_PASSWORD: SecurePassword123!
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7
    command: redis-server --requirepass SecurePassword123!
    volumes:
      - redis_data:/data
    restart: unless-stopped

  backend:
    image: audiovault:latest
    ports:
      - "8000:8000"
    volumes:
      - ./music_library:/app/music_library
    environment:
      - DATABASE_URL=postgresql+asyncpg://audiovault:SecurePassword123!@postgres:5432/audiovault
      - REDIS_URL=redis://:SecurePassword123!@redis:6379/0
      - USE_REDIS=true
      - WORKERS=4
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  frontend:
    image: audiovault-frontend:latest
    ports:
      - "2137:80"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## Network & Remote Access

### Using Tailscale (Recommended)

```bash
# Install Tailscale on host
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate
sudo tailscale up

# Get your Tailscale IP
tailscale ip -4

# Access from anywhere: http://[your-tailscale-ip]:2137
```

### Using Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name audiovault.example.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/audiovault.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/audiovault.example.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Best Practices

✅ **Do**:

- **Set a strong `ADMIN_PASSWORD` in `.env` before first start** (generated passwords are not logged)
- Use PostgreSQL for production
- Enable Redis for caching
- Use HTTPS with valid certificate
- Regularly backup your database
- Keep Docker images updated

❌ **Don't**:

- Commit `.env` file to version control
- Use default/weak passwords
- Expose backend directly to internet
- Skip HTTPS for remote access
- Run with `DEBUG=true` in production

## Troubleshooting Configuration

### "Invalid configuration" error

```bash
# Check syntax
docker compose config

# View logs
docker compose logs backend
```

### Environment variable not applied

```bash
# Recreate containers
docker compose down
docker compose up -d --build
```

---

For more configuration examples, see [Getting Started](WIKI_GETTING_STARTED.md)
