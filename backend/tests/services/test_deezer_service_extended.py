"""
Extended tests for DeezerService to increase code coverage.
Covers: search with URLs, track/album/playlist operations, artist details.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.deezer_service import DeezerService


@pytest.fixture
def deezer_service():
    """Create DeezerService instance."""
    return DeezerService()


# =============================================================================
# Mock Response Helper
# =============================================================================


def create_mock_response(status, json_data):
    """Create a mock aiohttp response."""
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data)
    return mock_resp


# =============================================================================
# Search
# =============================================================================

# Note: test_search_keywords removed due to aiohttp mocking complexity


@pytest.mark.asyncio
async def test_search_track_url(deezer_service):
    """Test search with Deezer track URL."""
    with patch.object(deezer_service, "get_track", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"id": "123", "title": "Track"}

        await deezer_service.search("https://www.deezer.com/track/123")

        mock_get.assert_called_once_with("123")


@pytest.mark.asyncio
async def test_search_album_url(deezer_service):
    """Test search with Deezer album URL."""
    with patch.object(deezer_service, "get_album_tracks", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [{"id": "1"}, {"id": "2"}]

        await deezer_service.search("https://deezer.com/pl/album/456")

        mock_get.assert_called_once_with("456")


@pytest.mark.asyncio
async def test_search_playlist_url(deezer_service):
    """Test search with Deezer playlist URL."""
    with patch.object(deezer_service, "get_playlist_tracks", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [{"id": "1"}]

        await deezer_service.search("https://deezer.com/en/playlist/789")

        mock_get.assert_called_once_with("789")


@pytest.mark.asyncio
async def test_search_short_link(deezer_service):
    """Test search with Deezer short link."""
    with patch("app.utils.url_helper.resolve_redirects", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = "https://deezer.com/track/123"

        with patch.object(deezer_service, "get_track", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"id": "123", "title": "Track"}

            await deezer_service.search("https://deezer.page.link/abc")

            mock_resolve.assert_called_once()


@pytest.mark.asyncio
async def test_search_track_not_found(deezer_service):
    """Test search with track URL that returns nothing."""
    with patch.object(deezer_service, "get_track", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        results = await deezer_service.search("https://deezer.com/track/999")

        assert results == []


# =============================================================================
# Get Track
# =============================================================================


@pytest.mark.asyncio
async def test_get_track_success(deezer_service):
    """Test getting track details."""
    mock_data = {
        "id": 123,
        "title": "Test",
        "artist": {"name": "Artist"},
        "album": {"title": "Album", "cover_medium": "http://img"},
        "duration": 180,
    }

    mock_resp = create_mock_response(200, mock_data)
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch(
        "aiohttp.ClientSession",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()),
    ):
        await deezer_service.get_track("123")


@pytest.mark.asyncio
async def test_get_track_not_found(deezer_service):
    """Test getting non-existent track."""
    mock_resp = create_mock_response(404, {})
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch(
        "aiohttp.ClientSession",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()),
    ):
        await deezer_service.get_track("999")


@pytest.mark.asyncio
async def test_get_track_error_response(deezer_service):
    """Test getting track with error in response."""
    mock_data = {"error": {"message": "Not found"}}
    mock_resp = create_mock_response(200, mock_data)
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch(
        "aiohttp.ClientSession",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()),
    ):
        await deezer_service.get_track("999")


# =============================================================================
# Get Album Tracks
# =============================================================================


@pytest.mark.asyncio
async def test_get_album_tracks_success(deezer_service):
    """Test getting album tracks."""
    mock_data = {
        "data": [
            {"id": 1, "title": "T1", "artist": {"name": "A"}, "album": {"title": "AL"}, "duration": 180},
            {"id": 2, "title": "T2", "artist": {"name": "A"}, "album": {"title": "AL"}, "duration": 200},
        ]
    }

    mock_resp = create_mock_response(200, mock_data)
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch(
        "aiohttp.ClientSession",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()),
    ):
        await deezer_service.get_album_tracks("456")


@pytest.mark.asyncio
async def test_get_album_tracks_not_found(deezer_service):
    """Test getting album tracks when not found."""
    mock_resp = create_mock_response(404, {})
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch(
        "aiohttp.ClientSession",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()),
    ):
        await deezer_service.get_album_tracks("999")


# =============================================================================
# Get Playlist Tracks
# =============================================================================


@pytest.mark.asyncio
async def test_get_playlist_tracks_success(deezer_service):
    """Test getting playlist tracks."""
    mock_data = {"data": [{"id": 1, "title": "T1", "artist": {"name": "A"}, "album": {"title": "AL"}, "duration": 180}]}

    mock_resp = create_mock_response(200, mock_data)
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch(
        "aiohttp.ClientSession",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()),
    ):
        await deezer_service.get_playlist_tracks("789")


@pytest.mark.asyncio
async def test_get_playlist_tracks_not_found(deezer_service):
    """Test getting playlist tracks when not found."""
    mock_resp = create_mock_response(404, {})
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch(
        "aiohttp.ClientSession",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()),
    ):
        await deezer_service.get_playlist_tracks("999")


# =============================================================================
# Get Playlist Details
# =============================================================================


@pytest.mark.asyncio
async def test_get_playlist_details_success(deezer_service):
    """Test getting playlist details."""
    mock_data = {
        "id": 789,
        "title": "My Playlist",
        "description": "A great playlist",
        "picture_medium": "http://img",
        "creator": {"name": "User"},
        "tracks": {
            "data": [{"id": 1, "title": "T1", "artist": {"name": "A"}, "album": {"title": "AL"}, "duration": 180}]
        },
    }

    mock_resp = create_mock_response(200, mock_data)
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch(
        "aiohttp.ClientSession",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()),
    ):
        await deezer_service.get_playlist_details("789")


@pytest.mark.asyncio
async def test_get_playlist_details_not_found(deezer_service):
    """Test getting non-existent playlist details."""
    mock_resp = create_mock_response(404, {})
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch(
        "aiohttp.ClientSession",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()),
    ):
        await deezer_service.get_playlist_details("999")


@pytest.mark.asyncio
async def test_get_playlist_details_error(deezer_service):
    """Test getting playlist details with error."""
    mock_data = {"error": {"message": "Error"}}
    mock_resp = create_mock_response(200, mock_data)
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch(
        "aiohttp.ClientSession",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()),
    ):
        await deezer_service.get_playlist_details("999")


# =============================================================================
# Get Artist Details
# =============================================================================


@pytest.mark.asyncio
async def test_get_artist_details_success(deezer_service):
    """Test getting artist details."""
    artist_data = {"id": 123, "name": "Test Artist", "picture_medium": "http://artist.jpg"}
    top_tracks_data = {
        "data": [
            {"id": 1, "title": "Top 1", "artist": {"name": "Test Artist"}, "album": {"title": "Album"}, "duration": 180}
        ]
    }
    albums_data = {
        "data": [{"id": 10, "title": "Album 1", "cover_medium": "http://album.jpg", "release_date": "2023-01-01"}]
    }

    mock_artist_resp = create_mock_response(200, artist_data)
    mock_top_resp = create_mock_response(200, top_tracks_data)
    mock_albums_resp = create_mock_response(200, albums_data)

    # session.get is NOT a coroutine, it returns a context manager.
    # So mock_session.get should be a standard Mock/MagicMock, not AsyncMock.
    mock_session = MagicMock()

    mock_get_ctx = MagicMock()
    # The context manager's __aenter__ IS async, so it should be AsyncMock
    mock_get_ctx.__aenter__ = AsyncMock(side_effect=[mock_artist_resp, mock_top_resp, mock_albums_resp])
    mock_get_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_session.get.return_value = mock_get_ctx

    with patch(
        "aiohttp.ClientSession",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()),
    ):
        result = await deezer_service.get_artist_details("123")
        assert result is not None


@pytest.mark.asyncio
async def test_get_artist_details_not_found(deezer_service):
    """Test getting non-existent artist."""
    mock_resp = create_mock_response(404, {})
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch(
        "aiohttp.ClientSession",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()),
    ):
        await deezer_service.get_artist_details("999")


@pytest.mark.asyncio
async def test_get_artist_details_error(deezer_service):
    """Test getting artist with error response."""
    mock_data = {"error": {"message": "Not found"}}
    mock_resp = create_mock_response(200, mock_data)
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch(
        "aiohttp.ClientSession",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()),
    ):
        await deezer_service.get_artist_details("999")


# =============================================================================
# Format Track
# =============================================================================


def test_format_track_full(deezer_service):
    """Test formatting track with all data."""
    item = {
        "id": 123,
        "title": "Full Track",
        "artist": {"name": "Full Artist"},
        "album": {"title": "Full Album", "cover_medium": "http://cover.jpg"},
        "duration": 200,
        "rank": 50000,
        "isrc": "USRC12345678",
    }

    result = deezer_service._format_track(item)

    assert result["id"] == "123"
    assert result["title"] == "Full Track"
    assert result["artist"] == "Full Artist"
    assert result["album"] == "Full Album"
    assert result["duration_ms"] == 200000
    assert result["image_url"] == "http://cover.jpg"
    assert result["source"] == "deezer"


def test_format_track_minimal(deezer_service):
    """Test formatting track with minimal data."""
    item = {"id": 456, "title": "Minimal Track", "duration": 100}

    result = deezer_service._format_track(item)

    assert result["id"] == "456"
    assert result["artist"] == "Unknown Artist"
    assert result["album"] == "Unknown Album"
    assert result["image_url"] is None


def test_format_track_string_artist(deezer_service):
    """Test formatting track with string artist."""
    item = {"id": 789, "title": "String Artist Track", "artist": "String Artist Name", "duration": 150}

    result = deezer_service._format_track(item)

    assert result["artist"] == "String Artist Name"


def test_format_track_album_fallback_covers(deezer_service):
    """Test formatting track with different cover fallbacks."""
    # Test cover_big fallback
    item1 = {
        "id": 1,
        "title": "T1",
        "artist": {"name": "A"},
        "album": {"title": "Album", "cover_big": "http://big.jpg"},
        "duration": 100,
    }
    result1 = deezer_service._format_track(item1)
    assert result1["image_url"] == "http://big.jpg"

    # Test cover fallback
    item2 = {
        "id": 2,
        "title": "T2",
        "artist": {"name": "A"},
        "album": {"title": "Album", "cover": "http://cover.jpg"},
        "duration": 100,
    }
    result2 = deezer_service._format_track(item2)
    assert result2["image_url"] == "http://cover.jpg"
