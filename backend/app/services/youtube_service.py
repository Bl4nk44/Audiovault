from ytmusicapi import YTMusic
from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

class YouTubeService:
    def __init__(self):
        self.yt = YTMusic()

    def search(self, query: str, limit: int = 20, type: str = 'song') -> List[Dict[str, Any]]:
        logger.info(f"YouTube search query: {query}, type: {type}")
        
        # Check for YouTube URLs
        video_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', query)
        # Match list parameter in any YouTube URL (e.g. watch?v=...&list=... or playlist?list=...)
        playlist_match = re.search(r'[?&]list=([a-zA-Z0-9_-]+)', query)
        channel_match = re.search(r'youtube\.com/(?:channel/|@)([a-zA-Z0-9_-]+)', query)

        if video_match and (type == 'song' or type == 'track' or not playlist_match):
            # Only return video if type matches or is generic
            if type not in ['song', 'track', 'all']:
                pass
            else:
                video_id = video_match.group(1)
                try:
                    # Fallback: search for video ID usually works and returns song result
                    results = self.yt.search(video_id, filter="songs", limit=1)
                    if results:
                        return [self._format_track(results[0])]
                except Exception:
                    pass
        
        if playlist_match:
            # Only return playlist if type matches
            if type not in ['playlist', 'all']:
                pass
            else:
                playlist_id = playlist_match.group(1)
                try:
                    playlist = self.yt.get_playlist(playlist_id)
                    image_url = playlist['thumbnails'][-1]['url'] if playlist.get('thumbnails') else None
                    return [{
                        "id": playlist['id'],
                        "title": playlist['title'],
                        "image_url": image_url,
                        "source": "youtube",
                        "type": "playlist",
                        "track_count": playlist.get('trackCount', 0)
                    }]
                except Exception as e:
                    logger.error(f"Error fetching YouTube playlist {playlist_id}: {e}")
                    pass

        if channel_match:
             # Only return artist/channel if type matches
            if type not in ['artist', 'all']:
                pass
            else:
                channel_id = channel_match.group(1)
                if query.startswith('http') or 'youtube.com' in query:
                     try:
                        if channel_id.startswith('UC'):
                            artist = self.yt.get_artist(channel_id)
                            image_url = artist['thumbnails'][-1]['url'] if artist.get('thumbnails') else None
                            return [{
                                "id": artist['browseId'],
                                "name": artist['name'],
                                "image_url": image_url,
                                "source": "youtube",
                                "type": "artist"
                            }]
                     except Exception:
                        pass

        # Map frontend types to ytmusicapi filter types
        yt_filter = "songs"
        if type == 'artist':
            yt_filter = "artists"
        elif type == 'playlist':
            yt_filter = "community_playlists"
            
        results = self.yt.search(query, filter=yt_filter, limit=limit)
        items = []
        
        for item in results:
            if item['resultType'] == 'song':
                items.append(self._format_track(item))
            elif item['resultType'] == 'artist':
                image_url = item['thumbnails'][-1]['url'] if item.get('thumbnails') else None
                items.append({
                    "id": item['browseId'],
                    "name": item['artist'],
                    "image_url": image_url,
                    "source": "youtube",
                    "type": "artist"
                })
            elif item['resultType'] == 'playlist':
                image_url = item['thumbnails'][-1]['url'] if item.get('thumbnails') else None
                items.append({
                    "id": item['browseId'],
                    "title": item['title'],
                    "image_url": image_url,
                    "source": "youtube",
                    "type": "playlist",
                    "track_count": int(item.get('itemCount', 0)) if isinstance(item.get('itemCount'), (int, str)) else 0
                })
                
        return items

    def get_playlist_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        try:
            import yt_dlp
            ydl_opts = {
                'extract_flat': True,
                'quiet': True,
                'no_warnings': True,
            }
            url = f"https://www.youtube.com/playlist?list={playlist_id}"
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            tracks = []
            if 'entries' in info:
                for item in info['entries']:
                    # yt-dlp flat extraction returns basic info
                    tracks.append({
                        "id": item.get('id'),
                        "title": item.get('title'),
                        "artist": item.get('uploader'), # Use uploader as artist
                        "album": info.get('title'), # Use playlist title as album
                        "duration_ms": int(item.get('duration', 0) * 1000) if item.get('duration') else 0,
                        "image_url": None, # Flat extraction might not have thumbnails
                        "source": "youtube",
                        "popularity": 0,
                        "isrc": None
                    })
            return tracks
        except Exception as e:
            logger.error(f"Error fetching YouTube playlist {playlist_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def get_artist_tracks(self, channel_id: str) -> List[Dict[str, Any]]:
        try:
            artist = self.yt.get_artist(channel_id)
            tracks = []
            if 'songs' in artist and 'browseId' in artist['songs']:
                 songs_playlist = self.yt.get_playlist(artist['songs']['browseId'])
                 for item in songs_playlist.get('tracks', []):
                    tracks.append(self._format_track(item))
            return tracks
        except Exception:
            return []

    def _format_track(self, item: Dict[str, Any], album_name=None) -> Dict[str, Any]:
        artists = ", ".join([artist['name'] for artist in item.get('artists', [])])
        
        duration_ms = 0
        if 'duration_seconds' in item:
             duration_ms = item['duration_seconds'] * 1000
        elif 'duration' in item:
            duration_str = item.get('duration', '0:00')
            parts = duration_str.split(':')
            if len(parts) == 2:
                duration_ms = (int(parts[0]) * 60 + int(parts[1])) * 1000
            elif len(parts) == 3:
                duration_ms = (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000

        image_url = None
        if item.get('thumbnails'):
             image_url = item['thumbnails'][-1]['url']

        return {
            "id": item['videoId'],
            "title": item['title'],
            "artist": artists,
            "album": item.get('album', {}).get('name') if item.get('album') else album_name,
            "duration_ms": duration_ms,
            "image_url": image_url,
            "source": "youtube",
            "popularity": 0,
            "isrc": None
        }
