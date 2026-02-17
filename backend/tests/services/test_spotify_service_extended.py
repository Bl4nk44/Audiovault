"""
Extended tests for SpotifyService to increase code coverage to 80%+.
Covers: search with different types, URL parsing, pagination, error handling, album/artist details.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from app.services.spotify_service import SpotifyService


@pytest.fixture
def spotify_service():
    """Create SpotifyService with mocked client."""
    with (
        patch("app.services.spotify_service.spotipy.Spotify"),
        patch("app.services.spotify_service.SpotifyClientCredentials"),
    ):
        service = SpotifyService()
        mock_client = MagicMock()

        # Default safe returns for pagination methods
        safe_paginated: dict[str, Any] = {"items": [], "next": None, "tracks": {"items": [], "next": None}}
        mock_client.next.return_value = {"next": None, "items": []}
        mock_client.search.return_value = safe_paginated
        mock_client.artist_albums.return_value = safe_paginated
        mock_client.artist_top_tracks.return_value = {"tracks": []}
        mock_client.album_tracks.return_value = safe_paginated
        mock_client.playlist_tracks.return_value = safe_paginated

        service.client = mock_client
        return service


@pytest.fixture
def spotify_service_no_client():
    """SpotifyService without configured client."""
    with patch("app.services.spotify_service.settings") as mock_settings:
        mock_settings.SPOTIFY_CLIENT_ID = None
        mock_settings.SPOTIFY_CLIENT_SECRET = None
        service = SpotifyService()
        service.client = None
        return service


# =============================================================================
# GRUPA 1: Search - różne typy
# =============================================================================


def test_spotify_search_tracks(spotify_service):
    """Test search returning tracks."""
    mock_track = {
        "id": "track1",
        "name": "Test Track",
        "artists": [{"name": "Artist", "id": "a1"}],
        "album": {"name": "Album", "images": [{"url": "http://img"}]},
        "duration_ms": 180000,
        "popularity": 85,
    }
    spotify_service.client.search.return_value = {"tracks": {"items": [mock_track]}}

    results = spotify_service.search("test query", type="track")

    assert len(results) == 1
    assert results[0]["title"] == "Test Track"
    assert results[0]["source"] == "spotify"


def test_spotify_search_artists(spotify_service):
    """Test search returning artists."""
    mock_artist = {"id": "artist1", "name": "Test Artist", "images": [{"url": "http://artist.img"}]}
    spotify_service.client.search.return_value = {"artists": {"items": [mock_artist]}}

    results = spotify_service.search("artist name", type="artist")

    assert len(results) == 1
    assert results[0]["name"] == "Test Artist"
    assert results[0]["type"] == "artist"


def test_spotify_search_playlists(spotify_service):
    """Test search returning playlists."""
    mock_playlist = {
        "id": "pl1",
        "name": "Test Playlist",
        "images": [{"url": "http://playlist.img"}],
        "tracks": {"total": 50},
    }
    spotify_service.client.search.return_value = {"playlists": {"items": [mock_playlist]}}

    results = spotify_service.search("playlist", type="playlist")

    assert len(results) == 1
    assert results[0]["title"] == "Test Playlist"
    assert results[0]["type"] == "playlist"
    assert results[0]["track_count"] == 50


def test_spotify_search_empty_results(spotify_service):
    """Test search with no results."""
    spotify_service.client.search.return_value = {"tracks": {"items": []}}

    results = spotify_service.search("nonexistent query")

    assert results == []


def test_spotify_search_no_client(spotify_service_no_client):
    """Test search when client is not configured."""
    results = spotify_service_no_client.search("query")

    assert results == []


def test_spotify_search_api_error(spotify_service):
    """Test search handling API errors."""
    spotify_service.client.search.side_effect = Exception("API Error")

    results = spotify_service.search("query")

    assert results == []


def test_spotify_search_null_playlist_items(spotify_service):
    """Test search handles null items in playlists."""
    spotify_service.client.search.return_value = {
        "playlists": {"items": [None, {"id": "pl1", "name": "Valid", "images": [], "tracks": {"total": 10}}]}
    }

    results = spotify_service.search("playlist", type="playlist")

    assert len(results) == 1
    assert results[0]["title"] == "Valid"


# =============================================================================
# GRUPA 2: URL parsing w search
# =============================================================================


def test_spotify_search_track_url(spotify_service):
    """Test search with direct track URL."""
    mock_track = {
        "id": "abc123",
        "name": "Direct Track",
        "artists": [{"name": "Artist", "id": "a1"}],
        "album": {"name": "Album", "images": [{"url": "http://img"}]},
        "duration_ms": 200000,
    }
    spotify_service.client.track.return_value = mock_track

    results = spotify_service.search("https://open.spotify.com/track/abc123")

    assert len(results) == 1
    assert results[0]["id"] == "abc123"
    spotify_service.client.track.assert_called_with("abc123")


def test_spotify_search_track_url_intl(spotify_service):
    """Test search with international locale URL."""
    mock_track = {
        "id": "xyz789",
        "name": "Intl Track",
        "artists": [{"name": "Artist", "id": "a1"}],
        "album": {"name": "Album", "images": []},
        "duration_ms": 150000,
    }
    spotify_service.client.track.return_value = mock_track

    results = spotify_service.search("https://open.spotify.com/intl-pl/track/xyz789")

    assert len(results) == 1
    assert results[0]["id"] == "xyz789"


def test_spotify_search_artist_url(spotify_service):
    """Test search with artist URL."""
    mock_artist = {"id": "artist123", "name": "URL Artist", "images": [{"url": "http://artist.img"}]}
    spotify_service.client.artist.return_value = mock_artist

    results = spotify_service.search("https://open.spotify.com/artist/artist123")

    assert len(results) == 1
    assert results[0]["name"] == "URL Artist"
    assert results[0]["type"] == "artist"


def test_spotify_search_playlist_url(spotify_service):
    """Test search with playlist URL."""
    mock_playlist = {"id": "pl123", "name": "URL Playlist", "images": [], "tracks": {"total": 25}}
    spotify_service.client.playlist.return_value = mock_playlist

    results = spotify_service.search("https://open.spotify.com/playlist/pl123")

    assert len(results) == 1
    assert results[0]["title"] == "URL Playlist"


def test_spotify_search_album_url(spotify_service):
    """Test search with album URL."""
    mock_album = {"id": "album123", "name": "URL Album", "images": [{"url": "http://album.img"}], "total_tracks": 12}
    spotify_service.client.album.return_value = mock_album

    results = spotify_service.search("https://open.spotify.com/album/album123")

    assert len(results) == 1
    assert results[0]["title"] == "URL Album"


def test_spotify_search_artist_url_error(spotify_service):
    """Test artist URL with API error."""
    spotify_service.client.artist.side_effect = Exception("Not found")

    results = spotify_service.search("https://open.spotify.com/artist/invalid")

    assert results == []


def test_spotify_search_playlist_url_error(spotify_service):
    """Test playlist URL with API error."""
    spotify_service.client.playlist.side_effect = Exception("Access denied")

    results = spotify_service.search("https://open.spotify.com/playlist/private")

    assert results == []


def test_spotify_search_album_url_error(spotify_service):
    """Test album URL with API error."""
    spotify_service.client.album.side_effect = Exception("Not found")

    results = spotify_service.search("https://open.spotify.com/album/invalid")

    assert results == []


def test_spotify_search_short_link(spotify_service):
    """Test search with spotify.link short URL."""
    mock_track = {
        "id": "resolved",
        "name": "Resolved Track",
        "artists": [{"name": "Artist", "id": "a1"}],
        "album": {"name": "Album", "images": []},
        "duration_ms": 180000,
    }
    spotify_service.client.track.return_value = mock_track

    with patch("requests.head") as mock_head:
        mock_response = MagicMock()
        mock_response.url = "https://open.spotify.com/track/resolved"
        mock_head.return_value = mock_response

        results = spotify_service.search("https://spotify.link/abc123")

        assert len(results) == 1
        mock_head.assert_called_once()


def test_spotify_search_short_link_resolve_error(spotify_service):
    """Test short link resolution failure fallback."""
    spotify_service.client.search.return_value = {"tracks": {"items": []}}

    with patch("requests.head", side_effect=Exception("Network error")):
        results = spotify_service.search("https://spotify.link/abc123")

        # Should fallback to regular search
        assert results == []


# =============================================================================
# GRUPA 3: Playlist operations
# =============================================================================


def test_spotify_get_playlist_tracks_pagination(spotify_service):
    """Test playlist tracks with pagination."""
    page1_track = {
        "track": {
            "id": "t1",
            "name": "Track 1",
            "artists": [{"name": "A", "id": "a1"}],
            "album": {"name": "AL", "images": []},
            "duration_ms": 100,
        }
    }
    page2_track = {
        "track": {
            "id": "t2",
            "name": "Track 2",
            "artists": [{"name": "A", "id": "a1"}],
            "album": {"name": "AL", "images": []},
            "duration_ms": 100,
        }
    }

    spotify_service.client.playlist_tracks.return_value = {"items": [page1_track], "next": "page2_url"}
    spotify_service.client.next.return_value = {"items": [page2_track], "next": None}

    tracks = spotify_service.get_playlist_tracks("pl123")

    assert len(tracks) == 2


def test_spotify_get_playlist_tracks_no_client(spotify_service_no_client):
    """Test playlist tracks without client."""
    tracks = spotify_service_no_client.get_playlist_tracks("pl123")
    assert tracks == []


def test_spotify_get_playlist_tracks_null_track(spotify_service):
    """Test playlist tracks handles null tracks."""
    spotify_service.client.playlist_tracks.return_value = {
        "items": [
            {"track": None},
            {
                "track": {
                    "id": "valid",
                    "name": "Valid",
                    "artists": [{"name": "A", "id": "a1"}],
                    "album": {"name": "AL", "images": []},
                    "duration_ms": 100,
                }
            },
        ],
        "next": None,
    }

    tracks = spotify_service.get_playlist_tracks("pl123")

    assert len(tracks) == 1
    assert tracks[0]["id"] == "valid"


def test_spotify_get_playlist_details(spotify_service):
    """Test full playlist details with tracks."""
    mock_playlist = {
        "id": "pl123",
        "name": "Details Playlist",
        "images": [{"url": "http://pl.img"}],
        "tracks": {
            "total": 2,
            "items": [
                {
                    "track": {
                        "id": "t1",
                        "name": "T1",
                        "artists": [{"name": "A", "id": "a1"}],
                        "album": {"name": "AL", "images": []},
                        "duration_ms": 100,
                    }
                },
            ],
            "next": None,
        },
    }
    spotify_service.client.playlist.return_value = mock_playlist

    details = spotify_service.get_playlist_details("pl123")

    assert details["title"] == "Details Playlist"
    assert len(details["tracks"]) == 1


def test_spotify_get_playlist_details_pagination(spotify_service):
    """Test playlist details with paginated tracks."""
    mock_playlist = {
        "id": "pl123",
        "name": "Paginated Playlist",
        "images": [],
        "tracks": {
            "total": 150,
            "items": [
                {
                    "track": {
                        "id": f"t{i}",
                        "name": f"T{i}",
                        "artists": [{"name": "A", "id": "a1"}],
                        "album": {"name": "AL", "images": []},
                        "duration_ms": 100,
                    }
                }
                for i in range(100)
            ],
            "next": "page2",
        },
    }
    spotify_service.client.playlist.return_value = mock_playlist
    spotify_service.client.next.return_value = {
        "items": [
            {
                "track": {
                    "id": "t100",
                    "name": "T100",
                    "artists": [{"name": "A", "id": "a1"}],
                    "album": {"name": "AL", "images": []},
                    "duration_ms": 100,
                }
            }
        ],
        "next": None,
    }

    details = spotify_service.get_playlist_details("pl123")

    assert len(details["tracks"]) == 101


def test_spotify_get_playlist_details_no_client(spotify_service_no_client):
    """Test playlist details without client."""
    result = spotify_service_no_client.get_playlist_details("pl123")
    assert result is None


def test_spotify_get_playlist_details_error(spotify_service):
    """Test playlist details API error."""
    spotify_service.client.playlist.side_effect = Exception("API Error")

    result = spotify_service.get_playlist_details("pl123")

    assert result is None


# =============================================================================
# GRUPA 4: Artist operations
# =============================================================================


def test_spotify_get_artist_details_full(spotify_service):
    """Test full artist details with top tracks and albums."""
    mock_artist = {"id": "artist1", "name": "Full Artist", "images": [{"url": "http://artist.img"}]}
    mock_top_tracks = {
        "tracks": [
            {
                "id": "t1",
                "name": "Top 1",
                "artists": [{"name": "Full Artist", "id": "artist1"}],
                "album": {"name": "AL", "images": []},
                "duration_ms": 200000,
            }
        ]
    }
    mock_albums = {
        "items": [
            {
                "id": "alb1",
                "name": "Album 1",
                "images": [{"url": "http://alb.img"}],
                "release_date": "2024-01-01",
                "total_tracks": 12,
                "type": "album",
                "album_type": "album",
            }
        ],
        "next": None,
    }

    spotify_service.client.artist.return_value = mock_artist
    spotify_service.client.artist_top_tracks.return_value = mock_top_tracks
    spotify_service.client.artist_albums.return_value = mock_albums

    details = spotify_service.get_artist_details("artist1")

    assert details["name"] == "Full Artist"
    assert len(details["tracks"]) == 1
    assert len(details["albums"]) == 1


def test_spotify_get_artist_details_dedupe_albums(spotify_service):
    """Test artist details deduplicates albums."""
    mock_artist = {"id": "a1", "name": "Artist", "images": []}
    mock_albums = {
        "items": [
            {
                "id": "alb1",
                "name": "Same Album",
                "images": [],
                "release_date": "2024",
                "total_tracks": 10,
                "type": "album",
            },
            {
                "id": "alb2",
                "name": "Same Album",
                "images": [],
                "release_date": "2024",
                "total_tracks": 10,
                "type": "album",
            },
            {
                "id": "alb3",
                "name": "Other Album",
                "images": [],
                "release_date": "2023",
                "total_tracks": 8,
                "type": "album",
            },
        ],
        "next": None,
    }

    spotify_service.client.artist.return_value = mock_artist
    spotify_service.client.artist_top_tracks.return_value = {"tracks": []}
    spotify_service.client.artist_albums.return_value = mock_albums

    details = spotify_service.get_artist_details("a1")

    # Should deduplicate "Same Album"
    assert len(details["albums"]) == 2


def test_spotify_get_artist_details_no_client(spotify_service_no_client):
    """Test artist details without client."""
    result = spotify_service_no_client.get_artist_details("a1")
    assert result is None


def test_spotify_get_artist_details_error(spotify_service):
    """Test artist details API error."""
    spotify_service.client.artist.side_effect = Exception("Not found")

    result = spotify_service.get_artist_details("invalid")

    assert result is None


def test_spotify_get_artist_top_tracks(spotify_service):
    """Test getting artist top tracks."""
    mock_tracks = {
        "tracks": [
            {
                "id": "t1",
                "name": "Hit 1",
                "artists": [{"name": "A", "id": "a1"}],
                "album": {"name": "AL", "images": []},
                "duration_ms": 180000,
            },
            {
                "id": "t2",
                "name": "Hit 2",
                "artists": [{"name": "A", "id": "a1"}],
                "album": {"name": "AL", "images": []},
                "duration_ms": 200000,
            },
        ]
    }
    spotify_service.client.artist_top_tracks.return_value = mock_tracks

    tracks = spotify_service.get_artist_top_tracks("a1")

    assert len(tracks) == 2


def test_spotify_get_artist_top_tracks_no_client(spotify_service_no_client):
    """Test top tracks without client."""
    tracks = spotify_service_no_client.get_artist_top_tracks("a1")
    assert tracks == []


def test_spotify_get_artist_top_tracks_error(spotify_service):
    """Test top tracks API error."""
    spotify_service.client.artist_top_tracks.side_effect = Exception("Error")

    tracks = spotify_service.get_artist_top_tracks("a1")

    assert tracks == []


def test_spotify_get_artist_albums_pagination(spotify_service):
    """Test artist albums with pagination."""
    page1 = {"items": [{"id": "alb1", "name": "Album 1"}], "next": "page2"}
    page2 = {"items": [{"id": "alb2", "name": "Album 2"}], "next": None}

    spotify_service.client.artist_albums.return_value = page1
    spotify_service.client.next.return_value = page2

    albums = spotify_service.get_artist_albums("a1")

    assert len(albums) == 2


def test_spotify_get_artist_albums_no_client(spotify_service_no_client):
    """Test artist albums without client."""
    albums = spotify_service_no_client.get_artist_albums("a1")
    assert albums == []


def test_spotify_get_artist_albums_error(spotify_service):
    """Test artist albums API error."""
    spotify_service.client.artist_albums.side_effect = Exception("Error")

    albums = spotify_service.get_artist_albums("a1")

    assert albums == []


# =============================================================================
# GRUPA 5: Album operations
# =============================================================================


def test_spotify_get_album_tracks(spotify_service):
    """Test getting album tracks."""
    mock_album = {"id": "alb1", "name": "Test Album", "images": [{"url": "http://alb.img"}]}
    mock_tracks = {
        "items": [
            {"id": "t1", "name": "Track 1", "artists": [{"name": "A", "id": "a1"}], "duration_ms": 180000},
            {"id": "t2", "name": "Track 2", "artists": [{"name": "A", "id": "a1"}], "duration_ms": 200000},
        ],
        "next": None,
    }

    spotify_service.client.album.return_value = mock_album
    spotify_service.client.album_tracks.return_value = mock_tracks

    tracks = spotify_service.get_album_tracks("alb1")

    assert len(tracks) == 2
    # Tracks should have album info from album_obj
    assert tracks[0]["album"] == "Test Album"


def test_spotify_get_album_tracks_pagination(spotify_service):
    """Test album tracks with pagination."""
    mock_album = {"id": "alb1", "name": "Big Album", "images": []}
    page1 = {
        "items": [
            {"id": f"t{i}", "name": f"T{i}", "artists": [{"name": "A", "id": "a1"}], "duration_ms": 100}
            for i in range(50)
        ],
        "next": "page2",
    }
    page2 = {
        "items": [{"id": "t50", "name": "T50", "artists": [{"name": "A", "id": "a1"}], "duration_ms": 100}],
        "next": None,
    }

    spotify_service.client.album.return_value = mock_album
    spotify_service.client.album_tracks.return_value = page1
    spotify_service.client.next.return_value = page2

    tracks = spotify_service.get_album_tracks("alb1")

    assert len(tracks) == 51


def test_spotify_get_album_tracks_no_client(spotify_service_no_client):
    """Test album tracks without client."""
    tracks = spotify_service_no_client.get_album_tracks("alb1")
    assert tracks == []


def test_spotify_get_album_tracks_error(spotify_service):
    """Test album tracks API error."""
    spotify_service.client.album.side_effect = Exception("Error")

    tracks = spotify_service.get_album_tracks("alb1")

    assert tracks == []


def test_spotify_get_album_details(spotify_service):
    """Test full album details."""
    mock_album = {
        "id": "alb1",
        "name": "Full Album",
        "artists": [{"name": "Album Artist", "id": "a1"}],
        "images": [{"url": "http://alb.img"}],
        "release_date": "2024-06-15",
        "total_tracks": 12,
        "album_type": "album",
        "label": "Test Records",
    }

    spotify_service.client.album.return_value = mock_album
    spotify_service.client.album_tracks.return_value = {
        "items": [{"id": "t1", "name": "T1", "artists": [{"name": "A", "id": "a1"}], "duration_ms": 100}],
        "next": None,
    }

    details = spotify_service.get_album_details("alb1")

    assert details["title"] == "Full Album"
    assert details["artist"] == "Album Artist"
    assert details["label"] == "Test Records"
    assert len(details["tracks"]) == 1
    assert details["type"] == "album"


def test_spotify_get_album_details_no_artist(spotify_service):
    """Test album details with missing artist."""
    mock_album = {"id": "alb1", "name": "No Artist Album", "artists": [], "images": [], "total_tracks": 5}

    spotify_service.client.album.return_value = mock_album
    spotify_service.client.album_tracks.return_value = {"items": [], "next": None}

    details = spotify_service.get_album_details("alb1")

    assert details["artist"] == "Unknown Artist"
    assert details["artist_id"] is None


def test_spotify_get_album_details_no_client(spotify_service_no_client):
    """Test album details without client."""
    result = spotify_service_no_client.get_album_details("alb1")
    assert result is None


def test_spotify_get_album_details_error(spotify_service):
    """Test album details API error."""
    spotify_service.client.album.side_effect = Exception("Error")

    result = spotify_service.get_album_details("alb1")

    assert result is None


# =============================================================================
# GRUPA 6: Track formatting
# =============================================================================


def test_spotify_format_track_full(spotify_service):
    """Test formatting track with all fields."""
    item = {
        "id": "track1",
        "name": "Full Track",
        "artists": [{"name": "Artist 1", "id": "a1"}, {"name": "Artist 2", "id": "a2"}],
        "album": {"name": "Full Album", "images": [{"url": "http://cover.jpg"}]},
        "duration_ms": 210000,
        "popularity": 75,
        "external_ids": {"isrc": "USRC12345678"},
    }

    result = spotify_service._format_track(item)

    assert result["id"] == "track1"
    assert result["title"] == "Full Track"
    assert result["artist"] == "Artist 1, Artist 2"
    assert result["album"] == "Full Album"
    assert result["image_url"] == "http://cover.jpg"
    assert result["duration_ms"] == 210000
    assert result["popularity"] == 75
    assert result["isrc"] == "USRC12345678"


def test_spotify_format_track_no_album(spotify_service):
    """Test formatting track without album (simplified track)."""
    item = {
        "id": "track1",
        "name": "No Album Track",
        "artists": [{"name": "Artist", "id": "a1"}],
        "duration_ms": 180000,
    }

    result = spotify_service._format_track(item)

    assert result["album"] == "Unknown Album"
    assert result["image_url"] is None


def test_spotify_format_track_with_album_obj(spotify_service):
    """Test formatting track with album_obj parameter."""
    item = {"id": "track1", "name": "Album Track", "artists": [{"name": "Artist", "id": "a1"}], "duration_ms": 180000}
    album_obj = {"name": "Provided Album", "images": [{"url": "http://provided.jpg"}]}

    result = spotify_service._format_track(item, album_obj=album_obj)

    assert result["album"] == "Provided Album"
    assert result["image_url"] == "http://provided.jpg"


def test_spotify_format_track_no_images(spotify_service):
    """Test formatting track with empty album images."""
    item = {
        "id": "track1",
        "name": "No Image Track",
        "artists": [{"name": "Artist", "id": "a1"}],
        "album": {"name": "Album", "images": []},
        "duration_ms": 180000,
    }

    result = spotify_service._format_track(item)

    assert result["image_url"] is None


def test_spotify_format_track_no_popularity(spotify_service):
    """Test formatting track without popularity."""
    item = {
        "id": "track1",
        "name": "No Pop Track",
        "artists": [{"name": "Artist", "id": "a1"}],
        "album": {"name": "Album", "images": []},
        "duration_ms": 180000,
    }

    result = spotify_service._format_track(item)

    assert result["popularity"] == 0


# =============================================================================
# GRUPA 7: Get track
# =============================================================================


def test_spotify_get_track(spotify_service):
    """Test getting single track."""
    mock_track = {
        "id": "t1",
        "name": "Single Track",
        "artists": [{"name": "Artist", "id": "a1"}],
        "album": {"name": "Album", "images": []},
        "duration_ms": 180000,
    }
    spotify_service.client.track.return_value = mock_track

    track = spotify_service.get_track("t1")

    assert track["id"] == "t1"
    assert track["title"] == "Single Track"


def test_spotify_get_track_no_client(spotify_service_no_client):
    """Test get track without client."""
    result = spotify_service_no_client.get_track("t1")
    assert result is None


# =============================================================================
# GRUPA 8: Format helpers
# =============================================================================


def test_spotify_format_artist(spotify_service):
    """Test artist formatting."""
    item = {"id": "a1", "name": "Artist Name", "images": [{"url": "http://artist.jpg"}]}

    result = spotify_service._format_artist(item)

    assert result["id"] == "a1"
    assert result["name"] == "Artist Name"
    assert result["image_url"] == "http://artist.jpg"
    assert result["type"] == "artist"
    assert result["source"] == "spotify"


def test_spotify_format_artist_no_images(spotify_service):
    """Test artist formatting without images."""
    item = {"id": "a1", "name": "No Image Artist", "images": []}

    result = spotify_service._format_artist(item)

    assert result["image_url"] is None


def test_spotify_format_playlist(spotify_service):
    """Test playlist formatting."""
    item = {"id": "pl1", "name": "Playlist Name", "images": [{"url": "http://playlist.jpg"}], "tracks": {"total": 50}}

    result = spotify_service._format_playlist(item)

    assert result["id"] == "pl1"
    assert result["title"] == "Playlist Name"
    assert result["track_count"] == 50
    assert result["type"] == "playlist"


def test_spotify_format_playlist_as_album(spotify_service):
    """Test playlist formatting for albums."""
    item = {"id": "alb1", "name": "Album Name", "images": [], "total_tracks": 12}

    result = spotify_service._format_playlist(item, is_album=True)

    assert result["track_count"] == 12
