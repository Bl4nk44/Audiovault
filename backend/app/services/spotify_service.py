import logging
import re
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SpotifyService:
    def __init__(self):
        self._token: str | None = None
        self._token_expires_at: float = 0
        self.client_id = "client_anonymous"  # Extracted from response but not strictly needed for auth header

    async def get_anonymous_token(self) -> str:
        """Fetch a temporary anonymous token representing a web-player session."""
        if self._token and time.time() < self._token_expires_at:
            return self._token

        url = "https://open.spotify.com/get_access_token?reason=transport&productType=web_player"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                self._token = data.get("accessToken")
                # Tokens usually expire in 3600 seconds, setting buffer of 60 seconds
                self._token_expires_at = time.time() + 3540
                return self._token or ""
            except Exception as e:
                logger.error(f"Failed to fetch Spotify anonymous token: {e}")
                return ""

    async def _request(self, method: str, endpoint: str, params: dict | None = None) -> dict[str, Any] | None:
        """Helper to make API requests to Spotify Web API"""
        token = await self.get_anonymous_token()
        if not token:
            return None

        url = f"https://api.spotify.com/v1/{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await getattr(client, method.lower())(url, headers=headers, params=params, timeout=10.0)

                if response.status_code == 401:
                    # Token expired or invalid, invalidate cache and retry once
                    self._token = None
                    self._token_expires_at = 0
                    token = await self.get_anonymous_token()
                    headers["Authorization"] = f"Bearer {token}"
                    response = await getattr(client, method.lower())(url, headers=headers, params=params, timeout=10.0)

                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Spotify API error for {endpoint}: {e}")
                return None

    # Formatters
    def _format_artist(self, item: dict[str, Any]) -> dict[str, Any]:
        image_url = item["images"][0]["url"] if item.get("images") else None
        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "image_url": image_url,
            "source": "spotify",
            "type": "artist",
        }

    def _format_playlist(self, item: dict[str, Any], is_album: bool = False) -> dict[str, Any]:
        image_url = item["images"][0]["url"] if item.get("images") else None
        track_count = item.get("tracks", {}).get("total") if not is_album else item.get("total_tracks")
        return {
            "id": item.get("id"),
            "title": item.get("name"),
            "image_url": image_url,
            "source": "spotify",
            "type": "playlist" if not is_album else "album",
            "track_count": track_count,
        }

    def _format_track(self, item: dict[str, Any], album_obj=None) -> dict[str, Any]:
        album_name = "Unknown Album"
        image_url = None

        if "album" in item:
            album_name = item["album"]["name"]
            if item["album"].get("images") and len(item["album"]["images"]) > 0:
                image_url = item["album"]["images"][0]["url"]
        elif album_obj:
            album_name = album_obj.get("name", album_name)
            if album_obj.get("images") and len(album_obj["images"]) > 0:
                image_url = album_obj["images"][0]["url"]

        artists = ", ".join([artist["name"] for artist in item.get("artists", [])])
        artist_id = item["artists"][0]["id"] if item.get("artists") else None

        return {
            "id": item.get("id"),
            "title": item.get("name"),
            "artist": artists,
            "artist_id": artist_id,
            "album": album_name,
            "duration_ms": item.get("duration_ms"),
            "image_url": image_url,
            "source": "spotify",
            "popularity": item.get("popularity", 0),
            "isrc": item.get("external_ids", {}).get("isrc"),
        }

    # Data Fetchers
    async def get_track(self, track_id: str) -> dict[str, Any] | None:
        data = await self._request("get", f"tracks/{track_id}")
        if data:
            return self._format_track(data)
        return None

    async def get_playlist_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        tracks = []
        limit = 50
        offset = 0
        total = 1  # arbitrary starting point

        while offset < total and offset < 500:  # hard limit to prevent infinite loops for massive playlists
            data = await self._request(
                "get", f"playlists/{playlist_id}/tracks", params={"limit": limit, "offset": offset}
            )
            if not data:
                break

            total = data.get("total", 0)
            items = data.get("items", [])
            for item in items:
                track = item.get("track")
                if track:
                    tracks.append(self._format_track(track))

            offset += limit

        return tracks

    async def get_playlist_details(self, playlist_id: str) -> dict[str, Any] | None:
        data = await self._request("get", f"playlists/{playlist_id}")
        if not data:
            return None

        formatted = self._format_playlist(data)

        # In Spotify Web API, playlist endpoint already returns first 100 tracks
        tracks = []
        tracks_data = data.get("tracks", {})

        for item in tracks_data.get("items", []):
            if item.get("track"):
                tracks.append(self._format_track(item["track"]))

        # Handle pagination if more tracks exist
        limit = 50
        offset = 100
        total = tracks_data.get("total", 0)

        while offset < total and offset < 500:
            more_data = await self._request(
                "get", f"playlists/{playlist_id}/tracks", params={"limit": limit, "offset": offset}
            )
            if not more_data:
                break
            for item in more_data.get("items", []):
                if item.get("track"):
                    tracks.append(self._format_track(item["track"]))
            offset += limit

        formatted["tracks"] = tracks
        return formatted

    async def get_album_tracks(self, album_id: str) -> list[dict[str, Any]]:
        tracks = []
        # get album first to get album metadata (images etc. since /tracks doesn't return cover art)
        album_data = await self._request("get", f"albums/{album_id}")
        if not album_data:
            return []

        limit = 50
        offset = 0
        total = album_data.get("tracks", {}).get("total", 1)

        # Format tracks from initial album request
        for track in album_data.get("tracks", {}).get("items", []):
            tracks.append(self._format_track(track, album_obj=album_data))

        offset = 50
        while offset < total and offset < 500:
            data = await self._request("get", f"albums/{album_id}/tracks", params={"limit": limit, "offset": offset})
            if not data:
                break
            for track in data.get("items", []):
                tracks.append(self._format_track(track, album_obj=album_data))
            offset += limit

        return tracks

    async def get_album(self, album_id: str) -> dict[str, Any] | None:
        data = await self._request("get", f"albums/{album_id}")
        if data:
            return data
        return None

    async def get_album_details(self, album_id: str) -> dict[str, Any] | None:
        album_data = await self.get_album(album_id)
        if not album_data:
            return None

        tracks = await self.get_album_tracks(album_id)

        image_url = album_data["images"][0]["url"] if album_data.get("images") else None
        artist_name = album_data["artists"][0]["name"] if album_data.get("artists") else "Unknown Artist"
        artist_id = album_data["artists"][0]["id"] if album_data.get("artists") else None

        return {
            "id": album_data.get("id"),
            "title": album_data.get("name"),
            "artist": artist_name,
            "artist_id": artist_id,
            "image_url": image_url,
            "release_date": album_data.get("release_date"),
            "total_tracks": album_data.get("total_tracks"),
            "album_type": album_data.get("album_type", "album"),
            "label": album_data.get("label"),
            "tracks": tracks,
            "source": "spotify",
            "type": "album",
        }

    async def get_artist_top_tracks(self, artist_id: str) -> list[dict[str, Any]]:
        # Using web api requires market, but we can default
        data = await self._request("get", f"artists/{artist_id}/top-tracks", params={"market": "US"})
        if not data or "tracks" not in data:
            return []
        return [self._format_track(track) for track in data.get("tracks", [])]

    async def get_artist_albums(self, artist_id: str) -> list[dict[str, Any]]:
        albums = []
        limit = 50
        offset = 0
        total = 1

        while offset < total and offset < 200:
            params = {"include_groups": "album,single", "limit": limit, "offset": offset}
            data = await self._request("get", f"artists/{artist_id}/albums", params=params)
            if not data:
                break

            total = data.get("total", 0)
            items = data.get("items", [])
            for alb in items:
                # Filter out compilations and "Various Artists" to avoid mass-fetching unrelated tracks
                if alb.get("album_type") == "compilation":
                    continue
                if any(art.get("name", "").lower() == "various artists" for art in alb.get("artists", [])):
                    continue
                albums.append(alb)

            offset += limit

        return albums

    async def get_artist_details(self, artist_id: str) -> dict[str, Any] | None:
        artist_data = await self._request("get", f"artists/{artist_id}")
        if not artist_data:
            return None

        formatted_artist = self._format_artist(artist_data)

        top_tracks = await self.get_artist_top_tracks(artist_id)
        formatted_artist["tracks"] = top_tracks

        albums = await self.get_artist_albums(artist_id)
        formatted_albums = []
        seen_names = set()

        for album in albums:
            title = album.get("name", "")
            if title in seen_names:
                continue
            seen_names.add(title)

            image_url = album["images"][0]["url"] if album.get("images") else None
            formatted_albums.append(
                {
                    "id": album.get("id"),
                    "title": title,
                    "image_url": image_url,
                    "release_date": album.get("release_date"),
                    "total_tracks": album.get("total_tracks"),
                    "type": album.get("type"),
                    "album_type": album.get("album_type", "album"),
                }
            )

        formatted_artist["albums"] = formatted_albums
        return formatted_artist

    async def search(self, query: str, limit: int = 10, offset: int = 0, type: str = "track") -> list[dict[str, Any]]:
        """Overrides generic search. Returns results ONLY if it's a Spotify link resolver."""
        logger.info(f"Spotify async search for: {query}")

        # Only process URLs
        if "spotify.link" in query or "spoti.fi" in query:
            try:
                # Resolve short links
                async with httpx.AsyncClient() as client:
                    resp = await client.head(query, follow_redirects=True, timeout=5)
                    query = str(resp.url)
                    logger.info(f"Resolved Spotify short link to: {query}")
            except Exception as e:
                logger.warning(f"Failed to resolve spotify link {query}: {e}")

        url_match = re.search(
            r"(?:https?://)?(?:www\.)?(?:open\.spotify\.com/(?:intl-\w+/)?|spotify:)(track|artist|playlist|album)[:/]([a-zA-Z0-9_-]+)",
            query,
        )

        if url_match:
            resource_type, resource_id = url_match.groups()
            logger.info(f"Detected Spotify Async URL: type={resource_type}, id={resource_id}")

            if resource_type == "track":
                track = await self.get_track(resource_id)
                return [track] if track else []
            elif resource_type == "artist":
                try:
                    artist_data = await self._request("get", f"artists/{resource_id}")
                    if artist_data:
                        return [self._format_artist(artist_data)]
                except Exception:
                    pass
                return []
            elif resource_type == "playlist":
                try:
                    pl_data = await self._request("get", f"playlists/{resource_id}")
                    if pl_data:
                        return [self._format_playlist(pl_data)]
                except Exception:
                    pass
                return []
            elif resource_type == "album":
                try:
                    al_data = await self._request("get", f"albums/{resource_id}")
                    if al_data:
                        return [self._format_playlist(al_data, is_album=True)]
                except Exception:
                    pass
                return []

        # If not a link, we do NOT perform generic search anymore
        return []
