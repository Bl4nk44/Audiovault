# Configuration Guide 🔧

Complete reference for Audiovault configuration options. All basic configuration is done through environment variables in the `.env` file.

## Environment Variables

### Admin & Security

```bash
# Admin user credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=SecurePassword123!  # Set strong password!

# Secret key for JWT tokens (generates if not set)
JWT_SECRET_KEY=your-super-secret-key-here

# Security headers
ALLOWED_HOSTS=localhost,127.0.0.1,audiovault.example.com
BACKEND_CORS_ORIGINS=["http://localhost:2137", "https://audiovault.example.com"]
```

### Database & Storage Configuration

```bash
# PostgreSQL (recommended for production)
DATABASE_URL=postgresql://user:password@localhost:5432/audiovault
# Redis caching
REDIS_URL=redis://localhost:6379/0

# Storage limits
DOWNLOAD_DIR=/downloads
MAX_PARALLEL_DOWNLOADS=3
STORAGE_QUOTA_GB=500
```

### Integrations

See detailed guides for:
- [Spotify Integration](SPOTIFY_INTEGRATION.md) (Zero config, no keys needed)
- [Last.fm Integration](LASTFM_INTEGRATION.md)
- [Platform Support & Fallbacks](PLATFORM_SUPPORT.md)
- [Automation & Watchlists](AUTOMATION.md)

### Advanced Configuration

```bash
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
TIMEZONE=UTC
```

## Docker Compose Setup Examples

### Basic Setup (SQLite)

```yaml
version: "3.8"

services:
  backend:
    image: audiovault:latest
    ports:
      - "8000:8000"
    volumes:
      - ./downloads:/downloads
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
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7
    volumes:
      - redis_data:/data
    restart: unless-stopped

  backend:
    image: audiovault:latest
    ports:
      - "8000:8000"
    volumes:
      - ./downloads:/downloads
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/audiovault
      - REDIS_URL=redis://redis:6379/0
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

For reverse proxy configurations (Nginx, Traefik, Caddy, etc.), see the [Reverse Proxy Guide](REVERSE_PROXY.md).
