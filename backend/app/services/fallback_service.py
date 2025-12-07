import logging
import random
from typing import Optional, List
from app.models.track import Track

logger = logging.getLogger(__name__)

class FallbackService:
    def __init__(self):
        self.invidious_instances = [
            "https://inv.tux.pizza",
            "https://invidious.jing.rocks",
            "https://vid.puffyan.us",
            "https://invidious.nerdvpn.de"
        ]
    
    def get_search_query(self, track: Track, attempt: int = 1) -> str:
        """
        Generate search query variations based on attempt number.
        """
        base_query = f"{track.artist} - {track.title}"
        
        strategies = [
            f"{base_query}",                        # Standard
            f"{base_query} audio",                  # Force audio
            f"{base_query} official audio",         # Official
            f"{base_query} lyrics",                 # Lyrics video (often good audio)
            f"{track.title} {track.artist}",        # Reversed
        ]
        
        index = (attempt - 1) % len(strategies)
        return strategies[index]

    def get_proxy_url(self, original_url: str) -> Optional[str]:
        """
        Transform a YouTube URL to use an Invidious instance (basic proxy bypass).
        This is a naïve implementation for "bypassing blocks".
        """
        if "youtube.com" in original_url or "youtu.be" in original_url:
            # Extract video ID (naive)
            try:
                if "v=" in original_url:
                    vid_id = original_url.split("v=")[1].split("&")[0]
                else:
                    vid_id = original_url.split("/")[-1]
                
                instance = random.choice(self.invidious_instances)
                return f"{instance}/watch?v={vid_id}"
            except Exception:
                return None
        return None

fallback_service = FallbackService()
