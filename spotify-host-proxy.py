#!/usr/bin/env python3
"""
Spotify embed proxy — run on WSL2 host (outside Docker).

Fetches open.spotify.com/embed/* using the residential IP of the host machine,
bypassing Spotify's IP-based blocking of Docker/VPS datacenter ranges.

Usage:
    python3 spotify-host-proxy.py          # foreground, port 3001
    python3 spotify-host-proxy.py --port 3001 --host 0.0.0.0

Docker containers reach this via http://host.docker.internal:3001/
Set SPOTIFY_HOST_PROXY=http://host.docker.internal:3001 in .env to enable.
"""

import http.server
import json
import logging
import re
import sys
import urllib.error
import urllib.request

PORT = 3001
HOST = "0.0.0.0"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("spotify-proxy")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_EMBED_BASE = "https://open.spotify.com/embed"


def _fetch_embed(resource_type: str, resource_id: str) -> dict:
    url = f"{_EMBED_BASE}/{resource_type}/{resource_id}"
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=12) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("__NEXT_DATA__ not found in embed page")

    data = json.loads(m.group(1))
    return data["props"]["pageProps"]["state"]["data"]["entity"]


def _track_id(uri: str) -> str:
    return uri.split(":")[-1]


def _clean_artists(subtitle: str) -> str:
    # subtitle uses   (non-breaking space) between artists separated by commas
    return subtitle.replace(" ", " ").strip()


def _fmt_track(t: dict, playlist_image: str | None = None) -> dict:
    return {
        "id": _track_id(t.get("uri", "")),
        "title": t.get("title", "Unknown"),
        "artist": _clean_artists(t.get("subtitle", "Unknown Artist")),
        "artist_id": None,
        "album": None,
        "duration_ms": t.get("duration"),
        "image_url": playlist_image,
        "source": "spotify",
        "popularity": 0,
        "isrc": None,
    }


def _get_image(entity: dict) -> str | None:
    cover = entity.get("coverArt") or {}
    sources = cover.get("sources") or []
    return sources[0]["url"] if sources else None


def handle_playlist(playlist_id: str) -> dict:
    entity = _fetch_embed("playlist", playlist_id)
    image = _get_image(entity)
    tracks = [_fmt_track(t, image) for t in entity.get("trackList", [])]
    return {
        "id": entity.get("id", playlist_id),
        "title": entity.get("name") or entity.get("title"),
        "image_url": image,
        "source": "spotify",
        "type": "playlist",
        "track_count": len(tracks),
        "tracks": tracks,
    }


def handle_album(album_id: str) -> dict:
    entity = _fetch_embed("album", album_id)
    image = _get_image(entity)
    artist = _clean_artists(entity.get("subtitle", "Unknown Artist"))
    tracks = [_fmt_track(t, image) for t in entity.get("trackList", [])]
    return {
        "id": entity.get("id", album_id),
        "title": entity.get("name") or entity.get("title"),
        "artist": artist,
        "artist_id": None,
        "image_url": image,
        "release_date": (entity.get("releaseDate") or {}).get("isoString"),
        "total_tracks": len(tracks),
        "album_type": "album",
        "label": None,
        "tracks": tracks,
        "source": "spotify",
        "type": "album",
    }


def handle_track(track_id: str) -> dict:
    entity = _fetch_embed("track", track_id)
    image = _get_image(entity)
    return _fmt_track(
        {
            "uri": entity.get("uri", f"spotify:track:{track_id}"),
            "title": entity.get("name") or entity.get("title", "Unknown"),
            "subtitle": entity.get("subtitle", ""),
            "duration": entity.get("duration"),
        },
        playlist_image=image,
    )


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        if path == "/health":
            self._json({"ok": True})
            return

        m = re.match(r"^/(playlist|album|track)/([A-Za-z0-9]+)$", path)
        if not m:
            self._error(404, "Not found")
            return

        resource_type, resource_id = m.group(1), m.group(2)
        try:
            if resource_type == "playlist":
                result = handle_playlist(resource_id)
            elif resource_type == "album":
                result = handle_album(resource_id)
            else:
                result = handle_track(resource_id)
            self._json(result)
            log.info("OK %s/%s (%d tracks)", resource_type, resource_id, len(result.get("tracks") or [result]))
        except urllib.error.HTTPError as e:
            log.warning("Spotify HTTP %d for %s/%s", e.code, resource_type, resource_id)
            self._error(502, f"Spotify returned {e.code}")
        except Exception as e:
            log.error("Error %s/%s: %s", resource_type, resource_id, e)
            self._error(500, str(e))

    def _json(self, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code: int, msg: str):
        body = json.dumps({"error": msg}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # handled by stdlib logger above


def main():
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--port" and i + 1 < len(sys.argv) - 1:
            globals()["PORT"] = int(sys.argv[i + 2])
        if arg == "--host" and i + 1 < len(sys.argv) - 1:
            globals()["HOST"] = sys.argv[i + 2]

    server = http.server.HTTPServer((HOST, PORT), ProxyHandler)
    log.info("Spotify embed proxy listening on %s:%d", HOST, PORT)
    log.info("Add to .env: SPOTIFY_HOST_PROXY=http://host.docker.internal:%d", PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Stopped")


if __name__ == "__main__":
    main()
