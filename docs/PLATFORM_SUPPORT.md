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

## Direct URL Import

You can paste a URL from any supported platform directly into the Audiovault search bar. The app auto-detects the platform from the URL and routes the request to the correct provider — no need to select a source manually.

**Supported URL types:**

| Platform | Example URLs |
|---|---|
| Spotify | `https://open.spotify.com/playlist/...`, `https://open.spotify.com/album/...`, `https://open.spotify.com/track/...` |
| YouTube | `https://www.youtube.com/watch?v=...`, `https://youtu.be/...`, `https://www.youtube.com/playlist?list=...` |
| Deezer | `https://www.deezer.com/playlist/...`, `https://www.deezer.com/album/...` |
| SoundCloud | `https://soundcloud.com/artist/track`, `https://soundcloud.com/artist/sets/playlist` |
| Apple Music | `https://music.apple.com/...`, `https://apple.co/...` (short links resolved automatically) |
| Tidal | `https://listen.tidal.com/...`, `https://tidal.com/browse/...` |
| Amazon Music | `https://music.amazon.com/...` |

Pasting an album or playlist URL imports all tracks. Individual track URLs download a single file.

## Adding New Platforms

New platforms are registered in `backend/app/providers/__init__.py` via `provider_manager.register_provider()`. Each platform needs a provider class (metadata + URL detection) and optionally a dedicated service (download logic). `GenericProvider` (yt-dlp wildcard) must remain last in the registration order. See the `platform-integrator` subagent for end-to-end scaffolding.
