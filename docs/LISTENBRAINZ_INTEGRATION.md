# ListenBrainz Integration Guide

Audiovault supports [ListenBrainz](https://listenbrainz.org) as a second,
selectable listening provider alongside [Last.fm](./LASTFM_INTEGRATION.md).
ListenBrainz is MetaBrainz's open-source scrobbling service.

You can connect **either or both** providers. Scrobbles are sent to every
connected provider; recommendations are generated from the one you choose.

## Features

- **Scrobbling** ("submitting listens") to your ListenBrainz profile.
- **Recommendations** built from your ListenBrainz listening history
  (top recordings, top artists, recent listens). The similarity expansion
  still uses the public Last.fm graph, so `LASTFM_API_KEY` improves
  ListenBrainz recommendation quality but is not required to connect.
- **Now Playing** updates while a track is playing.

## Setup

No application registration and no server-side API key are needed.

### Step 1 — get your token

1. Log in to [listenbrainz.org](https://listenbrainz.org).
2. Open **[Settings](https://listenbrainz.org/settings/)**.
3. Copy your **User token**.

### Step 2 — (optional) self-hosted instance

Only if you run your own ListenBrainz server, set the base URL in `.env`:

```bash
LISTENBRAINZ_API_URL=https://your-instance.example.org
```

The default is `https://api.listenbrainz.org`.

### Step 3 — connect in the app

1. Open the **Recommendations** page.
2. In the **ListenBrainz** row, paste your token and click **Connect ListenBrainz**.
3. The token is validated against ListenBrainz and stored encrypted.

### Step 4 — choose your recommendation source

When both Last.fm and ListenBrainz are connected, a **Recommendation source**
switch appears on the Recommendations page (Last.fm / ListenBrainz / Auto).
"Auto" uses the first connected provider.

## Notes

- The stored token is encrypted at rest (`service_credentials` table).
- ListenBrainz has no "friends" concept, so that section of the profile card
  is Last.fm-only.
- ListenBrainz `recommendation/tracks` (its own precomputed recommendations)
  is not consumed yet — seeds come from your listening stats and are expanded
  via Last.fm. This may change in a future release.

## Troubleshooting

- **"ListenBrainz authentication failed"**: the token is wrong or expired —
  copy it again from the ListenBrainz settings page.
- **Few or no recommendations**: you need some listening history on
  ListenBrainz; also set `LASTFM_API_KEY` for a richer similarity graph.
