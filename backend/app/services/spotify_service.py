import logging
import re
from typing import Any

import spotipy
from app.core.config import settings
from spotipy.oauth2 import SpotifyClientCredentials

logger = logging.getLogger(__name__)


class SpotifyService:
    def __init__(self):
        if settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET:
            self.client = spotipy.Spotify(
                auth_manager=SpotifyClientCredentials(
                    client_id=settings.SPOTIFY_CLIENT_ID,
                    client_secret=settings.SPOTIFY_CLIENT_SECRET,
                )
            )
        else:
            self.client = None

    def search(self, query: str, limit: int = 20, offset: int = 0, type: str = "track") -> list[dict[str, Any]]:
        if not self.client:
            logger.warning("Spotify client not configured")
            return []

        logger.info(f"Spotify search query: {query}, type: {type}")

        # Handle short links / redirects first
        if "spotify.link" in query or "spoti.fi" in query:
            # We need to run async function in sync method (search is sync here? No, let's check)
            # Wait, SpotifyService.search is standard sync? Fastapi runs it in threadpool usually if not async def.
            # But let's check if we can make search async or use run_until_complete.
            # Usually standard def in FastAPI is run in threadpool.
            # We can use a loop runner.
            # Actually, it's better to just resolve it using requests or httpx sync if this is a sync method.
            # Checking file... it is `def search`.
            # Let's import requests for sync resolution for now to avoid async loop issues in threadpool,
            # or better yet, verify if we can make it async.
            # Most other services are async (DeezerService async def search). SpotifyService from legacy code is sync using spotipy.
            # Let's stick to sync resolution for SpotifyService for consistency.
            try:
                import requests

                resp = requests.head(query, allow_redirects=True, timeout=5)
                decoded_query = resp.url
                logger.info(f"Resolved Spotify short link to: {decoded_query}")
            except Exception as e:
                logger.warning(f"Failed to resolve spotify link {query}: {e}")
                decoded_query = query
        else:
            from urllib.parse import unquote

            decoded_query = unquote(query)

        logger.info(f"Decoded query: {decoded_query}")

        # Updated Regex to handle intl-xx and other variants
        # e.g. open.spotify.com/intl-pl/track/...
        # e.g. open.spotify.com/track/...
        url_match = re.search(
            r"(?:https?://)?(?:www\.)?(?:open\.spotify\.com/(?:intl-\w+/)?|spotify:)(track|artist|playlist|album)[:/]([a-zA-Z0-9_-]+)",
            decoded_query,
        )
        if url_match:
            resource_type, resource_id = url_match.groups()
            logger.info(f"Detected Spotify URL: type={resource_type}, id={resource_id}")
            if resource_type == "track":
                track = self.get_track(resource_id)
                return [track] if track else []
            elif resource_type == "artist":
                try:
                    artist = self.client.artist(resource_id)
                    return [self._format_artist(artist)]
                except Exception:
                    return []
            elif resource_type == "playlist":
                try:
                    playlist = self.client.playlist(resource_id)
                    return [self._format_playlist(playlist)]
                except Exception as e:
                    import traceback

                    logger.error(f"Error fetching Spotify playlist {resource_id}: {e}")
                    logger.error(traceback.format_exc())
                    return []
            elif resource_type == "album":
                try:
                    album = self.client.album(resource_id)
                    return [self._format_playlist(album, is_album=True)]
                except Exception:
                    return []

        try:
            results = self.client.search(q=query, limit=limit, offset=offset, type=type)
        except Exception as e:
            logger.error(f"Spotify search error: {e}")
            return []
        items = []

        if "tracks" in results:
            for item in results["tracks"]["items"]:
                items.append(self._format_track(item))

        if "artists" in results:
            for item in results["artists"]["items"]:
                items.append(self._format_artist(item))

        if "playlists" in results:
            for item in results["playlists"]["items"]:
                if not item:
                    continue
                items.append(self._format_playlist(item))

        return items

    def _format_artist(self, item: dict[str, Any]) -> dict[str, Any]:
        image_url = item["images"][0]["url"] if item.get("images") else None
        return {
            "id": item["id"],
            "name": item["name"],
            "image_url": image_url,
            "source": "spotify",
            "type": "artist",
        }

    def _format_playlist(self, item: dict[str, Any], is_album: bool = False) -> dict[str, Any]:
        image_url = item["images"][0]["url"] if item.get("images") else None
        track_count = item.get("tracks", {}).get("total") if not is_album else item.get("total_tracks")
        return {
            "id": item["id"],
            "title": item["name"],
            "image_url": image_url,
            "source": "spotify",
            "type": "playlist",
            "track_count": track_count,
        }

    def get_track(self, track_id: str) -> dict[str, Any]:
        if not self.client:
            return None

        item = self.client.track(track_id)
        return self._format_track(item)

    def get_playlist_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        if not self.client:
            return []

        results = self.client.playlist_tracks(playlist_id)
        tracks = []
        for item in results["items"]:
            if item["track"]:
                tracks.append(self._format_track(item["track"]))

        while results["next"]:
            results = self.client.next(results)
            for item in results["items"]:
                if item["track"]:
                    tracks.append(self._format_track(item["track"]))

        return tracks

    def get_playlist_details(self, playlist_id: str) -> dict[str, Any]:
        """
        Fetches full playlist details including metadata and all tracks.
        """
        if not self.client:
            return None

        try:
            # Get playlist metadata
            playlist = self.client.playlist(playlist_id)
            formatted_playlist = self._format_playlist(playlist)

            # Fetch all tracks (client.playlist only returns first 100)
            tracks = []
            results = playlist["tracks"]

            for item in results["items"]:
                if item.get("track"):
                    tracks.append(self._format_track(item["track"]))

            while results["next"]:
                results = self.client.next(results)
                for item in results["items"]:
                    if item.get("track"):
                        tracks.append(self._format_track(item["track"]))

            formatted_playlist["tracks"] = tracks
            return formatted_playlist

        except Exception as e:
            logger.error(f"Error fetching playlist details {playlist_id}: {e}")
            return None

    def get_artist_details(self, artist_id: str) -> dict[str, Any]:
        """
        Fetches full artist details including metadata, top tracks, and albums.
        """
        if not self.client:
            return None

        try:
            # 1. Get Artist Metadata
            artist = self.client.artist(artist_id)
            formatted_artist = self._format_artist(artist)

            # 2. Get Top Tracks
            top_tracks = self.get_artist_top_tracks(artist_id)
            formatted_artist["tracks"] = top_tracks

            # 3. Get Albums
            albums = self.get_artist_albums(artist_id)
            formatted_albums = []
            for album in albums:
                # Simplified album formatting for list
                image_url = album["images"][0]["url"] if album.get("images") else None
                formatted_albums.append(
                    {
                        "id": album["id"],
                        "title": album["name"],
                        "image_url": image_url,
                        "release_date": album["release_date"],
                        "total_tracks": album["total_tracks"],
                        "type": album["type"],
                    }
                )

            # De-duplicate albums by name (Spotify sometimes returns duplicates for different markets)
            unique_albums = []
            seen_names = set()
            for alb in formatted_albums:
                if alb["title"] not in seen_names:
                    unique_albums.append(alb)
                    seen_names.add(alb["title"])

            formatted_artist["albums"] = unique_albums
            return formatted_artist

        except Exception as e:
            logger.error(f"Error fetching artist details {artist_id}: {e}")
            return None

    def get_artist_top_tracks(self, artist_id: str) -> list[dict[str, Any]]:
        if not self.client:
            return []

        try:
            results = self.client.artist_top_tracks(artist_id)
            return [self._format_track(track) for track in results["tracks"]]
        except Exception as e:
            logger.error(f"Error fetching top tracks for {artist_id}: {e}")
            return []

    def get_artist_albums(self, artist_id: str) -> list[dict[str, Any]]:
        if not self.client:
            return []

        try:
            results = self.client.artist_albums(artist_id, album_type="album,single", limit=50)
            albums = results["items"]
            while results["next"]:
                results = self.client.next(results)
                albums.extend(results["items"])
            return albums
        except Exception as e:
            logger.error(f"Error fetching albums for {artist_id}: {e}")
            return []

    def get_album_tracks(self, album_id: str) -> list[dict[str, Any]]:
        if not self.client:
            return []

        try:
            results = self.client.album_tracks(album_id)
            tracks = [self._format_track(track, album_obj=None) for track in results["items"]]
            while results["next"]:
                results = self.client.next(results)
                tracks.extend([self._format_track(track, album_obj=None) for track in results["items"]])
            return tracks
        except Exception:
            return []

    def _format_track(self, item: dict[str, Any], album_obj=None) -> dict[str, Any]:
        # Handle simplified track object which might not have album
        album_name = "Unknown Album"
        image_url = None

        if "album" in item:
            album_name = item["album"]["name"]
            if item["album"].get("images") and len(item["album"]["images"]) > 0:
                image_url = item["album"]["images"][0]["url"]
        elif album_obj:
            album_name = album_obj["name"]
            if album_obj.get("images") and len(album_obj["images"]) > 0:
                image_url = album_obj["images"][0]["url"]

        return {
            "id": item["id"],
            "title": item["name"],
            "artist": ", ".join([artist["name"] for artist in item["artists"]]),
            "artist_id": item["artists"][0]["id"] if item.get("artists") else None,
            "album": album_name,
            "duration_ms": item["duration_ms"],
            "image_url": image_url,
            "source": "spotify",
            "popularity": item.get("popularity", 0),
            "isrc": item.get("external_ids", {}).get("isrc"),
        }
