import logging

logger = logging.getLogger(__name__)

class FallbackService:
    def __init__(self):
        self.invidious_instances = [
            "https://inv.tux.pizza",
            "https://invidious.jing.rocks",
            "https://vid.puffyan.us",
            "https://invidious.nerdvpn.de"
        ]
    
    
    def get_fallback_instruction(self, download_source: str, attempt: int, track_metadata) -> dict:
        """
        Determine the next download strategy based on the source service and retry attempt.
        Returns a dict with 'type' (yt_search, sc_search, direct, proxy) and 'query'/'url'.
        """
        # Determine strategy based on source
        # Strategy Matrix from plan:
        # Spotify/Apple/Tidal/Deezer/Amazon:
        # 1. YT Search "Artist - Title official"
        # 2. YT Search "Artist - Title audio"
        # 3. SC Search "Artist - Title" (Cross-platform)
        # 4. YT Search "Artist - Title" (Last resort)
        
        # YouTube:
        # 1. Direct
        # 2. Invidious Proxy
        # 3. SC Search (if song)
        
        # SoundCloud:
        # 1. Direct
        # 2. SC Search
        # 3. YT Search
        
        artist = track_metadata.artist if track_metadata else "Unknown"
        title = track_metadata.title if track_metadata else "Unknown"
        base_query = f"{artist} - {title}"
        
        instruction = {"type": "none", "value": None}

        if download_source in ['spotify', 'apple_music', 'tidal', 'deezer', 'amazon_music', 'imported']:
            if attempt == 1:
                instruction = {"type": "yt_search", "value": f"{base_query} official video"}
            elif attempt == 2:
                # Slight variation, audio focus
                instruction = {"type": "yt_search", "value": f"{base_query} audio"}
            elif attempt == 3:
                # Cross-platform: SoundCloud
                instruction = {"type": "sc_search", "value": base_query}
            elif attempt == 4:
                # Last resort generic YT
                instruction = {"type": "yt_search", "value": base_query}
                
        elif download_source == 'youtube':
            # Logic for YouTube is slightly different because we start with a URL usually, 
            # but DownloadManager calls _resolve_url which generally handles the "Direct" part first.
            # Retry count 0 -> Direct (handled in manager default)
            # Retry count 1 -> Attempt 2 in our logic here (since attempt = retry_count + 1)
            
            # Note: In Manager, attempt 1 is the first retry? No, attempt = retry_count + 1.
            # So retry_count 0 is attempt 1.
            # For YT, Attempt 1 is actually the first run (Direct). 
            # If we are here, likely Manager failed Direct and is retrying.
            
            # Wait, manager calls _resolve_url at start too.
            # For YT, attempt 1 should be direct URL (handled by manager if returning URL).
            # So if we return None, manager might use original? 
            # In Manager: if download.source == "youtube": returns URL.
            # We need to change Manager to use this service properly.
            
            if attempt == 1:
                # Should be direct, handled by manager usually, but let's be explicit
                instruction = {"type": "direct_youtube", "value": None} 
            elif attempt == 2:
                # Cross-platform SC as fallback
                instruction = {"type": "sc_search", "value": base_query}
            elif attempt == 3:
                # Final generic search
                instruction = {"type": "yt_search", "value": base_query}
                
        elif download_source == 'soundcloud':
            if attempt == 1:
                instruction = {"type": "direct_soundcloud", "value": None}
            elif attempt == 2:
                instruction = {"type": "sc_search", "value": base_query}
            elif attempt == 3:
                instruction = {"type": "yt_search", "value": base_query}
                
        return instruction



fallback_service = FallbackService()
