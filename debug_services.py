import re
import logging

# Mock logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_spotify_regex(query):
    print(f"Testing Spotify query: {query}")
    # Regex from spotify_service.py
    # Note: I'm copying the regex I saw in previous turns. 
    # It was: r'(?:open\.spotify\.com/|spotify:)(track|artist|playlist|album)[:/]([a-zA-Z0-9]+)'
    # But wait, the ID can be longer? Spotify IDs are base62, usually 22 chars.
    # Let's verify the regex strictly.
    regex = r'(?:open\.spotify\.com/|spotify:)(track|artist|playlist|album)[:/]([a-zA-Z0-9]+)'
    
    url_match = re.search(regex, query)
    if url_match:
        resource_type, resource_id = url_match.groups()
        print(f"MATCH: type={resource_type}, id={resource_id}")
    else:
        print("NO MATCH")

def test_youtube_regex(query):
    print(f"Testing YouTube query: {query}")
    # Regexes from youtube_service.py
    video_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', query)
    playlist_match = re.search(r'youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)', query)
    channel_match = re.search(r'youtube\.com/(?:channel/|@)([a-zA-Z0-9_-]+)', query)

    if video_match:
        print(f"VIDEO MATCH: id={video_match.group(1)}")
    
    if playlist_match:
        print(f"PLAYLIST MATCH: id={playlist_match.group(1)}")
        
    if channel_match:
        print(f"CHANNEL MATCH: id={channel_match.group(1)}")

if __name__ == "__main__":
    spotify_link = "https://open.spotify.com/playlist/5Qx92okDv8lmIyxL2W6qTG?si=ad84841305e94e03"
    test_spotify_regex(spotify_link)
    
    youtube_playlist_link = "https://www.youtube.com/playlist?list=PLD-9Kxp5j3xgi5mWJxSWoetle-b4UWmBp"
    test_youtube_regex(youtube_playlist_link)

    youtube_video_in_playlist = "https://www.youtube.com/watch?v=y7FBy4eIxig&list=PLD-9Kxp5j3xgi5mWJxSWoetle-b4UWmBp&pp=gAQB"
    test_youtube_regex(youtube_video_in_playlist)
