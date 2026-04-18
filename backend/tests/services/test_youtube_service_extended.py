"""Extended tests covering uncovered paths in YouTubeService."""

from unittest.mock import MagicMock, patch

import pytest
from app.services.youtube_service import YouTubeService


@pytest.fixture
def service():
    with patch("app.services.youtube_service.YTMusic"):
        svc = YouTubeService()
        svc.yt = MagicMock()
        return svc


# ─── search() routing ─────────────────────────────────────────────────────────


def test_search_routes_to_playlist_search(service):
    service.yt.get_playlist.return_value = {
        "id": "pl1",
        "title": "Playlist",
        "thumbnails": [{"url": "http://img"}],
        "trackCount": 10,
    }
    results = service.search("https://www.youtube.com/watch?v=abc&list=PLxxx", type="playlist")
    assert len(results) == 1
    assert results[0]["type"] == "playlist"


def test_search_routes_to_channel_search_with_uc_prefix(service):
    service.yt.get_artist.return_value = {
        "browseId": "UCabc",
        "name": "Artist Name",
        "thumbnails": [{"url": "http://img"}],
    }
    results = service.search("https://www.youtube.com/channel/UCabc", type="artist")
    assert len(results) == 1
    assert results[0]["type"] == "artist"


def test_search_channel_non_uc_returns_empty(service):
    results = service._search_channel("@somehandle")
    assert results == []


def test_search_routes_to_keyword_for_artist_type(service):
    service.yt.search.return_value = []
    service.search("nirvana", type="artist")
    service.yt.search.assert_called_with("nirvana", filter="artists", limit=20)


def test_search_routes_to_keyword_for_playlist_type(service):
    service.yt.search.return_value = []
    service.search("chill mix", type="playlist")
    service.yt.search.assert_called_with("chill mix", filter="community_playlists", limit=20)


# ─── _search_video ─────────────────────────────────────────────────────────────


def test_search_video_exception_returns_empty(service):
    service.yt.search.side_effect = RuntimeError("API error")
    result = service._search_video("vidId")
    assert result == []


def test_search_video_empty_results_returns_empty(service):
    service.yt.search.return_value = []
    result = service._search_video("vidId")
    assert result == []


# ─── _search_playlist ─────────────────────────────────────────────────────────


def test_search_playlist_success(service):
    service.yt.get_playlist.return_value = {
        "id": "PL1",
        "title": "My Playlist",
        "thumbnails": [{"url": "http://img"}],
        "trackCount": 5,
    }
    result = service._search_playlist("PL1")
    assert len(result) == 1
    assert result[0]["title"] == "My Playlist"
    assert result[0]["type"] == "playlist"
    assert result[0]["track_count"] == 5


def test_search_playlist_no_thumbnails(service):
    service.yt.get_playlist.return_value = {
        "id": "PL1",
        "title": "PL",
        "trackCount": 3,
    }
    result = service._search_playlist("PL1")
    assert result[0]["image_url"] is None


def test_search_playlist_exception_returns_empty(service):
    service.yt.get_playlist.side_effect = RuntimeError("error")
    result = service._search_playlist("PL1")
    assert result == []


# ─── _search_channel ─────────────────────────────────────────────────────────


def test_search_channel_uc_success(service):
    service.yt.get_artist.return_value = {
        "browseId": "UCabc",
        "name": "My Channel",
        "thumbnails": [{"url": "http://img"}],
    }
    result = service._search_channel("UCabc")
    assert len(result) == 1
    assert result[0]["type"] == "artist"
    assert result[0]["name"] == "My Channel"


def test_search_channel_uc_exception_returns_empty(service):
    service.yt.get_artist.side_effect = RuntimeError("error")
    result = service._search_channel("UCabc")
    assert result == []


def test_search_channel_no_thumbnails(service):
    service.yt.get_artist.return_value = {
        "browseId": "UCabc",
        "name": "Artist",
    }
    result = service._search_channel("UCabc")
    assert result[0]["image_url"] is None


# ─── _search_keywords ─────────────────────────────────────────────────────────


def test_search_keywords_exception_returns_empty(service):
    service.yt.search.side_effect = RuntimeError("API down")
    result = service._search_keywords("query", 10, "song")
    assert result == []


# ─── _map_search_result ───────────────────────────────────────────────────────


def test_map_search_result_artist_type(service):
    item = {
        "resultType": "artist",
        "browseId": "UCabc",
        "artist": "Cool Artist",
        "thumbnails": [{"url": "http://img"}],
    }
    result = service._map_search_result(item)
    assert result is not None
    assert result["type"] == "artist"
    assert result["name"] == "Cool Artist"


def test_map_search_result_playlist_type(service):
    item = {
        "resultType": "playlist",
        "browseId": "PLabc",
        "title": "Great Playlist",
        "itemCount": 12,
        "thumbnails": [{"url": "http://img"}],
    }
    result = service._map_search_result(item)
    assert result is not None
    assert result["type"] == "playlist"
    assert result["track_count"] == 12


def test_map_search_result_playlist_string_item_count(service):
    item = {
        "resultType": "playlist",
        "browseId": "PLabc",
        "title": "PL",
        "itemCount": "7",
    }
    result = service._map_search_result(item)
    assert result["track_count"] == 7


def test_map_search_result_playlist_non_numeric_item_count(service):
    item = {
        "resultType": "playlist",
        "browseId": "PLabc",
        "title": "PL",
        "itemCount": "many",
    }
    result = service._map_search_result(item)
    assert result["track_count"] == 0


def test_map_search_result_unknown_type_returns_none(service):
    result = service._map_search_result({"resultType": "album"})
    assert result is None


# ─── get_artist_tracks ────────────────────────────────────────────────────────


def test_get_artist_tracks_success(service):
    service.yt.get_artist.return_value = {
        "songs": {"browseId": "PLsongs"},
    }
    service.yt.get_playlist.return_value = {
        "tracks": [
            {"videoId": "v1", "title": "Song 1", "artists": [{"name": "A"}], "thumbnails": [{"url": "img"}]},
        ]
    }
    tracks = service.get_artist_tracks("UCabc")
    assert len(tracks) == 1
    assert tracks[0]["title"] == "Song 1"


def test_get_artist_tracks_no_songs_browse_id(service):
    service.yt.get_artist.return_value = {"songs": {}}
    tracks = service.get_artist_tracks("UCabc")
    assert tracks == []


def test_get_artist_tracks_exception_returns_empty(service):
    service.yt.get_artist.side_effect = RuntimeError("error")
    tracks = service.get_artist_tracks("UCabc")
    assert tracks == []


# ─── get_playlist_details ─────────────────────────────────────────────────────


def test_get_playlist_details_exception_returns_none(service):
    service.yt.get_playlist.side_effect = RuntimeError("error")
    result = service.get_playlist_details("PL1")
    assert result is None


# ─── _format_track ────────────────────────────────────────────────────────────


def test_format_track_with_duration_seconds(service):
    item = {
        "videoId": "v1",
        "title": "T",
        "artists": [],
        "duration_seconds": 250,
    }
    result = service._format_track(item)
    assert result["duration_ms"] == 250_000


def test_format_track_duration_none_string(service):
    item: dict = {
        "videoId": "v1",
        "title": "T",
        "artists": [],
        "duration": None,
    }
    result = service._format_track(item)
    assert result["duration_ms"] == 0
