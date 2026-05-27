# Spotify Integration

Audiovault features a seamless, zero-configuration Spotify integration that works out of the box — no developer account, no API keys, no external scripts.

## How It Works

Audiovault uses Spotify's **internal Partner GraphQL API** (`api-partner.spotify.com`) — the same endpoint the official Spotify Web Player uses in your browser. Authentication is fully anonymous and automatic via a TOTP-based token chain:

```
Public TOTP secrets → TOTP code → open.spotify.com/api/token → access_token
                                → clienttoken.spotify.com   → client_token
                                → api-partner.spotify.com (GraphQL)
```

No Spotify account required. No developer app registration. No cookies.

### Key advantages over the old approach

| | Old (Client Credentials) | Current (Partner API) |
|---|---|---|
| API keys required | ✅ Yes | ❌ No |
| Works from Docker/VPS | ❌ No (Spotify blocked datacenter IPs in May 2024) | ✅ Yes |
| Playlist track limit | 100 tracks per page, rate-limited | **343 tracks/request**, unlimited pagination |
| Albums & tracks | ✅ | ✅ |
| Setup required | Developer account + app registration | Nothing |

## Features Supported

- **Playlists** — public, any size (hundreds or thousands of tracks, fully paginated)
- **Albums**
- **Tracks**
- **Artist top tracks & discography**

## Configuration

No configuration is needed. Audiovault handles all authentication automatically on first use.

Optional overrides in `.env`:

```env
# Use your own Spotify developer app credentials instead of the built-in ones
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret

# sp_dc cookie — free Spotify account cookie, ~1yr TTL
# How to get: open.spotify.com → DevTools → Application → Cookies → copy sp_dc value
# Used as a fallback authentication layer when TOTP token acquisition fails
SPOTIFY_SP_DC=your_sp_dc_cookie_value

# Host proxy for embed scraping — limited to 50 tracks, requires running
# spotify-host-proxy.py on the Docker host (e.g. WSL2 host machine)
SPOTIFY_HOST_PROXY=http://host.docker.internal:8765
```

> **Note**: None of the above are required. The built-in TOTP-based Partner API works without any credentials.

### OAuth fallback (for private playlists)

If you want to import **private playlists**, you can authenticate with your own Spotify account via the built-in OAuth flow:

1. Visit `http://localhost:8000/api/v1/spotify/oauth/start` in your browser
2. Log in with your Spotify account
3. Audiovault saves the refresh token to `/downloads/.spotify_auth.json` — all future requests use it silently

> **Note**: Private playlist support requires completing the OAuth flow once. Public playlists work without any OAuth.

## Architecture

The integration is split into two layers:

### `spotify_partner.py` — primary metadata source

Handles all playlist, album, and track metadata via the Partner GraphQL API:

- **Token management**: TOTP secret fetched automatically, access token and client token refreshed before expiry, all protected by an async lock
- **Hash auto-discovery**: GraphQL operations use SHA-256 persisted query hashes. If Spotify deploys a new JS bundle with an updated hash, the client extracts it automatically from the CDN bundle — no manual updates needed
- **Full pagination**: Fetches all tracks regardless of playlist size (batch size: 343 tracks per request)
- **Redis caching**: Playlist responses cached for 24 hours — minimizes API calls on repeated imports
- **Responsible rate-limiting**: Random jitter between paginated requests, rotated User-Agent pool, full browser headers — behaves like a real web player session

### `spotify_service.py` — fallback chain

When a playlist, album, or track is requested, the service tries sources in this order:

1. **Partner API** (`spotify_partner.py`) — primary, always tried first
2. **Host proxy** — embed scraping via `SPOTIFY_HOST_PROXY` env var if configured; limited to 50 tracks, requires a proxy script on the host machine
3. **Spotify Web API** — standard REST API; requires an OAuth refresh token (private playlists only)

## Troubleshooting

**Playlist returns empty or 0 tracks**
- Check backend logs: `docker compose logs backend | grep -i spotify`
- The GraphQL hash may have changed after a Spotify deployment — the client will auto-discover the new one on the next request

**Import fails with "Could not extract playlist"**
- Verify the playlist is public (private playlists require completing the OAuth flow)
- Try again after 30 seconds — token acquisition may have been temporarily rate-limited

**Very large playlists (500+ tracks) take a while**
- Expected — pagination includes small random delays to behave like a normal browser session
- The result is cached in Redis for 24 hours, so subsequent imports of the same playlist are instant
