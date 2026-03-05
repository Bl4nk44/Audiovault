# Spotify Integration

Audiovault features a seamless, zero-configuration integration with Spotify.

## Zero-Configuration Approach

Previously, Audiovault used the `spotipy` library, which required users to create a Spotify Developer account and provide a `CLIENT_ID` and `CLIENT_SECRET`.

To make the setup easier and more privacy-friendly, we have replaced `spotipy` with a custom scraping implementation using `httpx`.

### How it works

1. **Anonymous Tokens**: Audiovault automatically fetches an anonymous access token directly from Spotify's web player API.
2. **Direct Data Fetching**: Using this anonymous token, Audiovault can reliably extract metadata for tracks, albums, playlists, and artists.
3. **No Account Required**: You don't need to link your personal Spotify account or manage developer credentials to import music.

## Features Supported

- **Playlists** (Public)
- **Albums**
- **Tracks**
- **Artist Top Tracks**
