# Product Context: Audiovault

## User Personas

### Primary: The Self-Hoster
- **Profile**: Tech-savvy user running home server (Unraid, TrueNAS, etc.)
- **Goals**: Consolidate music from multiple platforms, maintain offline library
- **Pain Points**: Geo-restrictions, platform lock-in, losing tracks when subscriptions expire
- **Tech Level**: Comfortable with Docker, environment variables, reverse proxies

### Secondary: The Music Collector
- **Profile**: User with extensive playlists across Spotify, YouTube, etc.
- **Goals**: Backup and organize music library, stream to mobile devices
- **Pain Points**: Duplicate management, metadata consistency, cross-platform sync
- **Tech Level**: Can follow setup guides, prefers web UI over CLI

### Tertiary: The Audiophile
- **Profile**: User prioritizing audio quality and proper metadata
- **Goals**: FLAC downloads, perfect tagging, lossless streaming
- **Pain Points**: Lossy compression, incorrect metadata, format limitations
- **Tech Level**: Understands audio formats, bitrates, and codec differences

## Use Cases

### UC1: Import Spotify Playlist
1. User authenticates with Spotify
2. Selects playlist to import
3. System downloads tracks via yt-dlp with fallback sources
4. Tracks appear in library with proper metadata
5. User streams via Subsonic-compatible app

### UC2: Automated Watchlist Sync
1. User adds playlist to watchlist
2. Background scheduler checks every 60 minutes
3. New tracks automatically downloaded
4. Removed tracks optionally purged (with safeguards)

### UC3: Cross-Platform Search
1. User enters song name in universal search
2. System queries all enabled providers in parallel
3. Results aggregated and deduplicated
4. User selects best match for download

## User Feedback Themes
- **Most Requested**: More platform integrations, better duplicate detection
- **Most Praised**: Fallback system, UI design, Docker deployment ease
- **Most Reported Issues**: YouTube geo-restrictions, metadata inconsistencies

## Competitive Landscape
- **Lidarr**: Focuses on artists/albums (Audiovault focuses on tracks/playlists)
- **Spotdl**: CLI-only (Audiovault has full web UI)
- **Spotify-Downloader**: Single platform (Audiovault supports 7+ platforms)
- **Navidrome/Jellyfin**: Streaming-only (Audiovault includes acquisition)
