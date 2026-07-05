"""
Tests verifying Audiovault handles Spotify API February 2026 deprecations gracefully.

Covers:
- Removed fields: popularity, external_ids, followers, label, album_group
- Removed endpoint: /artists/{id}/top-tracks
- Search limit reduction: max 10 (was 50)
- Playlist access restrictions: other users' playlists return no tracks
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.spotify_service import SpotifyService


@pytest.fixture
def spotify_service():
    """Create a SpotifyService with a mocked httpx client."""
    with patch("app.services.spotify_service.httpx.AsyncClient"):
        service = SpotifyService()

        # We don't need to mock next, search, artist_albums anymore as we don't use spotipy
        # We just test the formatting logic here mostly
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

    @pytest.mark.asyncio
    async def test_top_tracks_api_error_returns_empty(self, spotify_service):
        """When Spotify returns an error for top tracks, return empty list gracefully."""
        with patch.object(spotify_service, "_request", return_value=None):
            result = await spotify_service.get_artist_top_tracks("artist123")
            assert result == []

    @pytest.mark.asyncio
    async def test_artist_details_still_works_without_top_tracks(self, spotify_service):
        """get_artist_details should succeed even if top tracks endpoint fails."""
        mock_artist = {"id": "ar1", "name": "Artist", "images": [{"url": "http://img"}]}

        async def mock_request(*args, **kwargs):
            endpoint = args[1] if len(args) > 1 else kwargs.get("endpoint", "")
            if "top-tracks" in endpoint:
                return None  # _request returns None on error
            if "albums" in endpoint:
                return {"items": [], "next": None}
            return mock_artist

        with patch.object(spotify_service, "_request", side_effect=mock_request):
            result = await spotify_service.get_artist_details("ar1")
            assert result is not None
            assert result["name"] == "Artist"
            assert result["tracks"] == []  # Graceful empty
            assert result["albums"] == []


# --- B3: Search limit capped to 10 ---


class TestSearchLimitCap:
    """Text search delegates to the partner GraphQL client with the given limit."""

    @pytest.mark.asyncio
    async def test_search_with_limit_above_10_delegates(self, spotify_service):
        with patch("app.services.spotify_service.partner_client.search_tracks", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            result = await spotify_service.search("test query", limit=20)
        mock_search.assert_awaited_once_with("test query", limit=20)
        assert result == []

    @pytest.mark.asyncio
    async def test_search_with_limit_5_stays_5(self, spotify_service):
        with patch("app.services.spotify_service.partner_client.search_tracks", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            result = await spotify_service.search("test", limit=5)
        mock_search.assert_awaited_once_with("test", limit=5)
        assert result == []

    @pytest.mark.asyncio
    async def test_search_default_limit_is_10_or_less(self, spotify_service):
        """Default limit stays at 10."""
        with patch("app.services.spotify_service.partner_client.search_tracks", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            result = await spotify_service.search("test")
        mock_search.assert_awaited_once_with("test", limit=10)
        assert result == []


# --- B4: Album details without label ---


class TestAlbumDetailsDeprecatedFields:
    """get_album_details must handle missing label and album_type."""

    @pytest.mark.asyncio
    async def test_album_without_label(self, spotify_service):
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

        async def mock_request(*args, **kwargs):
            endpoint = args[1] if len(args) > 1 else kwargs.get("endpoint", "")
            if "tracks" in endpoint:
                return mock_tracks
            return mock_album

        with patch.object(spotify_service, "_request", side_effect=mock_request):
            result = await spotify_service.get_album_details("al1")
            assert result is not None
            assert result["label"] is None
            assert result["album_type"] == "album"  # Default fallback

    @pytest.mark.asyncio
    async def test_album_with_album_type_present(self, spotify_service):
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

        async def mock_request(*args, **kwargs):
            endpoint = args[1] if len(args) > 1 else kwargs.get("endpoint", "")
            if "tracks" in endpoint:
                return mock_tracks
            return mock_album

        with patch.object(spotify_service, "_request", side_effect=mock_request):
            result = await spotify_service.get_album_details("al2")
            assert result["album_type"] == "single"


# --- B5: Playlist with no tracks (other user's playlist) ---


class TestPlaylistNoTracks:
    """Playlists from other users may return only metadata, no tracks."""

    @pytest.mark.asyncio
    async def test_playlist_details_empty_tracks(self, spotify_service):
        """get_playlist_details should handle playlist with no track items."""
        mock_playlist = {
            "id": "pl1",
            "name": "Other User's Playlist",
            "images": [{"url": "http://img"}],
            "tracks": {"items": [], "total": 50, "next": None},
        }
        with (
            patch("app.services.spotify_service.partner_client") as mock_partner,
            patch.object(spotify_service, "_proxy_get", new_callable=AsyncMock, return_value=None),
            patch.object(spotify_service, "_request", new_callable=AsyncMock, return_value=mock_playlist),
        ):
            mock_partner.get_playlist = AsyncMock(return_value=None)
            result = await spotify_service.get_playlist_details("pl1")
            assert result is not None
            assert result["tracks"] == []
            assert result["title"] == "Other User's Playlist"

    @pytest.mark.asyncio
    async def test_playlist_tracks_empty_items(self, spotify_service):
        """get_playlist_tracks should return empty list for restricted playlists."""
        mock_result: dict[str, Any] = {"items": [], "next": None}
        with (
            patch("app.services.spotify_service.partner_client") as mock_partner,
            patch.object(spotify_service, "_proxy_get", new_callable=AsyncMock, return_value=None),
            patch.object(spotify_service, "_request", new_callable=AsyncMock, return_value=mock_result),
        ):
            mock_partner.get_playlist = AsyncMock(return_value=None)
            result = await spotify_service.get_playlist_tracks("pl_restricted")
            assert result == []

    @pytest.mark.asyncio
    async def test_playlist_tracks_null_track_in_items(self, spotify_service):
        """Some items may have null 'track' field — should be skipped."""
        mock_result = {
            "id": "pl1",
            "name": "PL",
            "images": [],
            "tracks": {
                "total": 2,
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
            },
        }
        with (
            patch("app.services.spotify_service.partner_client") as mock_partner,
            patch.object(spotify_service, "_proxy_get", new_callable=AsyncMock, return_value=None),
            patch.object(spotify_service, "_request", new_callable=AsyncMock, return_value=mock_result),
        ):
            mock_partner.get_playlist = AsyncMock(return_value=None)
            result = await spotify_service.get_playlist_tracks("pl1")
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
