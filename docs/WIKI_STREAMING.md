# Streaming Guide 📱

Audiovault implements the Subsonic API (v1.16.1), allowing you to stream your music library to almost any device using compatible clients.

## Compatible Clients

We recommend the following clients:

- **Desktop/Linux**: [Sonixd](https://github.com/tempugh/Sonixd) (Highly Recommended), [Supersonic](https://github.com/dweymouth/supersonic), [Feishin](https://github.com/jeffvli/feishin)
- **Android**: [Symfonium](https://symfonium.app/) (Recommended), [DSub](https://github.com/daneren2005/Subsonic-Apps)
- **iOS**: [Amperfy](https://github.com/amperfy/amperfy) (Verified), [substreamer](https://substreamerapp.com/)

## Connection Details

To connect your client to Audiovault:

1.  **Server Type**: Subsonic / OpenSubsonic
2.  **Address**:
    - **Local**: `http://YOUR_LOCAL_IP:80` (e.g., `http://192.168.1.100`) or just `http://YOUR_LOCAL_IP`
    - **Tailscale**: `http://YOUR_TAILSCALE_IP:80`
    - _Note: Backend direct port is 8000, but using the main port 80 (frontend proxy) is recommended._
3.  **Username**: Your Audiovault username (e.g., `admin`)
4.  **Password**: Your Audiovault password

### ⚠️ IMPORTANT: Legacy Authentication

Audiovault stores passwords securely using bcrypt, which is incompatible with Subsonic's legacy token-based authentication (which requires storing plaintext passwords or unsalted MD5 hashes).

**You MUST enable "Legacy Authentication" in your client.**

- **Symfonium**: Settings → Host → Edit → Advanced → **Legacy Authentication** (Check this)
- **Amperfy**: Edit Server → **Legacy Authentication** / **Use plaintext password**
- **DSub**: Settings → Server → **Use plaintext password**
- **Feishin**: Works automatically (usually falls back to legacy).

If you see a `401 Unauthorized` error, it is almost certainly because this setting is disabled.

## Troubleshooting

### "Bad Credentials" / 401 Error

- Verify your password works on the Web UI.
- **Enable Legacy Authentication** in your app settings.

### "Connection Refused"

- Ensure you are using the correct IP and Port (`5173` or `8000`).
- If using Tailscale, ensure Tailscale is active on both devices.
