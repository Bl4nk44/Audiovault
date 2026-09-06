"""
Tests for offset pagination in SearchOrchestrator.search_tracks — TDD Red Phase.

Bug: GET /browse/search "load more" returned the same tracks because offset
was never propagated to the orchestrator/provider. Only Deezer supports
pagination (maps to the `index` param); Spotify partner search and
MusicBrainz do not paginate usefully, so for offset > 0 we query Deezer only
to avoid re-fetching page 1 from other providers and polluting page 2 with
duplicates after dedup.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.search_orchestrator import SearchOrchestrator

DEEZER_PAGE_2 = [
    {
        "id": "dz-789",
        "title": "Lithium",
        "artist": "Nirvana",
        "album": "Nevermind",
        "duration_ms": 257000,
        "image_url": "https://deezer.com/img/789.jpg",
        "source": "deezer",
        "isrc": "USGF19942504",
        "popularity": 700000,
    },
]


@pytest.fixture
def orchestrator() -> SearchOrchestrator:
    return SearchOrchestrator()


@pytest.fixture(autouse=True)
def _stub_network_providers():
    """YouTube / SoundCloud / Apple providers stay inert for the offset=0 path."""
    with (
        patch.object(SearchOrchestrator, "_search_youtube", new_callable=AsyncMock, return_value=[]),
        patch.object(SearchOrchestrator, "_search_soundcloud", new_callable=AsyncMock, return_value=[]),
        patch.object(SearchOrchestrator, "_search_apple", new_callable=AsyncMock, return_value=[]),
    ):
        yield


@pytest.mark.asyncio
async def test_search_tracks_offset_queries_deezer_with_offset(orchestrator: SearchOrchestrator):
    """offset>0 should call deezer.search with offset=20 and return its results."""
    mock_deezer = AsyncMock()
    mock_deezer.search.return_value = DEEZER_PAGE_2
    orchestrator.deezer = mock_deezer

    results = await orchestrator.search_tracks("Nirvana", limit=20, offset=20)

    assert mock_deezer.search.await_args.kwargs.get("offset") == 20
    assert results == DEEZER_PAGE_2


@pytest.mark.asyncio
async def test_search_tracks_offset_does_not_call_other_providers(orchestrator: SearchOrchestrator):
    """offset>0 must not query Spotify or MusicBrainz — they'd just return page 1 again."""
    mock_deezer = AsyncMock()
    mock_deezer.search.return_value = DEEZER_PAGE_2
    orchestrator.deezer = mock_deezer

    with (
        patch.object(orchestrator, "_search_musicbrainz", new_callable=AsyncMock) as mock_mb,
        patch.object(orchestrator, "_search_spotify", new_callable=AsyncMock) as mock_sp,
    ):
        await orchestrator.search_tracks("Nirvana", limit=20, offset=20)

    mock_mb.assert_not_awaited()
    mock_sp.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_tracks_offset_zero_uses_multi_provider_path(orchestrator: SearchOrchestrator):
    """offset=0 (default) must behave as before — multi-provider aggregation, no regression."""
    with (
        patch.object(orchestrator, "_search_deezer", new_callable=AsyncMock) as mock_dz,
        patch.object(orchestrator, "_search_musicbrainz", new_callable=AsyncMock) as mock_mb,
        patch.object(orchestrator, "_search_spotify", new_callable=AsyncMock) as mock_sp,
    ):
        mock_dz.return_value = DEEZER_PAGE_2
        mock_mb.return_value = []
        mock_sp.return_value = []

        results = await orchestrator.search_tracks("Nirvana", limit=20, offset=0)

    mock_dz.assert_awaited()
    mock_mb.assert_awaited()
    mock_sp.assert_awaited()
    assert results == DEEZER_PAGE_2


@pytest.mark.asyncio
async def test_search_tracks_offset_with_non_deezer_source_returns_empty(orchestrator: SearchOrchestrator):
    """source not in (all, deezer) with offset>0 has no pagination available -> empty list."""
    mock_deezer = AsyncMock()
    orchestrator.deezer = mock_deezer

    results = await orchestrator.search_tracks("Nirvana", limit=20, offset=20, source="spotify")

    assert results == []
    mock_deezer.search.assert_not_awaited()
