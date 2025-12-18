import logging
import re
from typing import List, Dict, Any, Optional
import yt_dlp
import asyncio

logger = logging.getLogger(__name__)

class AppleMusicService:
    def __init__(self):
        pass

    def can_handle(self, url: str) -> bool:
        return "music.apple.com" in url or "apple.co" in url

    async def get_tracks(self, url: str) -> List[Dict[str, Any]]:
        """
        Extract tracks from Apple Music URL (Song, Album, or Playlist) using yt-dlp.
        yt-dlp supports apple music scraping beautifully.
        """
        ydl_opts = {
            'extract_flat': True, # Fast extraction, no download
            'dump_single_json': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }

        try:
            # Resolve short links
            if "apple.co" in url:
                from app.utils.url_helper import resolve_redirects
                url = await resolve_redirects(url)
                logger.info(f"Resolved Apple Music short link to: {url}")

            logger.info(f"Extracting Apple Music metadata from: {url}")
            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(
                None, 
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
            )

            if not info:
                logger.warning("No info extracted from Apple Music URL")
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
                    "id": entry.get('id'), # This might be internal yt-dlp id or actual apple id
                    "title": title,
                    "artist": artist,
                    "album": entry.get('album') or info.get('title', "Unknown Album"), # Fallback to playlist/album title
                    "duration_ms": int(entry.get('duration', 0) * 1000) if entry.get('duration') else None,
                    "image_url": entry.get('thumbnail'), # yt-dlp usually scrapes the artwork
                    "source": "apple_music",
                    "source_url": entry.get('url') or entry.get('webpage_url') or url
                }
                tracks.append(track)
            
            logger.info(f"Extracted {len(tracks)} tracks from Apple Music")
            return tracks

        except Exception as e:
            logger.error(f"Error extracting Apple Music data: {e}")
            return []
    async def get_playlist_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract playlist info (title, image, id) from Apple Music URL.
        Returns a dict suitable for frontend PlaylistCard.
        """
        ydl_opts = {
            'extract_flat': True,
            'dump_single_json': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'playlist_items': '1', # Only fetch first item to get playlist metadata quickly? 
            # Actually flat extraction gets metadata without items if supported.
        }

        try:
            if "apple.co" in url:
                from app.utils.url_helper import resolve_redirects
                url = await resolve_redirects(url)

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
            
            # Count tracks if available
            track_count = info.get('playlist_count')
            if not track_count and info.get('entries'):
                track_count = len(info['entries'])

            return {
                "id": url, # Use URL as ID for generic providers
                "title": info.get('title', "Unknown Playlist"),
                "image_url": image_url,
                "source": "apple_music",
                "type": "playlist",
                "track_count": track_count
            }

        except Exception as e:
            logger.error(f"Error extracting Apple Music playlist info: {e}")
            return None

apple_music_service = AppleMusicService()
