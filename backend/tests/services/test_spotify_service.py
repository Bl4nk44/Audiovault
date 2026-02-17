from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from app.services.spotify_service import SpotifyService


@pytest.fixture
def spotify_service():
    with (
        patch("app.services.spotify_service.spotipy.Spotify"),
        patch("app.services.spotify_service.SpotifyClientCredentials"),
    ):
        service = SpotifyService()
        mock_client = MagicMock()
        safe_paginated: dict[str, Any] = {"items": [], "next": None, "tracks": {"items": [], "next": None}}
        mock_client.next.return_value = {"next": None, "items": []}
        mock_client.search.return_value = safe_paginated
        mock_client.artist_albums.return_value = safe_paginated
        mock_client.artist_top_tracks.return_value = {"tracks": []}
        mock_client.album_tracks.return_value = safe_paginated
        mock_client.playlist_tracks.return_value = safe_paginated
        service.client = mock_client
        return service


def test_spotify_search_keywords(spotify_service):
    mock_results = {
        "tracks": {
            "items": [
                {
                    "id": "t1",
                    "name": "T1",
                    "artists": [{"name": "A1", "id": "a1"}],
                    "album": {"name": "AL1", "images": [{"url": "http://img"}]},
                    "duration_ms": 100,
                }
            ]
        }
    }
    spotify_service.client.search.return_value = mock_results
    results = spotify_service.search("test")
    assert len(results) == 1
    assert results[0]["title"] == "T1"


def test_spotify_get_track(spotify_service):
    mock_track = {
        "id": "t1",
        "name": "T1",
        "artists": [{"name": "A1", "id": "a1"}],
        "album": {"name": "AL1", "images": [{"url": "http://img"}]},
        "duration_ms": 100,
    }
    spotify_service.client.track.return_value = mock_track
    track = spotify_service.get_track("t1")
    assert track["title"] == "T1"


def test_spotify_get_playlist_tracks(spotify_service):
    mock_pl = {
        "items": [
            {
                "track": {
                    "id": "t1",
                    "name": "T1",
                    "artists": [{"name": "A1", "id": "a1"}],
                    "album": {"name": "AL1", "images": [{"url": "http://img"}]},
                    "duration_ms": 100,
                }
            }
        ],
        "next": None,
    }
    spotify_service.client.playlist_tracks.return_value = mock_pl
    tracks = spotify_service.get_playlist_tracks("pl1")
    assert len(tracks) == 1


def test_spotify_get_album_tracks(spotify_service):
    mock_album = {
        "id": "al1",
        "name": "Album",
        "artists": [{"name": "A1", "id": "a1"}],
        "images": [{"url": "http://img"}],
    }
    mock_tracks = {
        "items": [{"id": "t1", "name": "T1", "artists": [{"name": "A1", "id": "a1"}], "duration_ms": 100}],
        "next": None,
    }
    spotify_service.client.album.return_value = mock_album
    spotify_service.client.album_tracks.return_value = mock_tracks
    tracks = spotify_service.get_album_tracks("al1")
    assert len(tracks) == 1


def test_spotify_format_playlist(spotify_service):
    item = {"id": "pl1", "name": "PL", "images": [{"url": "http://img"}], "tracks": {"total": 10}}
    res = spotify_service._format_playlist(item)
    assert res["title"] == "PL"
    assert res["track_count"] == 10


def test_spotify_format_artist(spotify_service):
    item = {"id": "ar1", "name": "Artist", "images": [{"url": "http://img"}]}
    res = spotify_service._format_artist(item)
    assert res["name"] == "Artist"


def test_spotify_get_artist_details(spotify_service):
    mock_artist = {"id": "ar1", "name": "Artist", "images": [{"url": "http://img"}]}
    mock_top = {
        "tracks": [
            {
                "id": "t1",
                "name": "T1",
                "artists": [{"name": "A1", "id": "a1"}],
                "album": {"name": "AL1", "images": [{"url": "http://img"}]},
                "duration_ms": 100,
            }
        ]
    }
    mock_albums = {
        "items": [
            {
                "id": "al1",
                "name": "Album",
                "images": [{"url": "http://img"}],
                "release_date": "2024",
                "total_tracks": 5,
                "type": "album",
            }
        ],
        "next": None,
    }
    spotify_service.client.artist.return_value = mock_artist
    spotify_service.client.artist_top_tracks.return_value = mock_top
    spotify_service.client.artist_albums.return_value = mock_albums
    res = spotify_service.get_artist_details("ar1")
    assert res["name"] == "Artist"
    assert len(res["tracks"]) == 1
    assert len(res["albums"]) == 1
