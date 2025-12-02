import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from app.core.config import settings
from typing import List, Dict, Any

class SpotifyService:
    def __init__(self):
        if settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET:
            self.client = spotipy.Spotify(
                auth_manager=SpotifyClientCredentials(
                    client_id=settings.SPOTIFY_CLIENT_ID,
                    client_secret=settings.SPOTIFY_CLIENT_SECRET
                )
            )
        else:
            self.client = None

    def search(self, query: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        
        results = self.client.search(q=query, limit=limit, offset=offset, type='track')
        tracks = []
        
        for item in results['tracks']['items']:
            # Safe image extraction
            image_url = None
            if item.get('album') and item['album'].get('images') and len(item['album']['images']) > 0:
                image_url = item['album']['images'][0]['url']

            track = {
                "id": item['id'],
                "title": item['name'],
                "artist": ", ".join([artist['name'] for artist in item['artists']]),
                "album": item['album']['name'] if item.get('album') else "Unknown Album",
                "duration_ms": item['duration_ms'],
                "image_url": image_url,
                "source": "spotify",
                "popularity": item['popularity'],
                "isrc": item.get('external_ids', {}).get('isrc')
            }
            tracks.append(track)
            
        return tracks

    def get_track(self, track_id: str) -> Dict[str, Any]:
        if not self.client:
            return None
            
        item = self.client.track(track_id)
        return {
            "id": item['id'],
            "title": item['name'],
            "artist": ", ".join([artist['name'] for artist in item['artists']]),
            "album": item['album']['name'],
            "duration_ms": item['duration_ms'],
            "image_url": item['album']['images'][0]['url'] if item['album']['images'] else None,
            "source": "spotify",
            "popularity": item['popularity'],
            "isrc": item.get('external_ids', {}).get('isrc')
        }
