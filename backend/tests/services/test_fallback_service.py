"""
Tests for FallbackService to improve coverage.
"""

from unittest.mock import MagicMock

import pytest
from app.services.fallback_service import FallbackService


@pytest.fixture
def service():
    return FallbackService()


@pytest.fixture
def mock_track():
    track = MagicMock()
    track.artist = "Artist"
    track.title = "Title"
    return track


# =============================================================================
# Streaming Service Strategy (Spotify, Deezer, Tidal, etc.)
# =============================================================================


def test_streaming_service_attempt_1(service, mock_track):
    """Test first attempt for Spotify uses official video search."""
    result = service.get_fallback_instruction("spotify", 1, mock_track)
    assert result["type"] == "yt_search"
    assert "official video" in result["value"]


def test_streaming_service_attempt_2(service, mock_track):
    """Test second attempt for Spotify uses audio search."""
    result = service.get_fallback_instruction("spotify", 2, mock_track)
    assert result["type"] == "yt_search"
    assert "audio" in result["value"]


def test_streaming_service_attempt_3(service, mock_track):
    """Test third attempt for Spotify uses SoundCloud."""
    result = service.get_fallback_instruction("spotify", 3, mock_track)
    assert result["type"] == "sc_search"


def test_streaming_service_attempt_4(service, mock_track):
    """Test fourth attempt uses generic YT search."""
    result = service.get_fallback_instruction("spotify", 4, mock_track)
    assert result["type"] == "yt_search"


def test_streaming_service_attempt_5_none(service, mock_track):
    """Test attempt beyond max returns none."""
    result = service.get_fallback_instruction("spotify", 5, mock_track)
    assert result["type"] == "none"


# =============================================================================
# YouTube Strategy
# =============================================================================


def test_youtube_attempt_1(service, mock_track):
    """Test first YouTube attempt is direct."""
    result = service.get_fallback_instruction("youtube", 1, mock_track)
    assert result["type"] == "direct_youtube"


def test_youtube_attempt_2(service, mock_track):
    """Test second YouTube attempt uses SoundCloud."""
    result = service.get_fallback_instruction("youtube", 2, mock_track)
    assert result["type"] == "sc_search"


def test_youtube_attempt_3(service, mock_track):
    """Test third YouTube attempt uses YT search."""
    result = service.get_fallback_instruction("youtube", 3, mock_track)
    assert result["type"] == "yt_search"


def test_youtube_attempt_4_none(service, mock_track):
    """Test YouTube beyond max returns none."""
    result = service.get_fallback_instruction("youtube", 4, mock_track)
    assert result["type"] == "none"


# =============================================================================
# SoundCloud Strategy
# =============================================================================


def test_soundcloud_attempt_1(service, mock_track):
    """Test first SoundCloud attempt is direct."""
    result = service.get_fallback_instruction("soundcloud", 1, mock_track)
    assert result["type"] == "direct_soundcloud"


def test_soundcloud_attempt_2(service, mock_track):
    """Test second SoundCloud attempt uses SC search."""
    result = service.get_fallback_instruction("soundcloud", 2, mock_track)
    assert result["type"] == "sc_search"


def test_soundcloud_attempt_3(service, mock_track):
    """Test third SoundCloud attempt uses YT search."""
    result = service.get_fallback_instruction("soundcloud", 3, mock_track)
    assert result["type"] == "yt_search"


def test_soundcloud_attempt_4_none(service, mock_track):
    """Test SoundCloud beyond max returns none."""
    result = service.get_fallback_instruction("soundcloud", 4, mock_track)
    assert result["type"] == "none"


# =============================================================================
# Unknown Source
# =============================================================================


def test_unknown_source(service, mock_track):
    """Test unknown source returns none."""
    result = service.get_fallback_instruction("unknown_service", 1, mock_track)
    assert result["type"] == "none"


def test_no_track_metadata(service):
    """Test handling of None track metadata."""
    result = service.get_fallback_instruction("spotify", 1, None)
    assert result["type"] == "yt_search"
    assert "Unknown" in result["value"]


# =============================================================================
# Other Streaming Services (Apple Music, Tidal, etc.)
# =============================================================================


def test_apple_music_uses_streaming_strategy(service, mock_track):
    """Test Apple Music uses the same strategy as Spotify."""
    result = service.get_fallback_instruction("apple_music", 1, mock_track)
    assert result["type"] == "yt_search"


def test_deezer_uses_streaming_strategy(service, mock_track):
    """Test Deezer uses the same strategy as Spotify."""
    result = service.get_fallback_instruction("deezer", 1, mock_track)
    assert result["type"] == "yt_search"


def test_tidal_uses_streaming_strategy(service, mock_track):
    """Test Tidal uses the same strategy as Spotify."""
    result = service.get_fallback_instruction("tidal", 1, mock_track)
    assert result["type"] == "yt_search"


def test_amazon_uses_streaming_strategy(service, mock_track):
    """Test Amazon Music uses the same strategy as Spotify."""
    result = service.get_fallback_instruction("amazon_music", 1, mock_track)
    assert result["type"] == "yt_search"


def test_imported_uses_streaming_strategy(service, mock_track):
    """Test imported source uses streaming strategy."""
    result = service.get_fallback_instruction("imported", 1, mock_track)
    assert result["type"] == "yt_search"
