# 🚀 Quick Start - 5 Minutes

Get Audiovault running in minutes!

## Step 1: Prerequisites

```bash
# Check Docker is installed
docker --version
docker compose --version
```

**Don't have Docker?** [Install Docker Desktop](https://www.docker.com/products/docker-desktop)

## Step 2: Clone & Configure

```bash
# Clone the repository
git clone https://github.com/Bl4nk44/Audiovault.git
cd Audiovault

# Create .env file
cp .env.example .env

# REQUIRED: Set your admin password in .env
# nano .env -> ADMIN_PASSWORD=your_secure_password
```

## Step 3: Start

```bash
# Pull the latest images and start all containers
docker compose pull
docker compose up -d

# Wait ~30 seconds for startup...

# Check status
docker compose ps
```

## Step 4: Access

1. **Web Interface**: http://localhost:2137
2. **API Docs**: http://localhost:8000/docs
3. **Username**: `admin`
4. **Password**: The one you set in `.env` (Default: `admin` if not changed)

## Step 5: Updating

When a new version is released, pull the latest images and restart:

```bash
docker compose pull
docker compose up -d
```

Migrations run automatically. No `git pull` needed — unless you want to update `.env` with new config options.

## 🎵 First Download

1. Login to http://localhost:2137
2. Go to **Services** section
3. Add your ![Spotify](https://img.shields.io/badge/Spotify-1ED760?style=flat-square&logo=spotify&logoColor=white)/![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=flat-square&logo=youtube&logoColor=white)/other service (see [Configuration Guide](https://github.com/Bl4nk44/Audiovault/wiki/Configuration))
4. Go to **Download**
5. Search for a track and download!

## 📱 Stream to Phone

1.  In **Settings**, enable Subsonic API
2.  Download **Sonixd** (Desktop/Linux), **Symfonium** (Android), or **Amperfy** (iOS)
3.  Add server: `http://YOUR_IP:2137`
    - If connecting locally: `http://localhost:2137`
4.  **IMPORTANT**: Enable "Legacy Auth" / "Use plaintext password" in app settings
5.  Stream your music!

## 🎵 Audio Quality

Configure in **Settings → General → Audio Quality**:

- **Low**: 128kbps MP3
- **Normal**: 192kbps MP3
- **High**: 320kbps MP3 (default)
- **Lossless**: FLAC format

## 🎆 Troubleshooting

**Can't access?**

```bash
# Check logs
docker compose logs backend

# Restart
docker compose restart
```

**Password issues?**

If you forgot your password or it's not working, ensure `ADMIN_PASSWORD` is correctly set in your `.env` and restart:
```bash
docker compose up -d --force-recreate backend
```

**Free up space?**

```bash
# Stop and remove everything
docker compose down

# Restart fresh
docker compose up -d
```

## 📚 Next Steps

- **[Full Setup Guide](https://github.com/Bl4nk44/Audiovault/wiki/Getting-Started)**
- **[Configuration Options](https://github.com/Bl4nk44/Audiovault/wiki/Configuration)**
- **[FAQ & Support](SUPPORT.md)**
- **[Contributing](CONTRIBUTING.md)**

## 🛠️ Developer Setup

To build images locally from source:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

This uses `docker-compose.dev.yml` which adds `build:` overrides and backend hot-reload.

---

That's it! You now have Audiovault running. 🎉

For detailed guides, see the [Wiki](https://github.com/Bl4nk44/Audiovault/wiki).
