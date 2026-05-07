<div align="center">

# Audiovault


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/Bl4nk44/Audiovault?logo=github)](https://github.com/Bl4nk44/Audiovault/releases)
[![GitHub Stars](https://img.shields.io/github/stars/Bl4nk44/Audiovault?logo=github)](https://github.com/Bl4nk44/Audiovault/stargazers)
[![Docker Pulls](https://img.shields.io/docker/pulls/bl4nk404/audiovault?logo=docker)](https://hub.docker.com/r/bl4nk404/audiovault)
[![Security monitoring by GitGuardian](https://img.shields.io/badge/Protected_by-GitGuardian-darkblue?logo=gitguardian&logoColor=white)](https://www.gitguardian.com/)
[![SonarQube](https://img.shields.io/badge/Quality-SonarQube-4E9BCD?logo=sonarqube&logoColor=white)](https://sonarqube.org/)
[![Semgrep](https://img.shields.io/badge/Semgrep-Scanned-00D26A?logo=semgrep)](https://semgrep.dev/)
[![Checkov](https://img.shields.io/badge/IaC-Checkov-blue?logo=paloaltonetworks&logoColor=white)](https://www.checkov.io/)
[![Aikido](https://img.shields.io/badge/SAST%2FSCA-Aikido-FF6B35?logo=aikido&logoColor=white)](https://aikido.dev/)
[![OSV-Scanner](https://img.shields.io/badge/CVE-OSV--Scanner-4285F4?logo=google&logoColor=white)](https://google.github.io/osv-scanner/)
[![Nuclei](https://img.shields.io/badge/DAST-Nuclei-9B59B6?logoColor=white)](https://nuclei.projectdiscovery.io/)
[![Trivy](https://img.shields.io/badge/Container-Trivy-1904DA?logo=aquasecurity&logoColor=white)](https://trivy.dev/)
[![codecov](https://codecov.io/gh/Bl4nk44/Audiovault/branch/main/graph/badge.svg)](https://codecov.io/gh/Bl4nk44/Audiovault)
[![Build Status](https://github.com/Bl4nk44/Audiovault/actions/workflows/ci.yml/badge.svg)](https://github.com/Bl4nk44/Audiovault/actions)

🔗 **Quick Links**:
[📖 Wiki](https://github.com/Bl4nk44/Audiovault/wiki) •
[🐛 Issues](https://github.com/Bl4nk44/Audiovault/issues) •
[🎯 Pull Requests](https://github.com/Bl4nk44/Audiovault/pulls) •
[💬 Discussions](https://github.com/Bl4nk44/Audiovault/discussions) •
[🤝 Contributing](CONTRIBUTING.md)

</div>

---

> **Legal Notice** — Audiovault is an independent, open-source project developed for **educational and personal use**. It is a technical demonstration of self-hosted media management and local network streaming. The author does not endorse, encourage, or condone any use of this software that violates applicable laws, the terms of service of any streaming platform, or the rights of copyright holders. You are solely responsible for how you use this software and for ensuring your usage complies with the laws of your jurisdiction. Downloading copyrighted content without authorization may be illegal. **If you enjoy an artist's work, please support them through official channels.**

---

Audiovault is a powerful, self-hosted application designed to import, manage, and download your music libraries from **any major streaming platform** directly to your local server. Built with performance, aesthetics, and reliability in mind.

![Audiovault Dashboard](https://i.imgur.com/yO8vjOy.png)

## ✨ Features

### Extensive Platform Support

- **Supported Services**: Spotify, YouTube, Deezer, SoundCloud, Apple Music, Tidal, Amazon Music
- **Zero-Config Spotify**: Uses Spotify's internal Partner GraphQL API — no developer app, no API keys, no account required. Works from Docker and VPS without restrictions. Supports playlists of any size (no 50- or 100-track limit).
- **Robust Fallback**: Automatically tries alternative sources if a primary fetch fails
- [Read the Platform & Fallback Guide](docs/PLATFORM_SUPPORT.md)
- [Read the Spotify Integration Guide](docs/SPOTIFY_INTEGRATION.md)

### Watchlist & Automation

- **Auto-Sync**: Background scheduler checks for new tracks
- **Safe Purge**: Removes local tracks deleted from remote playlists
- **Smart De-duplication**: Prevents duplicate downloads
- [Read the Automation Guide](docs/AUTOMATION.md)

### Audio Quality Options

- **Formats**: Various MP3 bitrates (128-320kbps) and Lossless FLAC
- **Smart Formatting**: Automatic format selection based on preference
- [Read the Audio Quality Guide](docs/AUDIO_QUALITY.md)

### 🎵 Last.fm Integration

- **Scrobbling**: Automatically sync your listening history to Last.fm
- **Recommendations**: Personalized track suggestions based on your taste
- **Integration**: Easy setup with OAuth connection
- [Read the Setup Guide](docs/LASTFM_INTEGRATION.md)
  > **Note**: When creating your API key, use `http://localhost:2137/recommendations` as the **Callback URL**.

### Personal Streaming Server

- **Subsonic API Support**: Native implementation for compatibility with mobile apps
- **Mobile Apps**: Stream using Symfonium, Amperfy, DSub, and more
- **Remote Access**: Seamless integration with Tailscale for secure streaming
- [Read the Streaming Server Guide](docs/STREAMING_SERVER.md)

## 🚀 Getting Started

The recommended way to run Audiovault is via **Docker**.

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

   - **Frontend**: `http://localhost:2137`
   - **Backend API**: `http://localhost:8000/docs`

   > **Important Security Note:** For the first launch, it is **highly recommended** to set your own `ADMIN_PASSWORD` in the `.env` file.
   > If not provided, a random password will be generated for the `admin` account, but for security reasons, it will **no longer be printed to the logs**.
   >
   > To set your password, add this to your `.env` before starting:
   > ```bash
   > ADMIN_PASSWORD=your_secure_password
   > ```
   > Default username: `admin`

### Reverse Proxy Configuration

Audiovault supports running behind reverse proxies out of the box. For detailed examples covering **Nginx Proxy Manager, Traefik, Caddy, HAProxy, and Zoraxy**, please see our dedicated guide:

👉 **[Reverse Proxy Setup Guide](docs/REVERSE_PROXY.md)**

1. **Environment Variables Configs**:
   Set `ALLOWED_HOSTS` and `BACKEND_CORS_ORIGINS` in your `.env` file to match your domain:

   ```bash
   ALLOWED_HOSTS=audiovault.example.com,localhost
   BACKEND_CORS_ORIGINS=https://audiovault.example.com
   ```


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
