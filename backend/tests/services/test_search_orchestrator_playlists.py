"""Tests for playlist search in SearchOrchestrator."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.search_orchestrator import SearchOrchestrator


@pytest.fixture
def orchestrator() -> SearchOrchestrator:
    return SearchOrchestrator()


@pytest.mark.asyncio
async def test_search_playlists_delegates_to_deezer(orchestrator: SearchOrchestrator) -> None:
    fake = [{"id": "123", "title": "Rock Hits", "type": "playlist", "source": "deezer"}]
    with patch.object(orchestrator.deezer, "search_playlists", new=AsyncMock(return_value=fake)) as mock_dz:
        results = await orchestrator.search_playlists("rock", limit=10)
    mock_dz.assert_awaited_once_with("rock", limit=10)
    assert results == fake


@pytest.mark.asyncio
async def test_search_playlists_survives_provider_error(orchestrator: SearchOrchestrator) -> None:
    with patch.object(orchestrator.deezer, "search_playlists", new=AsyncMock(side_effect=RuntimeError)):
        results = await orchestrator.search_playlists("rock")
    assert results == []


@pytest.mark.asyncio
async def test_search_playlists_unsupported_source_returns_empty(orchestrator: SearchOrchestrator) -> None:
    with patch.object(orchestrator.deezer, "search_playlists", new=AsyncMock(return_value=[{"id": "1"}])) as mock_dz:
        results = await orchestrator.search_playlists("rock", source="spotify")
    mock_dz.assert_not_awaited()
    assert results == []
