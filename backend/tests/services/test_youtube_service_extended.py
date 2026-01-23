"""
Extended tests for YouTubeService to increase code coverage.
Covers: search with URLs, video/playlist/channel lookup, format mappings.
"""

from unittest.mock import MagicMock, patch

import pytest
from app.services.youtube_service import YouTubeService


@pytest.fixture
def youtube_service():
    """Create YouTubeService with mocked YTMusic client."""
    with patch("app.services.youtube_service.YTMusic"):
        service = YouTubeService()
        mock_client = MagicMock()
        service.yt = mock_client
        return service


# =============================================================================
# Search - URL Detection
# =============================================================================


def test_youtube_search_video_url(youtube_service):
    """Test search with YouTube video URL."""
    mock_result = [
        {
            "videoId": "abc123",
            "title": "Test Video",
            "artists": [{"name": "Artist"}],
            "thumbnails": [{"url": "http://img"}],
            "duration": "3:45",
        }
    ]
    youtube_service.yt.search.return_value = mock_result

    results = youtube_service.search("https://youtube.com/watch?v=abc123")

    assert len(results) == 1
    assert results[0]["id"] == "abc123"


def test_youtube_search_youtu_be_url(youtube_service):
    """Test search with youtu.be short URL."""
    mock_result = [
        {
            "videoId": "xyz789",
            "title": "Short URL Video",
            "artists": [{"name": "Artist"}],
            "thumbnails": [{"url": "http://img"}],
            "duration": "2:30",
        }
    ]
    youtube_service.yt.search.return_value = mock_result

    results = youtube_service.search("https://youtu.be/xyz789")

    assert len(results) == 1


def test_youtube_search_music_url(youtube_service):
    """Test search with music.youtube.com URL."""
    mock_result = [
        {
            "videoId": "music123",
            "title": "Music Video",
            "artists": [{"name": "Artist"}],
            "thumbnails": [],
            "duration": "4:00",
        }
    ]
    youtube_service.yt.search.return_value = mock_result

    results = youtube_service.search("https://music.youtube.com/watch?v=music123")

    assert len(results) == 1


def test_youtube_search_playlist_url(youtube_service):
    """Test search with playlist URL."""
    mock_playlist = {"id": "PLabc", "title": "My Playlist", "thumbnails": [{"url": "http://thumb"}], "trackCount": 25}
    youtube_service.yt.get_playlist.return_value = mock_playlist

    results = youtube_service.search("https://youtube.com/playlist?list=PLabc", type="playlist")

    assert len(results) == 1
    assert results[0]["type"] == "playlist"
    assert results[0]["track_count"] == 25


def test_youtube_search_channel_url(youtube_service):
    """Test search with channel URL."""
    mock_artist = {"browseId": "UCArtist", "name": "Channel Artist", "thumbnails": [{"url": "http://artist.jpg"}]}
    youtube_service.yt.get_artist.return_value = mock_artist

    results = youtube_service.search("https://youtube.com/channel/UCArtist", type="artist")

    assert len(results) == 1
    assert results[0]["type"] == "artist"


def test_youtube_search_handle_url(youtube_service):
    """Test search with @handle URL."""
    youtube_service.yt.search.return_value = []

    # Should fall back to keyword search for handles without UC prefix
    results = youtube_service.search("https://youtube.com/@SomeCreator", type="artist")

    assert results == []


# =============================================================================
# Video Search
# =============================================================================


def test_search_video_success(youtube_service):
    """Test _search_video with valid result."""
    mock_result = [
        {"videoId": "vid1", "title": "Found Video", "artists": [{"name": "A"}], "thumbnails": [], "duration": "3:00"}
    ]
    youtube_service.yt.search.return_value = mock_result

    results = youtube_service._search_video("vid1")

    assert len(results) == 1
    assert results[0]["title"] == "Found Video"


def test_search_video_not_found(youtube_service):
    """Test _search_video when no results."""
    youtube_service.yt.search.return_value = []

    results = youtube_service._search_video("notexist")

    assert results == []


def test_search_video_error(youtube_service):
    """Test _search_video with API error."""
    youtube_service.yt.search.side_effect = Exception("API Error")

    results = youtube_service._search_video("error_id")

    assert results == []


# =============================================================================
# Playlist Search
# =============================================================================


def test_search_playlist_success(youtube_service):
    """Test _search_playlist with valid result."""
    mock_playlist = {
        "id": "PL123",
        "title": "Found Playlist",
        "thumbnails": [{"url": "http://pl.jpg"}],
        "trackCount": 50,
    }
    youtube_service.yt.get_playlist.return_value = mock_playlist

    results = youtube_service._search_playlist("PL123")

    assert len(results) == 1
    assert results[0]["title"] == "Found Playlist"
    assert results[0]["track_count"] == 50


def test_search_playlist_no_thumbnails(youtube_service):
    """Test _search_playlist without thumbnails."""
    mock_playlist = {"id": "PL456", "title": "No Thumb Playlist", "thumbnails": []}
    youtube_service.yt.get_playlist.return_value = mock_playlist

    results = youtube_service._search_playlist("PL456")

    assert len(results) == 1
    assert results[0]["image_url"] is None


def test_search_playlist_error(youtube_service):
    """Test _search_playlist with API error."""
    youtube_service.yt.get_playlist.side_effect = Exception("Not found")

    results = youtube_service._search_playlist("invalid")

    assert results == []


# =============================================================================
# Channel Search
# =============================================================================


def test_search_channel_success(youtube_service):
    """Test _search_channel with UC channel ID."""
    mock_artist = {"browseId": "UCChannel", "name": "Some Artist", "thumbnails": [{"url": "http://ch.jpg"}]}
    youtube_service.yt.get_artist.return_value = mock_artist

    results = youtube_service._search_channel("UCChannel")

    assert len(results) == 1
    assert results[0]["name"] == "Some Artist"


def test_search_channel_non_uc_id(youtube_service):
    """Test _search_channel with non-UC ID."""
    results = youtube_service._search_channel("notUCprefix")

    assert results == []


def test_search_channel_error(youtube_service):
    """Test _search_channel with API error."""
    youtube_service.yt.get_artist.side_effect = Exception("Error")

    results = youtube_service._search_channel("UCError")

    assert results == []


# =============================================================================
# Keyword Search
# =============================================================================


def test_search_keywords_songs(youtube_service):
    """Test keyword search for songs."""
    mock_results = [
        {
            "resultType": "song",
            "videoId": "s1",
            "title": "Song 1",
            "artists": [{"name": "A"}],
            "thumbnails": [],
            "duration": "3:00",
        }
    ]
    youtube_service.yt.search.return_value = mock_results

    results = youtube_service._search_keywords("test query", 10, "song")

    assert len(results) == 1
    youtube_service.yt.search.assert_called_with("test query", filter="songs", limit=10)


def test_search_keywords_artists(youtube_service):
    """Test keyword search for artists."""
    mock_results = [
        {
            "resultType": "artist",
            "browseId": "UC123",
            "artist": "Found Artist",
            "thumbnails": [{"url": "http://art.jpg"}],
        }
    ]
    youtube_service.yt.search.return_value = mock_results

    results = youtube_service._search_keywords("artist name", 10, "artist")

    assert len(results) == 1
    youtube_service.yt.search.assert_called_with("artist name", filter="artists", limit=10)


def test_search_keywords_playlists(youtube_service):
    """Test keyword search for playlists."""
    mock_results = [
        {
            "resultType": "playlist",
            "browseId": "PL123",
            "title": "Found Playlist",
            "thumbnails": [],
            "itemCount": "25",  # String count
        }
    ]
    youtube_service.yt.search.return_value = mock_results

    results = youtube_service._search_keywords("playlist", 10, "playlist")

    assert len(results) == 1
    assert results[0]["track_count"] == 25


def test_search_keywords_error(youtube_service):
    """Test keyword search with API error."""
    youtube_service.yt.search.side_effect = Exception("Error")

    results = youtube_service._search_keywords("query", 10, "song")

    assert results == []


# =============================================================================
# Map Search Result
# =============================================================================


def test_map_search_result_song(youtube_service):
    """Test mapping song result."""
    item = {
        "resultType": "song",
        "videoId": "vid1",
        "title": "Song",
        "artists": [{"name": "A"}],
        "thumbnails": [],
        "duration": "3:30",
    }

    result = youtube_service._map_search_result(item)

    assert result["id"] == "vid1"
    assert result["source"] == "youtube"


def test_map_search_result_artist(youtube_service):
    """Test mapping artist result."""
    item = {"resultType": "artist", "browseId": "UC123", "artist": "Artist Name", "thumbnails": [{"url": "http://img"}]}

    result = youtube_service._map_search_result(item)

    assert result["type"] == "artist"
    assert result["name"] == "Artist Name"


def test_map_search_result_playlist(youtube_service):
    """Test mapping playlist result."""
    item = {"resultType": "playlist", "browseId": "PL123", "title": "Playlist", "thumbnails": [], "itemCount": 10}

    result = youtube_service._map_search_result(item)

    assert result["type"] == "playlist"
    assert result["track_count"] == 10


def test_map_search_result_playlist_string_count(youtube_service):
    """Test mapping playlist with string item count."""
    item = {
        "resultType": "playlist",
        "browseId": "PL456",
        "title": "Playlist",
        "thumbnails": [],
        "itemCount": "invalid",  # Non-numeric string
    }

    result = youtube_service._map_search_result(item)

    assert result["track_count"] == 0


def test_map_search_result_unknown(youtube_service):
    """Test mapping unknown result type."""
    item = {"resultType": "unknown"}

    result = youtube_service._map_search_result(item)

    assert result is None


# =============================================================================
# Artist Tracks
# =============================================================================


def test_get_artist_tracks_success(youtube_service):
    """Test getting artist tracks."""
    mock_artist = {"songs": {"browseId": "PLsongs123"}}
    mock_playlist = {
        "tracks": [
            {"videoId": "v1", "title": "T1", "artists": [], "thumbnails": [], "duration": "3:00"},
            {"videoId": "v2", "title": "T2", "artists": [], "thumbnails": [], "duration": "4:00"},
        ]
    }
    youtube_service.yt.get_artist.return_value = mock_artist
    youtube_service.yt.get_playlist.return_value = mock_playlist

    tracks = youtube_service.get_artist_tracks("UC123")

    assert len(tracks) == 2


def test_get_artist_tracks_no_songs(youtube_service):
    """Test artist with no songs browse ID."""
    mock_artist = {"songs": {}}
    youtube_service.yt.get_artist.return_value = mock_artist

    tracks = youtube_service.get_artist_tracks("UC123")

    assert tracks == []


def test_get_artist_tracks_error(youtube_service):
    """Test artist tracks with API error."""
    youtube_service.yt.get_artist.side_effect = Exception("Error")

    tracks = youtube_service.get_artist_tracks("UCError")

    assert tracks == []


# =============================================================================
# Playlist Details
# =============================================================================


def test_get_playlist_details_success(youtube_service):
    """Test getting full playlist details."""
    mock_playlist = {
        "id": "PL123",
        "title": "Full Playlist",
        "description": "A great playlist",
        "thumbnails": [{"url": "http://pl.jpg"}],
        "trackCount": 10,
        "tracks": [{"videoId": "v1", "title": "T1", "artists": [], "thumbnails": [], "duration": "3:00"}],
    }
    youtube_service.yt.get_playlist.return_value = mock_playlist

    details = youtube_service.get_playlist_details("PL123")

    assert details["title"] == "Full Playlist"
    assert len(details["tracks"]) == 1


def test_get_playlist_details_no_tracks(youtube_service):
    """Test playlist details without tracks."""
    mock_playlist = {"id": "PL456", "title": "Empty Playlist", "thumbnails": []}
    youtube_service.yt.get_playlist.return_value = mock_playlist

    details = youtube_service.get_playlist_details("PL456")

    assert details["tracks"] == []
    assert details["track_count"] == 0


def test_get_playlist_details_error(youtube_service):
    """Test playlist details with API error."""
    youtube_service.yt.get_playlist.side_effect = Exception("Not found")

    details = youtube_service.get_playlist_details("invalid")

    assert details is None


# =============================================================================
# Format Track
# =============================================================================


def test_format_track_full(youtube_service):
    """Test formatting track with all data."""
    item = {
        "videoId": "abc123",
        "title": "Full Track",
        "artists": [{"name": "Artist 1"}, {"name": "Artist 2"}],
        "album": {"name": "Album Name"},
        "thumbnails": [{"url": "http://thumb.jpg"}],
        "duration": "3:45",
    }

    result = youtube_service._format_track(item)

    assert result["id"] == "abc123"
    assert result["title"] == "Full Track"
    assert result["artist"] == "Artist 1, Artist 2"
    assert result["album"] == "Album Name"
    assert result["duration_ms"] == 225000  # 3:45 in ms


def test_format_track_duration_seconds(youtube_service):
    """Test formatting track with duration_seconds."""
    item = {"videoId": "s1", "title": "Track", "artists": [], "thumbnails": [], "duration_seconds": 180}

    result = youtube_service._format_track(item)

    assert result["duration_ms"] == 180000


def test_format_track_duration_hms(youtube_service):
    """Test formatting track with H:M:S duration."""
    item = {"videoId": "long1", "title": "Long Track", "artists": [], "thumbnails": [], "duration": "1:02:30"}

    result = youtube_service._format_track(item)

    assert result["duration_ms"] == (1 * 3600 + 2 * 60 + 30) * 1000


def test_format_track_no_duration(youtube_service):
    """Test formatting track with no duration."""
    item = {"videoId": "nd1", "title": "No Duration", "artists": [], "thumbnails": []}

    result = youtube_service._format_track(item)

    assert result["duration_ms"] == 0


def test_format_track_with_album_name(youtube_service):
    """Test formatting track with fallback album name."""
    item = {"videoId": "a1", "title": "Track", "artists": [], "thumbnails": [], "duration": "3:00"}

    result = youtube_service._format_track(item, album_name="Fallback Album")

    assert result["album"] == "Fallback Album"


def test_format_track_no_thumbnails(youtube_service):
    """Test formatting track without thumbnails."""
    item = {"videoId": "nt1", "title": "No Thumb", "artists": [], "thumbnails": [], "duration": "3:00"}

    result = youtube_service._format_track(item)

    assert result["image_url"] is None


def test_format_track_empty_duration(youtube_service):
    """Test formatting track with empty duration string."""
    item = {"videoId": "ed1", "title": "Empty Duration", "artists": [], "thumbnails": [], "duration": ""}

    result = youtube_service._format_track(item)

    assert result["duration_ms"] == 0
