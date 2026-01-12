# Getting Started with Audiovault 🎵

This guide will help you install and configure Audiovault for the first time.

## Prerequisites

### System Requirements

- **Operating System**: Windows, macOS, or Linux
- **CPU**: 2 vCPU cores minimum (more is better for faster encoding)
- **RAM**: 2 GB minimum (4 GB recommended)
- **Storage**: 2-3 GB for application + additional space for music library
- **Docker**: Version 20.10+ and Docker Compose 2.0+
- **Internet Connection**: Required for downloading from streaming services

### Check Your System

```bash
# Check Docker installation
docker --version
docker compose --version

# Check available disk space
df -h  # Linux/macOS
dir    # Windows

# Check RAM
free -h           # Linux
vm_stat           # macOS
SystemInfo        # Windows
```

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/Bl4nk44/Audiovault.git
cd Audiovault
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your preferred settings
nano .env
```

### 3. Essential Configuration

Edit `.env` and set these required variables:

```bash
# Admin access
FIRST_SUPERUSER_EMAIL=admin@example.com
FIRST_SUPERUSER_PASSWORD=SecurePassword123!  # Change this!

# Streaming service credentials (add as needed)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_secret
YOUTUBE_API_KEY=your_youtube_api_key
```

### 4. Start Audiovault

```bash
# Build and start containers in background
docker compose up -d --build

# Check if containers are running
docker compose ps

# View startup logs
docker compose logs -f backend
docker compose logs -f frontend
```

### 5. Access Audiovault

- **Web Interface**: http://localhost:2137
- **API Documentation**: http://localhost:8000/docs
- **API Redoc**: http://localhost:8000/redoc

### 6. Get Admin Password

If you didn't set `FIRST_SUPERUSER_PASSWORD`, check the logs:

```bash
docker compose logs backend | grep "password"
```

## First Login

1. Open http://localhost:2137 in your browser
2. Click "Login" and use:
   - **Email**: `admin@example.com`
   - **Password**: The one you set or generated
3. You'll see the setup wizard for service integrations

## Getting Streaming Service Credentials

### Spotify

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in or create an account
3. Create an "Application"
4. Accept terms and create the app
5. Copy `Client ID` and `Client Secret`
6. Add them to your `.env`:
   ```bash
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   ```
7. Restart backend: `docker compose restart backend`

### YouTube

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "YouTube Data API v3"
4. Create an API key (Credentials → Create Credentials → API Key)
5. Add to `.env`:
   ```bash
   YOUTUBE_API_KEY=your_api_key
   ```
6. Restart backend: `docker compose restart backend`

### Other Services

See [Configuration Guide](WIKI_CONFIGURATION.md) for detailed instructions for:

- Apple Music
- Deezer
- Tidal
- SoundCloud
- Amazon Music

## Common Setup Issues

### "Connection refused" or "Cannot reach backend"

```bash
# Check if backend is running
docker compose ps

# Check backend logs
docker compose logs backend | tail -20

# Restart all containers
docker compose restart
```

### "Port already in use"

```bash
# Find what's using the port (Linux/macOS)
lsof -i :3000    # Frontend
lsof -i :8000    # Backend

# Or change ports in docker-compose.yml
```

### "Permission denied" on music library

```bash
# Fix permissions
chmod 755 /path/to/music/library
```

### High Memory Usage

Increase available memory in `docker-compose.yml`:

```yaml
services:
  backend:
    mem_limit: 4g
```

## Next Steps

1. **[Configure Streaming Services](WIKI_CONFIGURATION.md)** - Add your favorite music sources
2. **[Learn Usage Basics](WIKI_USAGE.md)** - Download and manage music

## Useful Docker Commands

```bash
# View logs
docker compose logs backend
docker compose logs -f backend  # Follow in real-time

# Stop/Start containers
docker compose stop
docker compose start

# Restart containers
docker compose restart backend

# Update and restart
docker compose pull
docker compose up -d
```

## Getting Help

- **[FAQ & Troubleshooting](../SUPPORT.md)** - Common problems and solutions
- **[GitHub Discussions](https://github.com/Bl4nk44/Audiovault/discussions)** - Ask the community
- **[Report a Bug](https://github.com/Bl4nk44/Audiovault/issues/new?template=bug_report.md)** - Found an issue?

---

Congratulations! Audiovault is now running. 🌟

Next: [Configure Streaming Services](WIKI_CONFIGURATION.md)
