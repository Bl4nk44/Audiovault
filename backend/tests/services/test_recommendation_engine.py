from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.models.user import User
from app.schemas.recommendation import RecommendationResponse, RecommendedTrack
from app.services.lastfm_service import LastfmError, LastfmService
from app.services.recommendation_engine import HybridRecommendationEngine


@pytest.fixture
def mock_lastfm_service():
    service = Mock(spec=LastfmService)
    service.get_recommendations = AsyncMock()
    service.get_recommended_artists = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_cache_manager():
    # We mock app.core.cache.cache_manager
    # Ideally checking how it's imported in recommendation_engine
    cache = AsyncMock()
    return cache


@pytest.fixture
def engine(mock_lastfm_service, mock_cache_manager):
    # Patch the global cache_manager imported in module
    with patch("app.services.recommendation_engine.cache_manager", mock_cache_manager):
        return HybridRecommendationEngine(mock_lastfm_service)


@pytest.fixture
def user_with_lastfm():
    return User(id=uuid4(), username="testuser", lastfm_session_key="sess_key", lastfm_username="lastfm_user")


@pytest.fixture
def user_without_lastfm():
    return User(id=uuid4(), username="testuser", lastfm_session_key=None)


@pytest.mark.asyncio
async def test_get_recommendations_cache_hit(engine, user_with_lastfm, mock_cache_manager, mock_lastfm_service):
    # Setup cache hit
    cached_resp = RecommendationResponse(
        tracks=[RecommendedTrack(name="Cached", artist="Artist", url="", match=1.0)],
        source="cache",
        cache_status="hit",
        lastfm_connected=True,
        generated_at=datetime.now(),
    )
    mock_cache_manager.get.return_value = cached_resp.model_dump_json()

    result = await engine.get_recommendations(user_with_lastfm)

    assert result.source == "cache"
    assert len(result.tracks) == 1
    assert result.tracks[0].name == "Cached"
    mock_lastfm_service.get_recommendations.assert_not_called()


@pytest.mark.asyncio
async def test_get_recommendations_lastfm_success(engine, user_with_lastfm, mock_cache_manager, mock_lastfm_service):
    # Setup cache miss
    mock_cache_manager.get.return_value = None

    mock_lastfm_service.get_recommendations.return_value = [
        RecommendedTrack(name="Lastfm", artist="Artist", url="", match=0.9)
    ]

    result = await engine.get_recommendations(user_with_lastfm)

    assert result.source == "lastfm+deezer"
    assert len(result.tracks) == 1

    # Verify caching
    mock_cache_manager.set.assert_called_once()


@pytest.mark.asyncio
async def test_get_recommendations_lastfm_failure_fallback(
    engine, user_with_lastfm, mock_cache_manager, mock_lastfm_service
):
    mock_cache_manager.get.return_value = None
    mock_lastfm_service.get_recommendations.side_effect = LastfmError("API Error")

    result = await engine.get_recommendations(user_with_lastfm)

    assert result.source == "unknown"
    # LLM stub returns empty list for now
    assert result.tracks == []


@pytest.mark.asyncio
async def test_user_without_lastfm_uses_llm(engine, user_without_lastfm, mock_lastfm_service):
    result = await engine.get_recommendations(user_without_lastfm)

    assert result.source == "unknown"
    mock_lastfm_service.get_recommendations.assert_not_called()


@pytest.mark.asyncio
async def test_force_refresh_bypasses_cache(engine, user_with_lastfm, mock_cache_manager, mock_lastfm_service):
    mock_cache_manager.get.return_value = "should ignore this"
    mock_lastfm_service.get_recommendations.return_value = []

    await engine.get_recommendations(user_with_lastfm, force_refresh=True)

    mock_cache_manager.get.assert_not_called()
    mock_lastfm_service.get_recommendations.assert_called_once()
