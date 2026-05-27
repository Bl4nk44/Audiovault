"""
Tests for SearchOrchestrator — TDD Red Phase.

Covers:
- multi-source search aggregation
- deduplication by ISRC and title+artist
- scoring algorithm
- fallback behavior when providers fail
- Spotify optional (works without it)
- track/artist/album details delegation
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.search_orchestrator import SearchOrchestrator

# --- Fixtures ---


@pytest.fixture
def orchestrator() -> SearchOrchestrator:
    return SearchOrchestrator()


# --- Mock Data ---

DEEZER_RESULTS = [
    {
        "id": "dz-123",
        "title": "Smells Like Teen Spirit",
        "artist": "Nirvana",
        "album": "Nevermind",
        "duration_ms": 301000,
        "image_url": "https://deezer.com/img/123.jpg",
        "source": "deezer",
        "isrc": "USGF19942501",
        "popularity": 950000,
    },
    {
        "id": "dz-456",
        "title": "Come As You Are",
        "artist": "Nirvana",
        "album": "Nevermind",
        "duration_ms": 218000,
        "image_url": "https://deezer.com/img/456.jpg",
        "source": "deezer",
        "isrc": "USGF19942502",
        "popularity": 800000,
    },
]

MUSICBRAINZ_RESULTS = [
    {
        "id": "mb-rec-1",
        "title": "Smells Like Teen Spirit",
        "artist": "Nirvana",
        "album": "Nevermind",
        "duration_ms": 301000,
        "image_url": None,
        "source": "musicbrainz",
        "isrc": "USGF19942501",
        "score": 100,
    },
    {
        "id": "mb-rec-2",
        "title": "In Bloom",
        "artist": "Nirvana",
        "album": "Nevermind",
        "duration_ms": 254000,
        "image_url": None,
        "source": "musicbrainz",
        "isrc": "USGF19942503",
        "score": 85,
    },
]

SPOTIFY_RESULTS = [
    {
        "id": "sp-abc",
        "title": "Smells Like Teen Spirit",
        "artist": "Nirvana",
        "album": "Nevermind",
        "duration_ms": 301000,
        "image_url": "https://i.scdn.co/image/abc.jpg",
        "source": "spotify",
        "isrc": "USGF19942501",
        "popularity": 90,
    },
]


# --- Multi-Source Search Tests ---


@pytest.mark.asyncio
async def test_search_tracks_aggregates_sources(orchestrator: SearchOrchestrator):
    """Should aggregate results from multiple providers."""
    with (
        patch.object(orchestrator, "_search_deezer", new_callable=AsyncMock) as mock_dz,
        patch.object(orchestrator, "_search_musicbrainz", new_callable=AsyncMock) as mock_mb,
        patch.object(orchestrator, "_search_spotify", new_callable=AsyncMock) as mock_sp,
    ):
        mock_dz.return_value = DEEZER_RESULTS
        mock_mb.return_value = MUSICBRAINZ_RESULTS
        mock_sp.return_value = []  # Spotify not configured

        results = await orchestrator.search_tracks("Nirvana Smells Like Teen Spirit")

    assert len(results) > 0
    # Should have results from both Deezer and MusicBrainz
    sources = {r["source"] for r in results}
    assert "deezer" in sources


@pytest.mark.asyncio
async def test_search_tracks_deduplicates_by_isrc(orchestrator: SearchOrchestrator):
    """Should not return duplicates of the same ISRC from different sources."""
    with (
        patch.object(orchestrator, "_search_deezer", new_callable=AsyncMock) as mock_dz,
        patch.object(orchestrator, "_search_musicbrainz", new_callable=AsyncMock) as mock_mb,
        patch.object(orchestrator, "_search_spotify", new_callable=AsyncMock) as mock_sp,
    ):
        mock_dz.return_value = DEEZER_RESULTS[:1]  # ISRC: USGF19942501
        mock_mb.return_value = MUSICBRAINZ_RESULTS[:1]  # Same ISRC
        mock_sp.return_value = SPOTIFY_RESULTS  # Same ISRC again

        results = await orchestrator.search_tracks("Smells Like Teen Spirit")

    # Same ISRC from 3 sources should be deduplicated to 1
    isrcs = [r.get("isrc") for r in results if r.get("isrc") == "USGF19942501"]
    assert len(isrcs) == 1


@pytest.mark.asyncio
async def test_search_tracks_prefers_deezer_with_image(orchestrator: SearchOrchestrator):
    """When deduplicating, prefer the result that has an image_url."""
    with (
        patch.object(orchestrator, "_search_deezer", new_callable=AsyncMock) as mock_dz,
        patch.object(orchestrator, "_search_musicbrainz", new_callable=AsyncMock) as mock_mb,
        patch.object(orchestrator, "_search_spotify", new_callable=AsyncMock) as mock_sp,
    ):
        mock_dz.return_value = DEEZER_RESULTS[:1]  # Has image_url
        mock_mb.return_value = MUSICBRAINZ_RESULTS[:1]  # No image_url
        mock_sp.return_value = []

        results = await orchestrator.search_tracks("Smells Like Teen Spirit")

    # The deduplicated result should have an image
    smells = [r for r in results if r.get("isrc") == "USGF19942501"]
    assert len(smells) == 1
    assert smells[0]["image_url"] is not None


@pytest.mark.asyncio
async def test_search_tracks_respects_limit(orchestrator: SearchOrchestrator):
    """Should respect the limit parameter."""
    many_results = [{**DEEZER_RESULTS[0], "id": f"dz-{i}", "isrc": f"ISRC{i:05d}"} for i in range(30)]

    with (
        patch.object(orchestrator, "_search_deezer", new_callable=AsyncMock) as mock_dz,
        patch.object(orchestrator, "_search_musicbrainz", new_callable=AsyncMock) as mock_mb,
        patch.object(orchestrator, "_search_spotify", new_callable=AsyncMock) as mock_sp,
    ):
        mock_dz.return_value = many_results
        mock_mb.return_value = []
        mock_sp.return_value = []

        results = await orchestrator.search_tracks("Nirvana", limit=10)

    assert len(results) <= 10


# --- Fallback Tests ---


@pytest.mark.asyncio
async def test_fallback_when_primary_fails(orchestrator: SearchOrchestrator):
    """If Deezer fails, should still return MusicBrainz results."""
    with (
        patch.object(orchestrator, "_search_deezer", new_callable=AsyncMock) as mock_dz,
        patch.object(orchestrator, "_search_musicbrainz", new_callable=AsyncMock) as mock_mb,
        patch.object(orchestrator, "_search_spotify", new_callable=AsyncMock) as mock_sp,
    ):
        mock_dz.side_effect = Exception("Deezer is down")
        mock_mb.return_value = MUSICBRAINZ_RESULTS
        mock_sp.return_value = []

        results = await orchestrator.search_tracks("Nirvana")

    assert len(results) > 0
    assert results[0]["source"] == "musicbrainz"


@pytest.mark.asyncio
async def test_spotify_optional(orchestrator: SearchOrchestrator):
    """Should work perfectly without Spotify configured."""
    with (
        patch.object(orchestrator, "_search_deezer", new_callable=AsyncMock) as mock_dz,
        patch.object(orchestrator, "_search_musicbrainz", new_callable=AsyncMock) as mock_mb,
        patch.object(orchestrator, "_search_spotify", new_callable=AsyncMock) as mock_sp,
    ):
        mock_dz.return_value = DEEZER_RESULTS
        mock_mb.return_value = MUSICBRAINZ_RESULTS
        mock_sp.return_value = []  # Not configured

        results = await orchestrator.search_tracks("Nirvana")

    assert len(results) > 0
    # No spotify results
    spotify_results = [r for r in results if r["source"] == "spotify"]
    assert len(spotify_results) == 0


# --- Search Artists / Albums Tests ---


@pytest.mark.asyncio
async def test_search_artists(orchestrator: SearchOrchestrator):
    """Should search artists across providers."""
    deezer_artists = [
        {
            "id": "27",
            "name": "Nirvana",
            "image_url": "https://deezer.com/img/nirvana.jpg",
            "source": "deezer",
            "type": "artist",
        }
    ]
    mb_artists = [
        {
            "id": "artist-mbid-1",
            "name": "Nirvana",
            "image_url": None,
            "source": "musicbrainz",
            "type": "artist",
        }
    ]

    with (
        patch.object(orchestrator, "_search_deezer_artists", new_callable=AsyncMock) as mock_dz,
        patch.object(orchestrator, "_search_musicbrainz_artists", new_callable=AsyncMock) as mock_mb,
    ):
        mock_dz.return_value = deezer_artists
        mock_mb.return_value = mb_artists

        results = await orchestrator.search_artists("Nirvana")

    assert len(results) >= 1
    assert any(r["name"] == "Nirvana" for r in results)


# --- Get Track Details Tests ---


@pytest.mark.asyncio
async def test_get_track_details_deezer(orchestrator: SearchOrchestrator):
    """Should delegate to Deezer for track details."""
    mock_track = {
        "id": "123",
        "title": "Test Track",
        "artist": "Test Artist",
        "source": "deezer",
    }

    mock_deezer = AsyncMock()
    mock_deezer.get_track.return_value = mock_track
    orchestrator.deezer = mock_deezer

    result = await orchestrator.get_track_details("deezer", "123")

    assert result is not None
    assert result["title"] == "Test Track"


@pytest.mark.asyncio
async def test_get_track_details_unknown_source(orchestrator: SearchOrchestrator):
    """Unknown source should return None."""
    result = await orchestrator.get_track_details("bandcamp", "123")
    assert result is None


# --- ISRC Resolution Tests ---


@pytest.mark.asyncio
async def test_resolve_isrc_from_musicbrainz(orchestrator: SearchOrchestrator):
    """Should resolve ISRC using MusicBrainz search."""
    mock_mb = AsyncMock()
    mock_mb.search_track.return_value = [{"isrc": "USGF19942501", "title": "Test", "artist": "Test"}]
    orchestrator.musicbrainz = mock_mb

    isrc = await orchestrator.resolve_isrc("Nirvana", "Smells Like Teen Spirit")

    assert isrc == "USGF19942501"


@pytest.mark.asyncio
async def test_resolve_isrc_not_found(orchestrator: SearchOrchestrator):
    """When no ISRC found, should return None."""
    mock_mb = AsyncMock()
    mock_mb.search_track.return_value = [
        {"title": "Test", "artist": "Test"}  # no isrc field
    ]
    orchestrator.musicbrainz = mock_mb

    isrc = await orchestrator.resolve_isrc("Unknown", "Unknown Track")

    assert isrc is None
