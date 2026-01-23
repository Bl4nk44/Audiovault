import logging
import re
from typing import Any

from app.services.base_music_service import BaseMusicService
from ytmusicapi import YTMusic

logger = logging.getLogger(__name__)


class YouTubeService(BaseMusicService):
    def __init__(self):
        super().__init__()
        self.yt = YTMusic()
        self.source_name = "youtube"

    def search(self, query: str, limit: int = 20, type: str = "song") -> list[dict[str, Any]]:
        logger.info(f"YouTube search query: {query}, type: {type}")

        # Regex matching
        video_match = re.search(
            r"(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/|music\.youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)",
            query,
        )
        playlist_match = re.search(r"[?&]list=([a-zA-Z0-9_-]+)", query)
        channel_match = re.search(
            r"(?:youtube\.com|music\.youtube\.com)/(?:channel/|@)([a-zA-Z0-9_-]+)",
            query,
        )

        # 1. Video Search Priority
        if video_match and (type in ["song", "track", "all"]) and not playlist_match:
            res = self._search_video(video_match.group(1))
            if res:
                return res

        # 2. Playlist Search Priority
        if playlist_match and (type in ["playlist", "all"]):
            res = self._search_playlist(playlist_match.group(1))
            if res:
                return res

        # 3. Channel Search Priority
        if channel_match and (type in ["artist", "all"]):
            # Additional check to ensuring it looks like a URL if strictly matching regex
            if query.startswith("http") or "youtube.com" in query:
                res = self._search_channel(channel_match.group(1))
                if res:
                    return res

        # 4. Keyword Search (Fallback)
        return self._search_keywords(query, limit, type)

    def _search_video(self, video_id: str) -> list[dict[str, Any]]:
        try:
            results = self.yt.search(video_id, filter="songs", limit=1)
            if results:
                return [self._format_track(results[0])]
        except Exception as e:
            logger.warning(f"Error fetching video details for {video_id}: {e}")
            return []
        return []

    def _search_playlist(self, playlist_id: str) -> list[dict[str, Any]]:
        try:
            playlist = self.yt.get_playlist(playlist_id)
            image_url = playlist["thumbnails"][-1]["url"] if playlist.get("thumbnails") else None
            return [
                {
                    "id": playlist["id"],
                    "title": playlist["title"],
                    "image_url": image_url,
                    "source": "youtube",
                    "type": "playlist",
                    "track_count": playlist.get("trackCount", 0),
                }
            ]
        except Exception as e:
            logger.error(f"Error fetching YouTube playlist {playlist_id}: {e}")
        return []

    def _search_channel(self, channel_id: str) -> list[dict[str, Any]]:
        try:
            if channel_id.startswith("UC"):
                artist = self.yt.get_artist(channel_id)
                image_url = artist["thumbnails"][-1]["url"] if artist.get("thumbnails") else None
                return [
                    {
                        "id": artist["browseId"],
                        "name": artist["name"],
                        "image_url": image_url,
                        "source": "youtube",
                        "type": "artist",
                    }
                ]
        except Exception as e:
            logger.warning(f"Error fetching channel details {channel_id}: {e}")
        return []

    def _search_keywords(self, query: str, limit: int, type: str) -> list[dict[str, Any]]:
        # Map frontend types to ytmusicapi filter types
        yt_filter = "songs"
        if type == "artist":
            yt_filter = "artists"
        elif type == "playlist":
            yt_filter = "community_playlists"

        try:
            results = self.yt.search(query, filter=yt_filter, limit=limit)
        except Exception as e:
            logger.error(f"Error searching YouTube keywords: {e}")
            return []

        return [item for item in (self._map_search_result(r) for r in results) if item]

    def _map_search_result(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """Maps a YouTube search result to a unified format."""
        result_type = item.get("resultType")

        if result_type == "song":
            return self._format_track(item)

        if result_type == "artist":
            return {
                "id": item["browseId"],
                "name": item["artist"],
                "image_url": item["thumbnails"][-1]["url"] if item.get("thumbnails") else None,
                "source": "youtube",
                "type": "artist",
            }

        if result_type == "playlist":
            track_count = item.get("itemCount", 0)
            if not isinstance(track_count, (int, float)):  # handle string cases cleanly
                track_count = int(track_count) if isinstance(track_count, str) and track_count.isdigit() else 0

            return {
                "id": item["browseId"],
                "title": item["title"],
                "image_url": item["thumbnails"][-1]["url"] if item.get("thumbnails") else None,
                "source": "youtube",
                "type": "playlist",
                "track_count": int(track_count),
            }

        return None

    # get_playlist_tracks removed as it duplicated BaseMusicService logic
    # and was likely unused or can be replaced by base.

    def get_artist_tracks(self, channel_id: str) -> list[dict[str, Any]]:
        try:
            artist = self.yt.get_artist(channel_id)
            tracks = []
            if "songs" in artist and "browseId" in artist["songs"]:
                songs_playlist = self.yt.get_playlist(artist["songs"]["browseId"])
                for item in songs_playlist.get("tracks", []):
                    tracks.append(self._format_track(item))
            return tracks
        except Exception:
            return []

    def get_playlist_details(self, playlist_id: str, limit: int = 100) -> dict[str, Any] | None:
        """
        Fetches full playlist details including metadata and tracks.
        """
        try:
            # Get playlist details (ytmusicapi returns tracks by default in get_playlist)
            playlist = self.yt.get_playlist(playlist_id, limit=limit)

            image_url = playlist["thumbnails"][-1]["url"] if playlist.get("thumbnails") else None

            tracks = []
            if "tracks" in playlist:
                for item in playlist["tracks"]:
                    tracks.append(self._format_track(item, album_name=playlist.get("title")))

            return {
                "id": playlist["id"],
                "title": playlist["title"],
                "description": playlist.get("description"),
                "image_url": image_url,
                "source": "youtube",
                "type": "playlist",
                "track_count": playlist.get("trackCount", len(tracks)),
                "tracks": tracks,
            }
        except Exception as e:
            logger.error(f"Error fetching YouTube playlist details {playlist_id}: {e}")
            return None

    def _format_track(self, item: dict[str, Any], album_name=None) -> dict[str, Any]:
        artists = ", ".join([artist["name"] for artist in item.get("artists", [])])

        duration_ms = 0
        if "duration_seconds" in item:
            duration_ms = int(item["duration_seconds"]) * 1000
        elif "duration" in item:
            duration_str = item.get("duration", "0:00")
            if duration_str:  # Handle None/empty string safe
                parts = duration_str.split(":")
                if len(parts) == 2:
                    duration_ms = (int(parts[0]) * 60 + int(parts[1])) * 1000
                elif len(parts) == 3:
                    duration_ms = (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000

        image_url = None
        if item.get("thumbnails"):
            image_url = item["thumbnails"][-1]["url"]

        return {
            "id": item["videoId"],
            "title": item["title"],
            "artist": artists,
            "album": item.get("album", {}).get("name") if item.get("album") else album_name,
            "duration_ms": duration_ms,
            "image_url": image_url,
            "source": "youtube",
            "popularity": 0,
            "isrc": None,
        }
