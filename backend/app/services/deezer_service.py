import logging
import re
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class DeezerService:
    BASE_URL = "https://api.deezer.com"

    def __init__(self):
        pass

    async def search(self, query: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        # Resolve short links (deezer.page.link)
        if (
            "deezer.page.link" in query or "deezer.com" in query
        ):  # check generic deezer too just in case of weird redirects
            from app.utils.url_helper import resolve_redirects

            if "page.link" in query:
                resolved = await resolve_redirects(query)
                if resolved != query:
                    logger.info(f"Resolved Deezer short link to: {resolved}")
                    query = resolved

        # Check if query is a URL
        url_match = re.search(
            r"(?:https?://)?(?:www\.)?deezer\.com/(?:\w{2}/)?(track|album|playlist)/(\d+)",
            query,
        )
        if url_match:
            kind, id = url_match.groups()
            logger.info(f"Detected Deezer URL: kind={kind}, id={id}")
            if kind == "track":
                track = await self.get_track(id)
                return [track] if track else []
            elif kind == "album":
                return await self.get_album_tracks(id)
            elif kind == "playlist":
                return await self.get_playlist_tracks(id)

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.BASE_URL}/search",
                params={"q": query, "limit": limit, "index": offset},
            ) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                tracks = []

                for item in data.get("data", []):
                    tracks.append(self._format_track(item))

                return tracks

    async def get_track(self, track_id: str) -> dict[str, Any] | None:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.BASE_URL}/track/{track_id}") as response:
                if response.status != 200:
                    return None
                data = await response.json()
                if "error" in data:
                    return None
                return self._format_track(data)

    async def get_album_tracks(self, album_id: str) -> list[dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.BASE_URL}/album/{album_id}/tracks", params={"limit": 500}) as response:
                if response.status != 200:
                    return []
                data = await response.json()
                # Need to fetch album info for cover if not in tracks
                # Unlike Search, Album Tracks endpoint often returns simplified objects
                # But usually contains fallback cover/album info.

                tracks = []
                for item in data.get("data", []):
                    # Album endpoint tracks might NOT represent album object fully,
                    # but usually we want to preserve the album context from the parent call if possible.
                    # For simplicty, _format_track handles what it can.
                    tracks.append(self._format_track(item))
                return tracks

    async def get_playlist_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.BASE_URL}/playlist/{playlist_id}/tracks", params={"limit": 500}) as response:
                if response.status != 200:
                    return []
                data = await response.json()
                tracks = []
                for item in data.get("data", []):
                    tracks.append(self._format_track(item))
                return tracks

    async def get_playlist_details(self, playlist_id: str) -> dict[str, Any] | None:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.BASE_URL}/playlist/{playlist_id}") as response:
                if response.status != 200:
                    return None
                data = await response.json()
                if "error" in data:
                    return None

                tracks = []
                # Playlist details response usually contains 'tracks' -> 'data'
                if "tracks" in data and "data" in data["tracks"]:
                    for item in data["tracks"]["data"]:
                        tracks.append(self._format_track(item))

                return {
                    "id": str(data["id"]),
                    "title": data["title"],
                    "description": data.get("description", ""),
                    "image_url": data.get("picture_medium") or data.get("picture_big") or data.get("picture"),
                    "source": "deezer",
                    "author": data.get("creator", {}).get("name"),
                    "tracks": tracks,
                }

    async def get_artist_details(self, artist_id: str) -> dict[str, Any] | None:
        async with aiohttp.ClientSession() as session:
            # 1. Get Artist Info
            async with session.get(f"{self.BASE_URL}/artist/{artist_id}") as response:
                if response.status != 200:
                    return None
                artist = await response.json()
                if "error" in artist:
                    return None

            # 2. Get Top Tracks
            top_tracks = []
            async with session.get(f"{self.BASE_URL}/artist/{artist_id}/top", params={"limit": 10}) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get("data", []):
                        top_tracks.append(self._format_track(item))

            # 3. Get Albums
            albums = []
            async with session.get(f"{self.BASE_URL}/artist/{artist_id}/albums", params={"limit": 20}) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get("data", []):
                        albums.append(
                            {
                                "id": str(item["id"]),
                                "title": item["title"],
                                "image_url": item.get("cover_medium") or item.get("cover_big"),
                                "year": item.get("release_date", "")[:4] if item.get("release_date") else None,
                                "source": "deezer",
                            }
                        )

            return {
                "id": str(artist["id"]),
                "name": artist["name"],
                "image_url": artist.get("picture_medium") or artist.get("picture_big"),
                "genres": [],  # Deezer doesn't easily expose genres in this view
                "top_tracks": top_tracks,
                "albums": albums,
                "source": "deezer",
            }

    def _format_track(self, item: dict[str, Any]) -> dict[str, Any]:
        # Safe image extraction
        image_url = None
        album_name = "Unknown Album"

        if item.get("album"):
            album_name = item["album"].get("title", "Unknown Album")
            if item["album"].get("cover_medium"):
                image_url = item["album"]["cover_medium"]
            elif item["album"].get("cover_big"):
                image_url = item["album"]["cover_big"]
            elif item["album"].get("cover"):
                image_url = item["album"]["cover"]

        # Sometimes 'artist' is just a name string in some simplified responses?
        # Usually it is an object
        artist_name = "Unknown Artist"
        if isinstance(item.get("artist"), dict):
            artist_name = item["artist"].get("name", "Unknown Artist")
        elif isinstance(item.get("artist"), str):
            artist_name = item.get("artist") or "Unknown Artist"

        return {
            "id": str(item["id"]),
            "title": item["title"],
            "artist": artist_name,
            "album": album_name,
            "duration_ms": int(item["duration"]) * 1000,
            "image_url": image_url,
            "source": "deezer",
            "popularity": item.get("rank", 0),
            "isrc": item.get("isrc"),
        }


deezer_service = DeezerService()
