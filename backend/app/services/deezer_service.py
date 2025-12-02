import aiohttp
from typing import List, Dict, Any

class DeezerService:
    BASE_URL = "https://api.deezer.com"

    async def search(self, query: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.BASE_URL}/search", params={"q": query, "limit": limit, "index": offset}) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                tracks = []
                
                for item in data.get('data', []):
                    # Safe image extraction
                    image_url = None
                    if item.get('album') and item['album'].get('cover_medium'):
                        image_url = item['album']['cover_medium']
                    elif item.get('album') and item['album'].get('cover_big'):
                         image_url = item['album']['cover_big']

                    track = {
                        "id": str(item['id']),
                        "title": item['title'],
                        "artist": item['artist']['name'],
                        "album": item['album']['title'] if item.get('album') else "Unknown Album",
                        "duration_ms": item['duration'] * 1000,
                        "image_url": image_url,
                        "source": "deezer",
                        "popularity": item.get('rank', 0),
                        "isrc": None # Need detailed track info for ISRC usually
                    }
                    tracks.append(track)
                    
                return tracks
