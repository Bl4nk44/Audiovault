import re

def test_spotify_regex():
    patterns = [
        "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT?si=123",
        "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        "spotify:track:4cOdK2wGLETKBW3PvgPWqT",
        "https://open.spotify.com/artist/1Xyo4u8uXC1ZmMpatF05PJ?si=...",
        "https://open.spotify.com/playlist/5Qx92okDv8lmIyxL2W6qTG?si=ad84841305e94e03"
    ]
    
    regex = r'(?:open\.spotify\.com/|spotify:)(track|artist|playlist|album)[:/]([a-zA-Z0-9]+)'
    
    print("Testing Spotify Regex:")
    for url in patterns:
        match = re.search(regex, url)
        if match:
            print(f"MATCH: {url} -> Type: {match.group(1)}, ID: {match.group(2)}")
        else:
            print(f"NO MATCH: {url}")

def test_youtube_regex():
    patterns = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/playlist?list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj",
        "https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw",
        "https://www.youtube.com/@YouTube"
    ]
    
    video_regex = r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)'
    playlist_regex = r'youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)'
    channel_regex = r'youtube\.com/(?:channel/|@)([a-zA-Z0-9_-]+)'
    
    print("\nTesting YouTube Regex:")
    for url in patterns:
        v_match = re.search(video_regex, url)
        p_match = re.search(playlist_regex, url)
        c_match = re.search(channel_regex, url)
        
        if v_match:
            print(f"VIDEO MATCH: {url} -> ID: {v_match.group(1)}")
        elif p_match:
            print(f"PLAYLIST MATCH: {url} -> ID: {p_match.group(1)}")
        elif c_match:
            print(f"CHANNEL MATCH: {url} -> ID: {c_match.group(1)}")
        else:
            print(f"NO MATCH: {url}")

if __name__ == "__main__":
    test_spotify_regex()
    test_youtube_regex()
