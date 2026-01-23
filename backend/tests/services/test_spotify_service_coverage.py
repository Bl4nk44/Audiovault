from unittest.mock import MagicMock, patch

import pytest
from app.services.spotify_service import SpotifyService


@pytest.fixture
def spotify_service_mocked():
    with patch("app.services.spotify_service.spotipy.Spotify") as mock_spotify_cls, \
         patch("app.services.spotify_service.SpotifyClientCredentials"):

        mock_client = MagicMock()
        mock_spotify_cls.return_value = mock_client

        service = SpotifyService()
        service.client = mock_client
        return service

def test_spotify_client_not_configured():
    with patch("app.core.config.settings.SPOTIFY_CLIENT_ID", None):
        service = SpotifyService()
        assert service.client is None
        assert service.search("query") == []

def test_search_short_link(spotify_service_mocked):
    with patch("requests.head") as mock_head:
        mock_head.return_value.url = "https://open.spotify.com/track/123"

        spotify_service_mocked.client.track.return_value = {
            "id": "123", "name": "Short Link Song",
            "artists": [{"name": "A", "id": "aid"}],
            "duration_ms": 100,
            "album": {"name": "Alb", "images": []},
            "external_ids": {"isrc": "isrc1"}
        }

        results = spotify_service_mocked.search("https://spotify.link/xyz")

        assert len(results) == 1
        assert results[0]["id"] == "123"
        assert mock_head.called

def test_search_exception_handling(spotify_service_mocked):
    spotify_service_mocked.client.search.side_effect = Exception("API Error")
    results = spotify_service_mocked.search("query")
    assert results == []

def test_get_playlist_tracks_pagination(spotify_service_mocked):
    # Fix: Ensure track formatting has everything needed
    track1 = {
        "id": "t1", "name": "T1", "artists": [{"name": "A", "id": "aid"}],
        "duration_ms": 100, "album": {"name": "A", "images": []}
    }
    track2 = {
        "id": "t2", "name": "T2", "artists": [{"name": "A", "id": "aid"}],
        "duration_ms": 100, "album": {"name": "A", "images": []}
    }

    # Page 1
    page1 = {
        "items": [{"track": track1}],
        "next": "url_to_page_2"
    }
    # Page 2
    page2 = {
        "items": [{"track": track2}],
        "next": None
    }

    spotify_service_mocked.client.playlist_tracks.return_value = page1
    spotify_service_mocked.client.next.return_value = page2

    tracks = spotify_service_mocked.get_playlist_tracks("pl_id")

    assert len(tracks) == 2
    assert tracks[0]["id"] == "t1"
    assert tracks[1]["id"] == "t2"

def test_get_artist_details_full_flow(spotify_service_mocked):
    # 1. Artist
    spotify_service_mocked.client.artist.return_value = {
        "id": "ar1", "name": "The Artist", "images": [{"url": "img"}]
    }
    # 2. Top Tracks
    spotify_service_mocked.client.artist_top_tracks.return_value = {
        "tracks": [
            {
                "id": "t1",
                "name": "Hit",
                "artists": [{"name": "The Artist", "id": "ar1"}],
                "duration_ms": 100,
                "album": {"name": "Al", "images": []},
            }
        ]
    }
    # 3. Albums (Pagination)
    p1 = {
        "items": [
            {
                "id": "al1",
                "name": "Alb1",
                "release_date": "2020",
                "total_tracks": 10,
                "images": [{"url": "cover"}],
                "type": "album",
            }
        ],
        "next": "next",
    }
    p2 = {
        "items": [
            {
                "id": "al2",
                "name": "Alb2",
                "release_date": "2021",
                "total_tracks": 12,
                "images": [{"url": "cover"}],
                "type": "album",
            }
        ],
        "next": None,
    }

    spotify_service_mocked.client.artist_albums.return_value = p1
    spotify_service_mocked.client.next.return_value = p2

    details = spotify_service_mocked.get_artist_details("ar1")

    assert details["name"] == "The Artist"
    assert len(details["tracks"]) == 1
    assert len(details["albums"]) == 2

def test_get_artist_details_error(spotify_service_mocked):
    spotify_service_mocked.client.artist.side_effect = Exception("Boom")
    assert spotify_service_mocked.get_artist_details("ar1") is None

def test_get_album_details_success(spotify_service_mocked):
    spotify_service_mocked.client.album.return_value = {
        "id": "al1", "name": "Album", "artists": [{"name": "A", "id": "aid"}],
        "images": [{"url": "img"}], "release_date": "2022", "total_tracks": 2, "label": "L"
    }

    # Mock get_album_tracks via client.album_tracks
    spotify_service_mocked.client.album_tracks.return_value = {
        "items": [
            {"id": "t1", "name": "T1", "artists": [{"name": "A", "id": "aid"}], "duration_ms": 100},
            {"id": "t2", "name": "T2", "artists": [{"name": "A", "id": "aid"}], "duration_ms": 200}
        ],
        "next": None
    }

    details = spotify_service_mocked.get_album_details("al1")

    assert details["title"] == "Album"
    assert len(details["tracks"]) == 2

def test_get_album_details_error(spotify_service_mocked):
    spotify_service_mocked.client.album.side_effect = Exception("Boom")
    assert spotify_service_mocked.get_album_details("al1") is None

def test_search_direct_url_types(spotify_service_mocked):
    # Artist URL
    spotify_service_mocked.client.artist.return_value = {"id": "ar1", "name": "A", "images": []}
    spotify_service_mocked.client.artist_top_tracks.return_value = {"tracks": []}
    spotify_service_mocked.client.artist_albums.return_value = {"items": [], "next": None}

    res = spotify_service_mocked.search("https://open.spotify.com/artist/ar1")
    assert res[0]["type"] == "artist"

