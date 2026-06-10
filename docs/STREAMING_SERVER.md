# Personal Streaming Server

Turn Audiovault into your personal streaming service, accessible from anywhere.
Audiovault implements the Subsonic API (v1.16.1 / OpenSubsonic), allowing you to stream your local music library to almost any device using compatible clients.

## Compatible Clients

| Client | Platform | Notes |
|---|---|---|
| [Symfonium](https://symfonium.app/) | Android | **Recommended** — polished UI, offline cache, gapless |
| [Ultrasonic](https://gitlab.com/ultrasonic/ultrasonic) | Android | Free, open-source |
| [DSub](https://github.com/daneren2005/Subsonic-Apps) | Android | Mature, feature-rich, free |
| [Amperfy](https://github.com/amperfy/amperfy) | iOS | **Recommended** — actively maintained, verified working |
| [substreamer](https://substreamerapp.com/) | iOS | Paid, polished |
| [Sonixd](https://github.com/jeffvli/sonixd) | Desktop (Win/Mac/Linux) | **Recommended** — Electron, best desktop experience |
| [Supersonic](https://github.com/dweymouth/supersonic) | Desktop (Win/Mac/Linux) | Lightweight Go app |
| [Feishin](https://github.com/jeffvli/feishin) | Desktop (Win/Mac/Linux) | Modern UI, actively developed |
| [Navidrome Web UI](https://www.navidrome.org/) | Browser | Not applicable — Audiovault has its own web UI |

## Connection Details

To connect any client to Audiovault:

| Field | Value |
|---|---|
| **Server Type** | Subsonic / OpenSubsonic |
| **Address (local)** | `http://YOUR_LOCAL_IP:2137` (e.g., `http://192.168.1.100:2137`) |
| **Address (Tailscale)** | `http://YOUR_TAILSCALE_IP:2137` |
| **Username** | Your Audiovault username (e.g., `admin`) |
| **Password** | Your Audiovault password |
| **API Path** | Leave empty or `/rest` (auto-detected by most clients) |

> Port `2137` is the frontend Nginx which proxies `/rest/*` to the backend. You can also use port `8000` (direct backend) but `2137` is recommended.

## ⚠️ Required: Legacy Authentication

Audiovault hashes passwords with bcrypt, which is incompatible with Subsonic's default token-based auth (which requires a plaintext or MD5 password on the server side).

**You MUST enable "Legacy Authentication" (plaintext password over the network) in your client.** This is safe as long as you use HTTPS — see [Remote Access](#remote-access--https) below.

### Per-Client Instructions

**Symfonium (Android)**
1. Add host → Edit → tap **Advanced**
2. Enable **Legacy Authentication**

**DSub (Android)**
1. Settings → Server → enable **Use plaintext password**

**Ultrasonic (Android)**
1. Server settings → enable **Force plain text password**

**Amperfy (iOS)**
1. Edit Server → enable **Legacy Authentication** / **Use plaintext password**

**substreamer (iOS)**
1. Add server → Advanced → enable **Legacy Password**

**Sonixd / Feishin / Supersonic (Desktop)**
1. Most fall back to legacy automatically. If you get 401, look for a "Password encryption" or "Token auth" toggle and disable it.

> If you see `401 Unauthorized`, it almost always means Legacy Authentication is disabled.

## Background Playback & Lock Screen Controls

Audiovault acts as the **streaming server** — it delivers audio over HTTP via the Subsonic API. All playback and UI are handled by the client app on your device.

**Both iOS and Android clients listed above support:**
- Background audio playback (music continues when you switch apps or lock the screen)
- Lock screen controls (play/pause, next, previous, track title and artwork)
- Home screen / notification widget (Android)
- Control Center integration (iOS)
- AirPlay (iOS) and Cast (Android, app-dependent)

This works because Amperfy uses `AVAudioSession` with the playback category on iOS, and Symfonium/DSub use a foreground `MediaSession` service on Android — both are standard OS mechanisms for background audio. No special configuration in Audiovault is needed.

## Remote Access & HTTPS

For access outside your home network, two options:

### Option A: Tailscale (Recommended — zero config)

1. Install [Tailscale](https://tailscale.com/) on your server and your phone.
2. Use your server's Tailscale IP in the app (e.g., `http://100.64.x.x:2137`).
3. Traffic is encrypted end-to-end — Legacy Auth is safe without a separate TLS certificate.

### Option B: Reverse Proxy + HTTPS

Expose Audiovault via a domain with TLS. See [REVERSE_PROXY.md](REVERSE_PROXY.md) for Nginx Proxy Manager, Traefik, Caddy, and other setups.

Once behind HTTPS, all credentials travel encrypted — Legacy Auth is safe.

> ⚠️ Avoid exposing port 2137 or 8000 directly to the internet without TLS. Without HTTPS, your password is sent in plaintext.

## Troubleshooting

### `401 Unauthorized`
1. Verify the password works on the Audiovault web UI.
2. **Enable Legacy Authentication** in the client — this is the most common cause.

### "Connection Refused" / "Cannot Connect"
- Check IP and port: `2137` (frontend) or `8000` (direct backend).
- Ensure Docker containers are running: `docker compose ps`.
- For Tailscale: ensure Tailscale is active on both devices.
- For reverse proxy: ensure the proxy forwards the `/rest/` path correctly (see [REVERSE_PROXY.md](REVERSE_PROXY.md)).

### "Invalid credentials" after password change
- Restart the Audiovault backend: `docker compose restart backend`.
- Log out and log back in on the client.

### Tracks not appearing in the client
- Audiovault indexes your library automatically. Trigger a manual re-scan from the web UI if recently downloaded tracks are missing.

### Client shows wrong artwork or metadata
- Artwork and metadata come from the stored ID3 tags. Editing them in the Audiovault web UI will update what clients see after a library refresh.

### Slow streaming / buffering
- Check your network bandwidth. For remote access, prefer Tailscale over a direct internet connection.
- Reduce streaming quality in the client settings (most clients let you choose a max bitrate).

### Playback stops after a few seconds
- This usually means the connection dropped. Check firewall rules if using a reverse proxy.
- On iOS with Amperfy, ensure Background App Refresh is enabled for the app in iOS Settings.
