import logging
import re
from typing import List, Dict, Any, Optional
import yt_dlp
import asyncio

logger = logging.getLogger(__name__)

class TidalService:
    def __init__(self):
        pass

    def can_handle(self, url: str) -> bool:
        return "tidal.com" in url

    async def get_tracks(self, url: str) -> List[Dict[str, Any]]:
        """
        Extract tracks from Tidal URL (Track, Album, or Playlist) using yt-dlp.
        """
        ydl_opts = {
            'extract_flat': True, # Fast extraction, no download
            'dump_single_json': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }

        try:
            logger.info(f"Extracting Tidal metadata from: {url}")
            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(
                None, 
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
            )

            if not info:
                logger.warning("No info extracted from Tidal URL")
                return []

            entries = info.get('entries', [])
            tracks = []

            # If it's a single track, entries might be empty but info contains the track
            if not entries and info.get('_type') != 'playlist':
                entries = [info]

            for entry in entries:
                if not entry: continue
                
                # data mapping
                title = entry.get('title')
                artist = entry.get('artist') or entry.get('uploader') or "Unknown Artist"
                
                if not title: continue

                track = {
                    "id": entry.get('id'),
                    "title": title,
                    "artist": artist,
                    "album": entry.get('album') or info.get('title', "Unknown Album"),
                    "duration_ms": int(entry.get('duration', 0) * 1000) if entry.get('duration') else None,
                    "image_url": entry.get('thumbnail'), 
                    "source": "tidal",
                    "source_url": entry.get('url') or entry.get('webpage_url') or url
                }
                tracks.append(track)
            
            logger.info(f"Extracted {len(tracks)} tracks from Tidal")
            return tracks

        except Exception as e:
            logger.error(f"Error extracting Tidal data: {e}")
            return []

    async def get_playlist_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract playlist info (title, image, id) from Tidal URL.
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

            if not info or info.get('_type') != 'playlist':
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
                "source": "tidal",
                "type": "playlist",
                "track_count": track_count
            }

        except Exception as e:
            logger.error(f"Error extracting Tidal playlist info: {e}")
            return None

tidal_service = TidalService()
