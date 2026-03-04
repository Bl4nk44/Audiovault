"""
Tests verifying Audiovault handles Spotify API February 2026 deprecations gracefully.

Covers:
- Removed fields: popularity, external_ids, followers, label, album_group
- Removed endpoint: /artists/{id}/top-tracks
- Search limit reduction: max 10 (was 50)
- Playlist access restrictions: other users' playlists return no tracks
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from app.services.spotify_service import SpotifyService


@pytest.fixture
def spotify_service():
    """Create a SpotifyService with a mocked spotipy client."""
    with (
        patch("app.services.spotify_service.spotipy.Spotify"),
        patch("app.services.spotify_service.SpotifyClientCredentials"),
    ):
        service = SpotifyService()
        mock_client = MagicMock()
        safe_paginated: dict[str, Any] = {
            "items": [],
            "next": None,
            "tracks": {"items": [], "next": None},
        }
        mock_client.next.return_value = {"next": None, "items": []}
        mock_client.search.return_value = safe_paginated
        mock_client.artist_albums.return_value = safe_paginated
        mock_client.artist_top_tracks.return_value = {"tracks": []}
        mock_client.album_tracks.return_value = safe_paginated
        mock_client.playlist_tracks.return_value = safe_paginated
        service.client = mock_client
        return service


# --- B2: Track format with deprecated fields removed ---


class TestFormatTrackDeprecatedFields:
    """_format_track must handle missing popularity and external_ids."""

    def test_track_without_popularity(self, spotify_service):
        """Track response without 'popularity' field should default to 0."""
        item = {
            "id": "t1",
            "name": "Song",
            "artists": [{"name": "Artist", "id": "a1"}],
            "album": {"name": "Album", "images": [{"url": "http://img"}]},
            "duration_ms": 200000,
            # No 'popularity' key at all
        }
        result = spotify_service._format_track(item)
        assert result["popularity"] == 0
        assert result["title"] == "Song"

    def test_track_without_external_ids(self, spotify_service):
        """Track response without 'external_ids' should return isrc=None."""
        item = {
            "id": "t2",
            "name": "Another Song",
            "artists": [{"name": "Artist", "id": "a1"}],
            "album": {"name": "Album", "images": []},
            "duration_ms": 180000,
            # No 'external_ids' key at all
        }
        result = spotify_service._format_track(item)
        assert result["isrc"] is None

    def test_track_without_both_deprecated_fields(self, spotify_service):
        """Track without both popularity AND external_ids still formats correctly."""
        item = {
            "id": "t3",
            "name": "Minimal Track",
            "artists": [{"name": "A", "id": "a1"}],
            "album": {"name": "AL", "images": []},
            "duration_ms": 100000,
        }
        result = spotify_service._format_track(item)
        assert result["popularity"] == 0
        assert result["isrc"] is None
        assert result["title"] == "Minimal Track"
        assert result["artist"] == "A"


# --- B1: get_artist_top_tracks removed endpoint ---


class TestArtistTopTracksRemoved:
    """get_artist_top_tracks must handle the removed /artists/{id}/top-tracks endpoint."""

    def test_top_tracks_api_error_returns_empty(self, spotify_service):
        """When Spotify returns an error for top tracks, return empty list gracefully."""
        spotify_service.client.artist_top_tracks.side_effect = Exception(
            "HTTP 404: Not Found - /artists/{id}/top-tracks has been removed"
        )
        result = spotify_service.get_artist_top_tracks("artist123")
        assert result == []

    def test_artist_details_still_works_without_top_tracks(self, spotify_service):
        """get_artist_details should succeed even if top tracks endpoint fails."""
        mock_artist = {"id": "ar1", "name": "Artist", "images": [{"url": "http://img"}]}
        spotify_service.client.artist.return_value = mock_artist
        spotify_service.client.artist_top_tracks.side_effect = Exception("Endpoint removed")
        spotify_service.client.artist_albums.return_value = {"items": [], "next": None}

        result = spotify_service.get_artist_details("ar1")
        assert result is not None
        assert result["name"] == "Artist"
        assert result["tracks"] == []  # Graceful empty
        assert result["albums"] == []


# --- B3: Search limit capped to 10 ---


class TestSearchLimitCap:
    """search() must cap limit to Spotify's new maximum of 10."""

    def test_search_with_limit_above_10_is_capped(self, spotify_service):
        """Passing limit=20 should internally call Spotify with limit=10."""
        spotify_service.client.search.return_value = {"tracks": {"items": []}}
        spotify_service.search("test query", limit=20)

        # Verify the actual call to Spotify API was capped at 10
        call_args = spotify_service.client.search.call_args
        assert call_args[1]["limit"] <= 10 or call_args.kwargs.get("limit", 20) <= 10

    def test_search_with_limit_5_stays_5(self, spotify_service):
        """Passing limit=5 (under max) should pass through unchanged."""
        spotify_service.client.search.return_value = {"tracks": {"items": []}}
        spotify_service.search("test", limit=5)

        call_args = spotify_service.client.search.call_args
        # Should be called with limit=5 (not capped)
        assert call_args[1].get("limit", call_args[0][1] if len(call_args[0]) > 1 else None) in [5, None]

    def test_search_default_limit_is_10_or_less(self, spotify_service):
        """Default limit should be at most 10 after the change."""
        spotify_service.client.search.return_value = {"tracks": {"items": []}}
        spotify_service.search("test")

        call_args = spotify_service.client.search.call_args
        # The limit kwarg should be <= 10
        actual_limit = call_args.kwargs.get("limit") or call_args[1].get("limit")
        assert actual_limit is not None
        assert actual_limit <= 10


# --- B4: Album details without label ---


class TestAlbumDetailsDeprecatedFields:
    """get_album_details must handle missing label and album_type."""

    def test_album_without_label(self, spotify_service):
        """Album response without 'label' should return None for label."""
        mock_album = {
            "id": "al1",
            "name": "Album",
            "artists": [{"name": "Artist", "id": "a1"}],
            "images": [{"url": "http://img"}],
            "release_date": "2025-01-01",
            "total_tracks": 10,
            # No 'label' key
            # No 'album_type' key
        }
        mock_tracks: dict[str, Any] = {"items": [], "next": None}
        spotify_service.client.album.return_value = mock_album
        spotify_service.client.album_tracks.return_value = mock_tracks

        result = spotify_service.get_album_details("al1")
        assert result is not None
        assert result["label"] is None
        assert result["album_type"] == "album"  # Default fallback

    def test_album_with_album_type_present(self, spotify_service):
        """If album_type is still present, it should be used."""
        mock_album = {
            "id": "al2",
            "name": "Single",
            "artists": [{"name": "Artist", "id": "a1"}],
            "images": [],
            "album_type": "single",
            "total_tracks": 1,
        }
        mock_tracks: dict[str, Any] = {"items": [], "next": None}
        spotify_service.client.album.return_value = mock_album
        spotify_service.client.album_tracks.return_value = mock_tracks

        result = spotify_service.get_album_details("al2")
        assert result["album_type"] == "single"


# --- B5: Playlist with no tracks (other user's playlist) ---


class TestPlaylistNoTracks:
    """Playlists from other users may return only metadata, no tracks."""

    def test_playlist_details_empty_tracks(self, spotify_service):
        """get_playlist_details should handle playlist with no track items."""
        mock_playlist = {
            "id": "pl1",
            "name": "Other User's Playlist",
            "images": [{"url": "http://img"}],
            "tracks": {"items": [], "total": 50, "next": None},
        }
        spotify_service.client.playlist.return_value = mock_playlist

        result = spotify_service.get_playlist_details("pl1")
        assert result is not None
        assert result["tracks"] == []
        assert result["title"] == "Other User's Playlist"

    def test_playlist_tracks_empty_items(self, spotify_service):
        """get_playlist_tracks should return empty list for restricted playlists."""
        mock_result: dict[str, Any] = {"items": [], "next": None}
        spotify_service.client.playlist_tracks.return_value = mock_result

        result = spotify_service.get_playlist_tracks("pl_restricted")
        assert result == []

    def test_playlist_tracks_null_track_in_items(self, spotify_service):
        """Some items may have null 'track' field — should be skipped."""
        mock_result = {
            "items": [
                {"track": None},
                {
                    "track": {
                        "id": "t1",
                        "name": "Valid",
                        "artists": [{"name": "A", "id": "a1"}],
                        "album": {"name": "AL", "images": []},
                        "duration_ms": 100,
                    }
                },
            ],
            "next": None,
        }
        spotify_service.client.playlist_tracks.return_value = mock_result

        result = spotify_service.get_playlist_tracks("pl1")
        assert len(result) == 1
        assert result[0]["title"] == "Valid"


# --- B7: SearchOrchestrator limit capping ---


class TestSearchOrchestratorLimitCap:
    """SearchOrchestrator._search_spotify must cap limit to 10."""

    @pytest.mark.asyncio
    async def test_search_spotify_caps_limit(self):
        """_search_spotify should pass at most limit=10 to SpotifyService.search."""
        with (
            patch("app.services.search_orchestrator.DeezerService"),
            patch("app.services.search_orchestrator.MusicBrainzService"),
            patch("app.services.search_orchestrator.SpotifyService") as mock_sp_cls,
        ):
            from app.services.search_orchestrator import SearchOrchestrator

            mock_sp = MagicMock()
            mock_sp.client = MagicMock()
            mock_sp.search.return_value = []
            mock_sp_cls.return_value = mock_sp

            orchestrator = SearchOrchestrator()
            await orchestrator._search_spotify("test query", limit=50)

            mock_sp.search.assert_called_once()
            call_kwargs = mock_sp.search.call_args
            # Limit should be capped to 10
            actual_limit = call_kwargs.kwargs.get("limit") or call_kwargs[1].get("limit")
            assert actual_limit <= 10
