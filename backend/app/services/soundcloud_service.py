import logging
from typing import List, Dict, Any, Optional
import yt_dlp
import asyncio

logger = logging.getLogger(__name__)

class SoundCloudService:
    def __init__(self):
        pass

    def can_handle(self, url: str) -> bool:
        return "soundcloud.com" in url or "on.soundcloud.com" in url

    async def get_tracks(self, url: str) -> List[Dict[str, Any]]:
        """
        Extract tracks from SoundCloud URL using yt-dlp.
        SoundCloud is well supported by yt-dlp.
        """
        ydl_opts = {
            'extract_flat': True, 
            'dump_single_json': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }

        try:
            logger.info(f"Extracting SoundCloud metadata from: {url}")
            
            # Resolve short links
            if "on.soundcloud.com" in url:
                from app.utils.url_helper import resolve_redirects
                url = await resolve_redirects(url)
                logger.info(f"Resolved SoundCloud short link to: {url}")

            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(
                None, 
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
            )

            if not info:
                logger.warning("No info extracted from SoundCloud URL")
                return []

            entries = info.get('entries', [])
            tracks = []

            # If it's a single track, entries might be empty but info contains the track
            if not entries and info.get('_type') != 'playlist':
                entries = [info]

            for entry in entries:
                if not entry: continue
                
                # SoundCloud specific: id usually exists
                track_id = entry.get('id')
                title = entry.get('title')
                uploader = entry.get('uploader') or entry.get('artist') or "Unknown Artist"
                
                if not title: continue

                # For SoundCloud, web_url or url is critical for direct download
                source_url = entry.get('webpage_url') or entry.get('url') or url

                track = {
                    "id": str(track_id) if track_id else None,
                    "title": title,
                    "artist": uploader,
                    "album": "SoundCloud", # SoundCloud rarely has albums in typical sense
                    "duration_ms": int(entry.get('duration', 0) * 1000) if entry.get('duration') else None,
                    "image_url": entry.get('thumbnail'), 
                    "source": "soundcloud",
                    "source_url": source_url
                }
                tracks.append(track)
            
            logger.info(f"Extracted {len(tracks)} tracks from SoundCloud")
            return tracks

        except Exception as e:
            logger.error(f"Error extracting SoundCloud data: {e}")
            return []

    async def get_playlist_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract playlist info (title, image, id) from SoundCloud URL.
        """
        ydl_opts = {
            'extract_flat': True,
            'dump_single_json': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'playlist_items': '1', 
        }

        try:
            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(
                None, 
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
            )

            if not info:
                return None
            
            # SoundCloud specific: check if it's a set or user (user can be playlist-like)
            if info.get('_type') != 'playlist' and '/sets/' not in url:
                # If it's a single track, we might not want to treat it as a playlist container
                # UNLESS the user pasted a track URL and expects it to be added as a "watched track"?
                # Current Watchlist logic supports "playlist", "artist", "channel".
                # For now, let's only support sets as playlists.
                return None

            image_url = None
            if info.get('thumbnails'):
                image_url = info['thumbnails'][-1]['url']
            
            track_count = info.get('playlist_count')
            if not track_count and info.get('entries'):
                track_count = len(info['entries'])

            return {
                "id": url, 
                "title": info.get('title', "Unknown Playlist"),
                "image_url": image_url,
                "source": "soundcloud",
                "type": "playlist",
                "track_count": track_count
            }

        except Exception as e:
            logger.error(f"Error extracting SoundCloud playlist info: {e}")
            return None

soundcloud_service = SoundCloudService()
