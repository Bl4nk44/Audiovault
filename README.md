# Audiovault

**Your Personal Music Sanctuary.**

Audiovault is a powerful, self-hosted application designed to import, manage, and download your music libraries from **any major streaming platform** directly to your local server. Built with performance, aesthetics, and reliability in mind.

![Audiovault Dashboard](https://i.imgur.com/gF9NGZu.png)

## Features

### Extensive Platform Support

Import playlists, albums, and tracks from:

- **Spotify**
- **YouTube** (Playlists, Mixes, Videos)
- **Apple Music**
- **Tidal**
- **Deezer**
- **Amazon Music**
- **SoundCloud** (Direct High-Speed Download)

### Robust Fallback System

Never miss a track. If a download fails (e.g., due to geo-restrictions or broken links), Audiovault automatically:

1.  Tries alternative search queries (Official Audio, Lyrics Video).
2.  Searches cross-platform (e.g., falls back to SoundCloud if YouTube fails).
3.  Uses proxies (Invidious) to bypass region locks.

### Watchlist & Automation

- **Auto-Sync**: Background scheduler checks for new tracks every 60 minutes.
- **Safe Purge**: Automatically removes local tracks that were deleted from remote playlists (with specific user approval & dry-run safety).
- **Smart De-duplication**: Prevents duplicate downloads by checking both ID3 tags and internal database history.
- **Universal Search**: Unified search bar for all supported providers.

### Redesigned Library

- **Hierarchical View**: Browse by **Service -> Playlist -> Tracks**.
- **Folders**: Organizational structure that keeps your library clean.
- **Management**: Rename files, edit metadata, and manage storage directly from the UI.
- **Rescan**: Detects manually added files or fixes missing entries.

### Modern UI/UX

- **Glassmorphism**: Stunning, responsive interface powered by React & TailwindCSS.
- **Themes**: Deep Void (Default), Midnight, Ocean, Forest, Sunset, Neon.
- **Feedback**: Real-time progress updates via global notifications.

## Tech Stack

- **Backend**: Python, FastAPI, yt-dlp, SQLAlchemy (Async), APScheduler
- **Frontend**: React, TypeScript, TailwindCSS v4, Framer Motion
- **Database**: SQLite (default) / PostgreSQL (supported), Redis (Caching & Locking)
- **Infrastructure**: Docker & Docker Compose

## Getting Started

The recommended way to run Audiovault is via **Docker**.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- [Git](https://git-scm.com/) installed.

### System Requirements

- **OS**: Windows, macOS, or Linux (any OS running Docker).
- **CPU**: 2 vCPU cores (Minimum). `yt-dlp` benefits from faster CPUs during encoding.
- **RAM**:
  - **Minimum**: 2 GB
  - **Recommended**: 4 GB (Smooth operation for heavy encoding tasks)
- **Storage**:
  - Application: ~2 GB (Docker Images & Database)
  - Content: Depends on your music library size.

### Installation

1.  **Clone the repository**:

    ```bash
    git clone https://github.com/Bl4nk44/Audiovault.git
    cd Audiovault
    ```

2.  **Configure Environment**:
    Rename `.env.example` to `.env` and fill in the necessary secrets.

    ```bash
    cp .env.example .env
    ```

3.  **Run with Docker**:

    ```bash
    docker compose up -d --build
    ```

    - **Backend API**: `http://localhost:8000/docs`

    > **Note:** On first launch, a random admin password will be generated and printed to the container logs (`docker compose logs backend`).
    > To set a custom password, add `FIRST_SUPERUSER_PASSWORD=yourpassword` to your `.env` file before starting.
    > Default email: `admin@example.com`

### Reverse Proxy Configuration

Audiovault supports running behind reverse proxies (Nginx, Traefik, etc.) out of the box.

1.  **Environment Variables**:
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

2.  **Docker Setup**:
    The Docker image is already configured to trust `X-Forwarded-*` headers from any proxy via `uvicorn.middleware.proxy_headers`. Ensure your proxy passes these headers correctly.

## How It Works

1.  **Search & Add**: Paste a link from any supported service into the Search bar.
2.  **Metadata Extraction**: The backend uses `yt-dlp` to extract high-quality metadata (Title, Artist, Album, Cover Art) from the source.
3.  **Smart Resolution**:
    - A search query is built based on the metadata.
    - The best quality audio source is located on YouTube or SoundCloud.
4.  **Download & Tag**: Steps are executed asynchronously. The file is downloaded, converted to MP3/FLAC, and tagged with ID3v2 metadata.
5.  **Library Organization**: The file is moved to your library and indexed in the database, available for streaming or export.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

Distributed under the MIT License. See `LICENSE` for more information.
