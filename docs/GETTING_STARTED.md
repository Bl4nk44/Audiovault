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
ADMIN_USERNAME=admin
ADMIN_PASSWORD=SecurePassword123!  # Change this!
```

> **Note**: Spotify integration natively uses anonymous scraping and requires no configuration. For Last.fm or Genius API setup, see the specific documentation files.

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

### 6. Admin Login

Once the containers are up, log in at http://localhost:2137 using the credentials set in `.env`.
> **Note:** For security reasons, generated passwords are **not printed to the logs**. Always set a strong password.

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

Find what's using the port and change ports in `docker-compose.yml` if necessary.

### High Memory Usage

Increase available memory in `docker-compose.yml`:
```yaml
services:
  backend:
    mem_limit: 4g
```

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
