"""
Tests for MusicBrainzProvider — TDD Red Phase.
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.providers.musicbrainz_provider import MusicBrainzProvider
from app.schemas.metadata import TrackMetadata


@pytest.fixture
def provider() -> MusicBrainzProvider:
    return MusicBrainzProvider()


# --- can_handle Tests ---


def test_can_handle_musicbrainz_url(provider: MusicBrainzProvider):
    """Should handle musicbrainz.org URLs."""
    assert provider.can_handle("https://musicbrainz.org/recording/some-mbid") is True
    assert provider.can_handle("https://musicbrainz.org/artist/some-mbid") is True


def test_cannot_handle_other_urls(provider: MusicBrainzProvider):
    """Should not handle non-MusicBrainz URLs."""
    assert provider.can_handle("https://open.spotify.com/track/123") is False
    assert provider.can_handle("https://www.youtube.com/watch?v=abc") is False
    assert provider.can_handle("https://deezer.com/track/456") is False


# --- Properties Tests ---


def test_name_is_musicbrainz(provider: MusicBrainzProvider):
    assert provider.name == "musicbrainz"


def test_domains_contain_musicbrainz(provider: MusicBrainzProvider):
    assert "musicbrainz.org" in provider.domains


# --- get_track Tests ---


@pytest.mark.asyncio
async def test_get_track_by_mbid_url(provider: MusicBrainzProvider):
    """Should extract track metadata from a MusicBrainz recording URL."""
    mock_recording = {
        "id": "rec-mbid-1",
        "title": "Smells Like Teen Spirit",
        "artist": "Nirvana",
        "album": "Nevermind",
        "duration_ms": 301000,
        "image_url": None,
        "source": "musicbrainz",
        "isrc": "USGF19942501",
        "release_mbid": "release-mbid-1",
        "score": 100,
    }

    mock_cover = "https://coverartarchive.org/release/release-mbid-1/500.jpg"

    with (
        patch.object(provider.service, "search_track", new_callable=AsyncMock) as mock_search,
        patch.object(provider.service, "get_cover_art", new_callable=AsyncMock) as mock_art,
    ):
        mock_search.return_value = [mock_recording]
        mock_art.return_value = mock_cover

        result = await provider.get_track("https://musicbrainz.org/recording/rec-mbid-1")

    assert result is not None
    assert isinstance(result, TrackMetadata)
    assert result.title == "Smells Like Teen Spirit"
    assert result.artist == "Nirvana"
    assert result.source == "musicbrainz"
    assert result.isrc == "USGF19942501"


@pytest.mark.asyncio
async def test_get_track_returns_none_for_no_results(provider: MusicBrainzProvider):
    """Should return None when no recording is found."""
    with patch.object(provider.service, "search_track", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = []

        result = await provider.get_track("https://musicbrainz.org/recording/nonexistent")

    assert result is None


# --- extract_playlist Tests ---


@pytest.mark.asyncio
async def test_extract_playlist_returns_none(provider: MusicBrainzProvider):
    """MusicBrainz doesn't have playlists — should return None."""
    result = await provider.extract_playlist("https://musicbrainz.org/something")
    assert result is None
