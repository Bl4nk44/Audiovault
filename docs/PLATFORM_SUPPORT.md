# Platform Support & Fallback System

Audiovault pulls metadata and audio from multiple streaming services via dedicated service implementations and a yt-dlp fallback chain.

## Supported Platforms

| Platform | Implementation | Notes |
|---|---|---|
| **Spotify** | Native Partner GraphQL API | Zero-config. Playlists, albums, tracks, artist discography. See [SPOTIFY_INTEGRATION.md](SPOTIFY_INTEGRATION.md). |
| **YouTube** | Dedicated service + yt-dlp | Playlists, mixes, individual videos, channels. |
| **Deezer** | Dedicated service | Native search, artist profiles, playlists. |
| **SoundCloud** | Dedicated service | Tracks, playlists, user libraries. |
| **Apple Music** | yt-dlp + short-URL resolution | Short links (`apple.co`) resolved before download. No native API. |
| **Tidal** | yt-dlp fallback only | No native Tidal API. URL matched, audio fetched via yt-dlp. |
| **Amazon Music** | yt-dlp fallback only | No native Amazon API. URL matched, audio fetched via yt-dlp. |

> **yt-dlp fallback**: Platforms without a native implementation use yt-dlp's built-in extractors. Quality and metadata completeness depend on what yt-dlp can retrieve for that platform.

## Metadata Enrichment

- **MusicBrainz** — used for MBID lookups, canonical artist/release data, and track deduplication
- **Last.fm** — recommendations and scrobbling (requires API key, see [LASTFM_INTEGRATION.md](LASTFM_INTEGRATION.md))
- **Genius** — lyrics (requires `GENIUS_API_TOKEN`)

## Fallback System

If a download fails (region lock, broken link, platform restriction), Audiovault tries the following in order:

1. **Alternative query** — retries with suffixes like "Official Audio" or "Lyrics Video"
2. **Cross-platform search** — falls back to SoundCloud or YouTube if the primary source fails
3. **Proxy support** — uses Invidious or a configured host proxy to bypass regional restrictions

## Adding New Platforms

New platforms are registered in `backend/app/providers/manager.py` and `backend/app/api/v1/platform_registry.py`. Each platform needs a provider (metadata) and optionally a dedicated service (download logic). See the `platform-integrator` subagent for end-to-end scaffolding.
