import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from app.core.config import settings
from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

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

    def search(self, query: str, limit: int = 20, offset: int = 0, type: str = 'track') -> List[Dict[str, Any]]:
        if not self.client:
            logger.warning("Spotify client not configured")
            return []
        
        logger.info(f"Spotify search query: {query}, type: {type}")
        
        from urllib.parse import unquote
        decoded_query = unquote(query)
        logger.info(f"Decoded query: {decoded_query}")
        
        url_match = re.search(r'(?:https?://)?(?:www\.)?(?:open\.spotify\.com/|spotify:)(track|artist|playlist|album)[:/]([a-zA-Z0-9_-]+)', decoded_query)
        if url_match:
            resource_type, resource_id = url_match.groups()
            logger.info(f"Detected Spotify URL: type={resource_type}, id={resource_id}")
            if resource_type == 'track':
                track = self.get_track(resource_id)
                return [track] if track else []
            elif resource_type == 'artist':
                try:
                    artist = self.client.artist(resource_id)
                    return [self._format_artist(artist)]
                except Exception:
                    return []
            elif resource_type == 'playlist':
                try:
                    playlist = self.client.playlist(resource_id)
                    return [self._format_playlist(playlist)]
                except Exception as e:
                    import traceback
                    logger.error(f"Error fetching Spotify playlist {resource_id}: {e}")
                    logger.error(traceback.format_exc())
                    return []
            elif resource_type == 'album':
                 try:
                    album = self.client.album(resource_id)
                    # Treat album as playlist for consistency in frontend if needed, or add _format_album
                    return [self._format_playlist(album, is_album=True)]
                 except Exception:
                    return []

        try:
            results = self.client.search(q=query, limit=limit, offset=offset, type=type)
        except Exception as e:
            logger.error(f"Spotify search error: {e}")
            return []
        items = []
        
        if 'tracks' in results:
            for item in results['tracks']['items']:
                items.append(self._format_track(item))
                
        if 'artists' in results:
            for item in results['artists']['items']:
                items.append(self._format_artist(item))

        if 'playlists' in results:
            for item in results['playlists']['items']:
                if not item: continue
                items.append(self._format_playlist(item))
            
        return items

    def _format_artist(self, item: Dict[str, Any]) -> Dict[str, Any]:
        image_url = item['images'][0]['url'] if item.get('images') else None
        return {
            "id": item['id'],
            "name": item['name'],
            "image_url": image_url,
            "source": "spotify",
            "type": "artist"
        }

    def _format_playlist(self, item: Dict[str, Any], is_album: bool = False) -> Dict[str, Any]:
        image_url = item['images'][0]['url'] if item.get('images') else None
        track_count = item.get('tracks', {}).get('total') if not is_album else item.get('total_tracks')
        return {
            "id": item['id'],
            "title": item['name'],
            "image_url": image_url,
            "source": "spotify",
            "type": "playlist",
            "track_count": track_count
        }

    def get_track(self, track_id: str) -> Dict[str, Any]:
        if not self.client:
            return None
            
        item = self.client.track(track_id)
        return self._format_track(item)

    def get_playlist_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        
        results = self.client.playlist_tracks(playlist_id)
        tracks = []
        for item in results['items']:
            if item['track']:
                tracks.append(self._format_track(item['track']))
        
        while results['next']:
            results = self.client.next(results)
            for item in results['items']:
                if item['track']:
                    tracks.append(self._format_track(item['track']))
                    
        return tracks

    def get_artist_top_tracks(self, artist_id: str) -> List[Dict[str, Any]]:
        if not self.client:
            return []
            
        results = self.client.artist_top_tracks(artist_id)
        return [self._format_track(track) for track in results['tracks']]

    def get_artist_albums(self, artist_id: str) -> List[Dict[str, Any]]:
        if not self.client:
            return []
            
        results = self.client.artist_albums(artist_id, album_type='album,single')
        albums = results['items']
        while results['next']:
            results = self.client.next(results)
            albums.extend(results['items'])
        return albums

    def get_album_tracks(self, album_id: str) -> List[Dict[str, Any]]:
        if not self.client:
            return []
            
        results = self.client.album_tracks(album_id)
        tracks = [self._format_track(track, album_obj=None) for track in results['items']] # Album tracks don't have album object inside
        while results['next']:
            results = self.client.next(results)
            tracks.extend([self._format_track(track, album_obj=None) for track in results['items']])
        return tracks

    def _format_track(self, item: Dict[str, Any], album_obj=None) -> Dict[str, Any]:
        # Handle simplified track object which might not have album
        album_name = "Unknown Album"
        image_url = None
        
        if 'album' in item:
            album_name = item['album']['name']
            if item['album'].get('images') and len(item['album']['images']) > 0:
                image_url = item['album']['images'][0]['url']
        elif album_obj:
             album_name = album_obj['name']
             if album_obj.get('images') and len(album_obj['images']) > 0:
                image_url = album_obj['images'][0]['url']

        return {
            "id": item['id'],
            "title": item['name'],
            "artist": ", ".join([artist['name'] for artist in item['artists']]),
            "artist_id": item['artists'][0]['id'] if item.get('artists') else None,
            "album": album_name,
            "duration_ms": item['duration_ms'],
            "image_url": image_url,
            "source": "spotify",
            "popularity": item.get('popularity', 0),
            "isrc": item.get('external_ids', {}).get('isrc')
        }
