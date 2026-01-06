<div align="center">

# Audiovault

**Your Personal Music Sanctuary.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/Bl4nk44/Audiovault?logo=github)](https://github.com/Bl4nk44/Audiovault/releases)
[![GitHub Stars](https://img.shields.io/github/stars/Bl4nk44/Audiovault?logo=github)](https://github.com/Bl4nk44/Audiovault/stargazers)
[![Docker Pulls](https://img.shields.io/docker/pulls/bl4nk44/audiovault?logo=docker)](https://hub.docker.com/r/bl4nk404/audiovault)

🔗 **Quick Links**:
[📖 Wiki](https://github.com/Bl4nk44/Audiovault/wiki) •
[🐛 Issues](https://github.com/Bl4nk44/Audiovault/issues) •
[🎯 Pull Requests](https://github.com/Bl4nk44/Audiovault/pulls) •
[💬 Discussions](https://github.com/Bl4nk44/Audiovault/discussions) •
[🤝 Contributing](CONTRIBUTING.md)

</div>

---

Audiovault is a powerful, self-hosted application designed to import, manage, and download your music libraries from **any major streaming platform** directly to your local server. Built with performance, aesthetics, and reliability in mind.

![Audiovault Dashboard](https://i.imgur.com/93QfgYt.png)

## ✨ Features

### Extensive Platform Support

Import playlists, albums, and tracks from:

- **Spotify** - Playlists, albums, liked songs, recommendations
- **YouTube** - Playlists, mixes, videos, channels
- **Deezer** - Native search, artist profiles, playlists
- **SoundCloud** - Tracks, playlists, user libraries
- **Apple Music** - Playlists, library, recommendations
- **Tidal** - Playlists, favorites, discovery
- **Amazon Music** - Playlists, library, recommendations

### Robust Fallback System

Never miss a track. If a download fails (e.g., due to geo-restrictions or broken links), Audiovault automatically:

1. Tries alternative search queries (Official Audio, Lyrics Video)
2. Searches cross-platform (e.g., falls back to SoundCloud if YouTube fails)
3. Uses proxies (Invidious) to bypass region locks

### Watchlist & Automation

- **Auto-Sync**: Background scheduler checks for new tracks every 60 minutes
- **Safe Purge**: Automatically removes local tracks that were deleted from remote playlists (with specific user approval & dry-run safety)
- **Smart De-duplication**: Prevents duplicate downloads by checking both ID3 tags and internal database history
- **Universal Search**: Unified search bar for all supported providers

### Personal Streaming Server

Turn Audiovault into your personal Spotify.

- **Subsonic API Support**: Native implementation of the Subsonic API (v1.16.1)
- **Mobile Apps**: Stream your library to your phone using **Symfonium**, **Amperfy**, **DSub**, or any Subsonic-compatible player
- **Remote Access**: Works seamlessly with **Tailscale** for secure remote streaming without port forwarding
- **Legacy Auth**: **REQUIRED** for most clients. Enable "Legacy Authentication" or "Use plaintext password" in your app settings (Amperfy, Symfonium).

### Redesigned Library

- **Hierarchical View**: Browse by **Service → Playlist → Tracks**
- **Folders**: Organizational structure that keeps your library clean
- **Management**: Rename files, edit metadata, and manage storage directly from the UI
- **Rescan**: Detects manually added files or fixes missing entries

### Modern UI/UX

- **Glassmorphism**: Stunning, responsive interface powered by React & TailwindCSS
- **Neon Aesthetics**: New "Liquid Neon" styling with glowing borders and glass effects
- **Themes**: Deep Void (Default), Midnight, Ocean, Forest, Sunset, Neon
- **Feedback**: Real-time progress updates via global notifications

## 🛠️ Tech Stack

| Component          | Technology                                                 |
| ------------------ | ---------------------------------------------------------- |
| **Backend**        | Python, FastAPI, yt-dlp, SQLAlchemy (Async), APScheduler   |
| **Frontend**       | React, TypeScript, TailwindCSS v4, Framer Motion           |
| **Database**       | SQLite (default) / PostgreSQL (supported), Redis (Caching) |
| **Infrastructure** | Docker & Docker Compose                                    |

## 🚀 Getting Started

The recommended way to run Audiovault is via **Docker**.

### System Requirements

- **OS**: Windows, macOS, or Linux (any OS running Docker)
- **CPU**: 2 vCPU cores (Minimum). `yt-dlp` benefits from faster CPUs during encoding
- **RAM**:
  - **Minimum**: 2 GB
  - **Recommended**: 4 GB (Smooth operation for heavy encoding tasks)
- **Storage**:
  - Application: ~2 GB (Docker Images & Database)
  - Content: Depends on your music library size

### Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/Bl4nk44/Audiovault.git
   cd Audiovault
   ```

2. **Configure Environment**:
   Rename `.env.example` to `.env` and fill in the necessary secrets.

   ```bash
   cp .env.example .env
   ```

3. **Run with Docker**:

   ```bash
   docker compose up -d --build
   ```

   - **Backend API**: `http://localhost:8000/docs`
   - **Frontend**: `http://localhost:3000`

   > **Note:** On first launch, a random admin password will be generated and printed to the container logs (`docker compose logs backend`).
   > To set a custom password, add `FIRST_SUPERUSER_PASSWORD=yourpassword` to your `.env` file before starting.
   > Default email: `admin@example.com`

### Reverse Proxy Configuration

Audiovault supports running behind reverse proxies (Nginx, Traefik, etc.) out of the box.

1. **Environment Variables**:
   Set `ALLOWED_HOSTS` and `BACKEND_CORS_ORIGINS` in your `.env` file to match your domain:

   ```bash
   ALLOWED_HOSTS=audiovault.example.com,localhost
   BACKEND_CORS_ORIGINS=https://audiovault.example.com
   ```

   **Docker Configuration**:
   If running behind a proxy or in a custom Docker network, ensure the Frontend container knows how to reach the Backend:

   ```bash
   # In docker-compose.yml or env:
   BACKEND_URL=http://audiovault-backend:8000
   ```

2. **Docker Setup**:
   The Docker image is already configured to trust `X-Forwarded-*` headers from any proxy via `uvicorn.middleware.proxy_headers`. Ensure your proxy passes these headers correctly.

## 📚 Documentation

For detailed guides and documentation, please visit our [**Wiki**](https://github.com/Bl4nk44/Audiovault/wiki):

- [Getting Started](https://github.com/Bl4nk44/Audiovault/wiki/Getting-Started)
- [Configuration Guide](https://github.com/Bl4nk44/Audiovault/wiki/Configuration)
- [Usage Guide](https://github.com/Bl4nk44/Audiovault/wiki/Usage-Guide)
- [Architecture](https://github.com/Bl4nk44/Audiovault/wiki/Architecture)
- [Development Setup](https://github.com/Bl4nk44/Audiovault/wiki/Development)
- [FAQ & Troubleshooting](https://github.com/Bl4nk44/Audiovault/wiki/FAQ-&-Troubleshooting)

## 🐛 Support & Issues

- **[Get Help](SUPPORT.md)** - Troubleshooting guide and FAQ
- **[Report a Bug](https://github.com/Bl4nk44/Audiovault/issues/new?template=bug_report.md)** - Submit a bug report
- **[Request a Feature](https://github.com/Bl4nk44/Audiovault/issues/new?template=feature_request.md)** - Suggest new features
- **[Ask Questions](https://github.com/Bl4nk44/Audiovault/discussions)** - Community discussions

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) to learn about:

- How to report bugs and suggest features
- Development setup and workflow
- Code style guidelines
- Testing requirements
- Pull request process

**Quick contribution process**:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'feat: Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a [Pull Request](https://github.com/Bl4nk44/Audiovault/pulls)

## 🔒 Security

If you discover a security vulnerability, please email [bl4nk44@pm.me](mailto:bl4nk44@pm.me) instead of using the issue tracker.

For more information, see our [Security Policy](SECURITY.md).

## 📝 Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## 📜 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

## 🌟 Acknowledgments

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - Powerful video/audio downloader
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework
- **[React](https://react.dev/)** - JavaScript library for building UIs
- **[TailwindCSS](https://tailwindcss.com/)** - Utility-first CSS framework
- **[SQLAlchemy](https://www.sqlalchemy.org/)** - Python SQL toolkit


