import pytest
from unittest.mock import MagicMock, patch
from app.services.youtube_service import YouTubeService

@pytest.fixture
def youtube_service():
    with patch("app.services.youtube_service.YTMusic") as mock_yt:
        service = YouTubeService()
        service.yt = mock_yt.return_value
        return service

def test_youtube_search_keywords(youtube_service):
    mock_results = [
        {
            "resultType": "song",
            "videoId": "vid1",
            "title": "Song Title",
            "artists": [{"name": "Artist Name"}],
            "album": {"name": "Album Name"},
            "duration": "3:45",
            "thumbnails": [{"url": "http://img.url"}]
        }
    ]
    youtube_service.yt.search.return_value = mock_results
    
    results = youtube_service.search("test song")
    assert len(results) == 1
    assert results[0]["title"] == "Song Title"
    assert results[0]["duration_ms"] == 225000

def test_youtube_search_url_video(youtube_service):
    mock_results = [
        {
            "videoId": "vid123",
            "title": "Video Title",
            "artists": [{"name": "A"}],
            "thumbnails": [{"url": "i"}]
        }
    ]
    youtube_service.yt.search.return_value = mock_results
    
    results = youtube_service.search("https://www.youtube.com/watch?v=vid123")
    assert len(results) == 1
    assert results[0]["id"] == "vid123"
    youtube_service.yt.search.assert_called()

def test_youtube_get_playlist_details(youtube_service):
    mock_pl = {
        "id": "pl_id",
        "title": "Playlist Title",
        "thumbnails": [{"url": "i"}],
        "tracks": [
            {
                "videoId": "v1",
                "title": "T1",
                "artists": [{"name": "A1"}],
                "duration": "1:00"
            }
        ],
        "trackCount": 1
    }
    youtube_service.yt.get_playlist.return_value = mock_pl
    
    details = youtube_service.get_playlist_details("pl_id")
    assert details["title"] == "Playlist Title"
    assert len(details["tracks"]) == 1
    assert details["tracks"][0]["id"] == "v1"

def test_youtube_format_duration(youtube_service):
    # Test 3 parts
    item = {"videoId": "v", "title": "T", "duration": "1:01:01"}
    formatted = youtube_service._format_track(item)
    assert formatted["duration_ms"] == (3600 + 60 + 1) * 1000
    
    # Test 2 parts
    item = {"videoId": "v", "title": "T", "duration": "10:00"}
    formatted = youtube_service._format_track(item)
    assert formatted["duration_ms"] == 600 * 1000
