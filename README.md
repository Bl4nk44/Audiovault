# 🎵 Audiovault

**Your Personal Music Sanctuary.**

Audiovault is a powerful, self-hosted application designed to import, manage, and download your music libraries from Spotify, Deezer, and YouTube directly to your local server. Built with performance and aesthetics in mind.

![Audiovault Dashboard](https://github.com/Bl4nk44/Audiovault/raw/main/screenshots/dashboard.png)

## ✨ Features

- **Multi-Platform Support**: Import playlists and tracks from **Spotify**, **Deezer**, and **YouTube**.
- **High Quality Audio**: Downloads tracks in high-quality formats (MP3/FLAC) with embedded metadata.
- **Automated Tagging**: Automatically fetches and embeds album art, artist info, and lyrics.
- **Modern UI**: A stunning, glassmorphic interface powered by React and TailwindCSS.
- **Advanced Theming**:
  - **Deep Void**: A default theme integrating brand colors (Neon Green/Purple) with a dynamic nebula background.
  - **Classic Mode**: A high-performance, retro "Terminal" style theme for low-resource environments.
- **Docker First**: Deployment is as simple as running a single command.

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, yt-dlp, SQLAlchemy
- **Frontend**: React, TypeScript, TailwindCSS, Framer Motion
- **Database**: SQLite (default) / PostgreSQL (supported)
- **Infrastructure**: Docker & Docker Compose

## 🚀 Getting Started

The recommended way to run Audiovault is via **Docker**.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- [Git](https://git-scm.com/) installed.

### Installation

1.  **Clone the repository**:

    ```bash
    git clone https://github.com/Bl4nk44/Audiovault.git
    cd Audiovault
    ```

2.  **Configure Environment**:
    Rename `.env.example` to `.env` and fill in the necessary information (API keys, secrets, etc.).

    ```bash
    cp .env.example .env
    # Edit the file with your preferred editor
    ```

3.  **Run with Docker**:

    ```bash
    docker compose up -d --build
    ```

4.  **Access the App**:
    Open your browser and navigate to:
    - **Frontend**: `http://localhost:5173` (or `http://localhost:80` if configured for production)
    - **Backend API**: `http://localhost:8000/docs`

## 🎨 Theming

Audiovault comes with a robust theming engine.

- **Standard Themes**: Midnight, Ocean, Forest, Sunset, Neon.
- **Classic Mode**: Enable this in Settings > Appearance for a raw, high-performance interface with no animations or blur effects (Terminal style).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1.  Fork the project.
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the Branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

## 📜 License

Distributed under the PolyForm Noncommercial License 1.0.0. See `LICENSE` for more information. This project is free for personal use but strictly prohibits commercial usage.
