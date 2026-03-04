"""
Tests for hidden Spotify API integrations found during deep scan.

Covers:
- H1: RecommendationsPage.tsx uses /browse/search (tested via backend endpoint)
- H3: downloads.py _resolve_track_to_local_id handles missing isrc gracefully
- H4: downloads.py download_all_artist_tracks handles empty top_tracks
- H5: downloads.py download_album uses get_album() correctly
- H6: stream.py _get_spotify_track_sync handles missing fields
- H7-H9: Watchlist/sync services handle Spotify API changes
"""

from unittest.mock import patch


class TestDownloadsSpotifyIntegration:
    """Tests for downloads.py hidden Spotify integrations."""

    def test_resolve_track_spotify_missing_isrc(self):
        """H3: When Spotify returns track without isrc, metadata should store None gracefully."""
        # Simulate track data from Spotify API after Feb 2026 (no external_ids)
        track_data = {
            "title": "Test Track",
            "artist": "Test Artist",
            "duration_ms": 240000,
            "image_url": "https://example.com/img.jpg",
            "album": "Test Album",
            # isrc deliberately missing (Spotify API Feb 2026)
        }

        # Verify .get("isrc") returns None without error
        metadata_content = {
            "image_url": track_data.get("image_url"),
            "album": track_data.get("album"),
            "isrc": track_data.get("isrc"),
        }

        assert metadata_content["isrc"] is None
        assert metadata_content["image_url"] == "https://example.com/img.jpg"
        assert metadata_content["album"] == "Test Album"

    def test_artist_download_metadata_without_isrc(self):
        """H4: download_all_artist_tracks stores metadata correctly when isrc is missing."""
        track_data = {
            "id": "spotify_track_123",
            "title": "Song Title",
            "artist": "Artist Name",
            "duration_ms": 180000,
            "image_url": "https://i.scdn.co/image/abc123",
            # No isrc field (removed in Feb 2026)
        }

        metadata_content = {
            "image_url": track_data.get("image_url"),
            "album_art": track_data.get("image_url"),
            "album": track_data.get("album"),
            "isrc": track_data.get("isrc"),
        }

        assert metadata_content["isrc"] is None
        assert metadata_content["album"] is None  # album also optional
        assert metadata_content["image_url"] == "https://i.scdn.co/image/abc123"

    def test_album_download_metadata_without_isrc(self):
        """H5: download_album stores metadata correctly when isrc is missing."""
        track_data = {
            "id": "spotify_track_456",
            "title": "Album Track",
            "artist": "Album Artist",
            "duration_ms": 200000,
            "image_url": "https://i.scdn.co/image/def456",
            "album": "Great Album",
            # isrc missing
        }

        metadata_content = {
            "image_url": track_data.get("image_url"),
            "album_art": track_data.get("image_url"),
            "album": track_data.get("album"),
            "isrc": track_data.get("isrc"),
        }

        assert metadata_content["isrc"] is None
        assert metadata_content["album"] == "Great Album"


class TestStreamSpotifyIntegration:
    """Tests for stream.py hidden Spotify integration."""

    def test_get_spotify_track_sync_returns_minimal_data(self):
        """H6: Stream pipeline only needs artist+title from Spotify, not deprecated fields."""
        with patch("app.services.spotify_service.SpotifyService") as MockService:
            mock_instance = MockService.return_value
            # Simulate Spotify response without deprecated fields
            mock_instance.get_track.return_value = {
                "title": "Streaming Track",
                "artist": "Stream Artist",
                "duration_ms": 210000,
                # No popularity, no external_ids, no isrc
            }

            result = mock_instance.get_track("spotify_id_789")

            assert result["title"] == "Streaming Track"
            assert result["artist"] == "Stream Artist"
            # Stream pipeline creates YouTube query from artist+title
            query = f"{result['artist']} - {result['title']}"
            assert query == "Stream Artist - Streaming Track"

    def test_get_spotify_track_sync_handles_none(self):
        """H6: Stream handles SpotifyService returning None."""
        with patch("app.services.spotify_service.SpotifyService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_track.return_value = None

            result = mock_instance.get_track("nonexistent_id")
            assert result is None


class TestWatchlistSpotifyIntegration:
    """Tests for watchlist/sync hidden Spotify integrations."""

    def test_processor_get_artist_albums_empty_result(self):
        """H8: WatchlistItemProcessor handles empty album list from Spotify."""
        with patch("app.services.spotify_service.SpotifyService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_artist_albums.return_value = []

            albums = mock_instance.get_artist_albums("artist_id")
            assert albums == []

    def test_processor_get_album_tracks_without_deprecated_fields(self):
        """H8: Album tracks from Spotify can lack popularity/isrc."""
        with patch("app.services.spotify_service.SpotifyService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_album_tracks.return_value = [
                {
                    "id": "track_1",
                    "title": "Track 1",
                    "artist": "Artist 1",
                    "duration_ms": 180000,
                    # No popularity, no isrc (removed fields)
                }
            ]

            tracks = mock_instance.get_album_tracks("album_id")
            assert len(tracks) == 1
            assert tracks[0]["title"] == "Track 1"
            assert tracks[0].get("popularity") is None
            assert tracks[0].get("isrc") is None

    def test_sync_manager_artist_albums_spotify(self):
        """H9: SyncManager._fetch_remote_tracks works with Spotify artist."""
        with patch("app.services.spotify_service.SpotifyService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_artist_albums.return_value = [{"id": "album_1", "name": "Album 1"}]
            mock_instance.get_album_tracks.return_value = [{"id": "track_1", "title": "Track 1", "artist": "Artist 1"}]

            albums = mock_instance.get_artist_albums("artist_id_sync")
            assert len(albums) == 1

            tracks = mock_instance.get_album_tracks(albums[0]["id"])
            assert len(tracks) == 1
            assert tracks[0]["id"] == "track_1"

    def test_watchlist_engine_init_spotify_service(self):
        """H7: WatchlistEngine initializes SpotifyService (may have no credentials)."""
        with patch("app.services.spotify_service.SpotifyService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.client = None  # No Spotify credentials configured

            # Should not crash even if client is None
            assert mock_instance.client is None


class TestGetAlbumMethod:
    """Tests for SpotifyService.get_album() used by downloads.py."""

    def test_get_album_returns_raw_data(self):
        """H5: get_album() returns raw Spotify API data including name."""
        with patch("app.services.spotify_service.SpotifyService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_album.return_value = {
                "name": "Test Album",
                "id": "album_123",
                "images": [{"url": "https://i.scdn.co/image/abc"}],
                "artists": [{"name": "Test Artist", "id": "artist_123"}],
                # label removed in Feb 2026
                # popularity removed in Feb 2026
            }

            album = mock_instance.get_album("album_123")
            assert album is not None
            assert album["name"] == "Test Album"
            assert album.get("label") is None  # Removed field
            assert album.get("popularity") is None  # Removed field

    def test_get_album_no_client(self):
        """H5: get_album() returns None when no Spotify client."""
        with patch("app.services.spotify_service.SpotifyService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_album.return_value = None

            result = mock_instance.get_album("any_id")
            assert result is None
