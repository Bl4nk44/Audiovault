# Platform Support & Fallback System

Audiovault is designed to pull metadata and audio from a vast array of streaming services.

## Supported Platforms

- **Spotify**: Playlists, albums, liked songs, recommendations (Zero-config)
- **YouTube**: Playlists, mixes, videos, channels
- **Deezer**: Native search, artist profiles, playlists
- **SoundCloud**: Tracks, playlists, user libraries
- **Apple Music**: Playlists, library, recommendations
- **Tidal**: Playlists, favorites, discovery
- **Amazon Music**: Playlists, library, recommendations

## Robust Fallback System

If a download fails due to restrictions (e.g., region locks) or broken links, Audiovault's automatic fallback system ensures you still get your music:

1. **Alternative Search**: Tries alternative queries such as "Official Audio" or "Lyrics Video".
2. **Cross-Platform Search**: Automatically falls back to other platforms (like SoundCloud or YouTube) if the primary source fails.
3. **Proxy Support**: Uses proxies (like Invidious) to bypass regional restrictions.
