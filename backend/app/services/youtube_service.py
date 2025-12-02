from ytmusicapi import YTMusic
from typing import List, Dict, Any

class YouTubeService:
    def __init__(self):
        self.yt = YTMusic()

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        results = self.yt.search(query, filter="songs", limit=limit)
        tracks = []
        
        for item in results:
            if item['resultType'] != 'song':
                continue
                
            artists = ", ".join([artist['name'] for artist in item['artists']])
            
            # Duration parsing (e.g. "3:45" -> ms)
            duration_str = item.get('duration', '0:00')
            parts = duration_str.split(':')
            if len(parts) == 2:
                duration_ms = (int(parts[0]) * 60 + int(parts[1])) * 1000
            elif len(parts) == 3:
                duration_ms = (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000
            else:
                duration_ms = 0
                
            track = {
                "id": item['videoId'],
                "title": item['title'],
                "artist": artists,
                "album": item['album']['name'] if item.get('album') else None,
                "duration_ms": duration_ms,
                "image_url": item['thumbnails'][-1]['url'] if item.get('thumbnails') else None,
                "source": "youtube",
                "popularity": 0, # Not available in search
                "isrc": None
            }
            tracks.append(track)
            
        return tracks
