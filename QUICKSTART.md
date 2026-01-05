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

# Edit with your favorite editor (or just skip - defaults work fine)
nano .env
```

## Step 3: Start

```bash
# Build and start all containers
docker compose up -d --build

# Wait ~30 seconds for startup...

# Check status
docker compose ps
```

## Step 4: Access

1. **Web Interface**: http://localhost:3000
2. **API Docs**: http://localhost:8000/docs
3. **Email**: `admin@example.com`
4. **Password**: Check with: `docker compose logs backend | grep "password"`

## 🎵 First Download

1. Login to http://localhost:3000
2. Go to **Services** section
3. Add your Spotify/YouTube/other service (see [Configuration Guide](https://github.com/Bl4nk44/Audiovault/wiki/Configuration))
4. Go to **Download**
5. Search for a track and download!

## 📱 Stream to Phone

1. In **Settings**, enable Subsonic API
2. Download **Symfonium**, **Amperfy**, or **DSub** (Subsonic clients)
3. Add server: `http://YOUR_IP:8000`
4. Stream your music!

## 🆘 Troubleshooting

**Can't access?**
```bash
# Check logs
docker compose logs backend

# Restart
docker compose restart
```

**Password issues?**
```bash
# Get generated password
docker compose logs backend | grep "Initial"
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

---

That's it! You now have Audiovault running. 🎉

For detailed guides, see the [Wiki](https://github.com/Bl4nk44/Audiovault/wiki).
