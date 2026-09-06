from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.user import User
from app.schemas.recommendation import RecommendationResponse, RecommendedTrack
from app.services.lastfm_service import LastfmError
from app.services.listening.base import ProviderCredentials
from app.services.recommendation_engine import HybridRecommendationEngine


def _fake_provider(name="lastfm"):
    p = AsyncMock()
    p.name = name
    p.get_seeds = AsyncMock(return_value=([("Song", "Artist")], ["Artist"]))
    p.get_recommended_artists = AsyncMock(return_value=[])
    return p


@pytest.fixture
def mock_expansion():
    exp = AsyncMock()
    exp.recommend_from_seeds = AsyncMock(return_value=[])
    return exp


@pytest.fixture
def mock_cache_manager():
    cache = AsyncMock()
    cache.get.return_value = None
    return cache


@pytest.fixture(autouse=True)
def _no_network_deezer():
    """Keep the Deezer image / playlist back-fill offline in engine tests."""
    deezer = AsyncMock()
    deezer.search.return_value = []
    deezer.search_playlists.return_value = []
    with patch("app.services.recommendation_engine.DeezerService", return_value=deezer):
        yield


@pytest.fixture
def provider():
    return _fake_provider()


@pytest.fixture
def engine(provider, mock_expansion, mock_cache_manager):
    with patch("app.services.recommendation_engine.cache_manager", mock_cache_manager):
        return HybridRecommendationEngine(
            provider=provider,
            credentials=ProviderCredentials(provider="lastfm", username="lfuser", secret="sk"),
            expansion=mock_expansion,
        )


@pytest.fixture
def user():
    return User(id=uuid4(), username="testuser")


@pytest.mark.asyncio
async def test_cache_hit_short_circuits(engine, user, mock_cache_manager, mock_expansion):
    cached = RecommendationResponse(
        tracks=[RecommendedTrack(name="Cached", artist="Artist", url="", match=1.0)],
        source="cache",
        cache_status="hit",
        provider="lastfm",
        generated_at=datetime.now(),
    )
    mock_cache_manager.get.return_value = cached.model_dump_json()

    result = await engine.get_recommendations(user)

    assert result.source == "cache"
    assert result.tracks[0].name == "Cached"
    mock_expansion.recommend_from_seeds.assert_not_called()


@pytest.mark.asyncio
async def test_expands_seeds_into_tracks(engine, user, mock_expansion):
    mock_expansion.recommend_from_seeds.return_value = [
        RecommendedTrack(name="Rec", artist="Artist", url="", match=0.9)
    ]

    result = await engine.get_recommendations(user)

    assert result.source == "lastfm+deezer"
    assert result.provider == "lastfm"
    assert result.lastfm_connected is True
    assert len(result.tracks) == 1
    engine.cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_expansion_failure_degrades_to_unknown(engine, user, mock_expansion):
    mock_expansion.recommend_from_seeds.side_effect = LastfmError("boom")

    result = await engine.get_recommendations(user)

    assert result.source == "unknown"
    assert result.tracks == []


@pytest.mark.asyncio
async def test_not_connected_yields_empty(mock_cache_manager):
    with patch("app.services.recommendation_engine.cache_manager", mock_cache_manager):
        engine = HybridRecommendationEngine(provider=None, credentials=None)
    user = User(id=uuid4(), username="u")

    result = await engine.get_recommendations(user)

    assert result.provider == "none"
    assert result.source == "unknown"
    assert result.lastfm_connected is False


@pytest.mark.asyncio
async def test_force_refresh_bypasses_cache(engine, user, mock_cache_manager, mock_expansion):
    mock_cache_manager.get.return_value = "should be ignored"
    mock_expansion.recommend_from_seeds.return_value = []

    await engine.get_recommendations(user, force_refresh=True)

    mock_cache_manager.get.assert_not_called()
    mock_expansion.recommend_from_seeds.assert_called_once()


@pytest.mark.asyncio
async def test_provider_field_reflects_listenbrainz(mock_expansion, mock_cache_manager):
    with patch("app.services.recommendation_engine.cache_manager", mock_cache_manager):
        engine = HybridRecommendationEngine(
            provider=_fake_provider("listenbrainz"),
            credentials=ProviderCredentials(provider="listenbrainz", username="lb", secret="tok"),
            expansion=mock_expansion,
        )
    mock_expansion.recommend_from_seeds.return_value = [RecommendedTrack(name="T", artist="A", url="", match=1.0)]

    result = await engine.get_recommendations(User(id=uuid4(), username="u"))

    assert result.provider == "listenbrainz"
    assert result.lastfm_connected is False


# --- for_user provider selection ---


@pytest.mark.asyncio
async def test_for_user_auto_picks_first_connected():
    prov = _fake_provider("listenbrainz")
    creds = ProviderCredentials(provider="listenbrainz", username="lb", secret="t")
    user = User(id=uuid4(), username="u")
    user.preferences = {}

    with patch(
        "app.services.recommendation_engine.connected_providers",
        new_callable=AsyncMock,
        return_value=[(prov, creds)],
    ):
        engine = await HybridRecommendationEngine.for_user(user, db=None)

    assert engine.provider is prov
    assert engine.credentials is creds


@pytest.mark.asyncio
async def test_for_user_honours_preference():
    lfm = _fake_provider("lastfm")
    lbz = _fake_provider("listenbrainz")
    lfm_creds = ProviderCredentials(provider="lastfm", username="lf", secret="s")
    lbz_creds = ProviderCredentials(provider="listenbrainz", username="lb", secret="t")
    user = User(id=uuid4(), username="u")
    user.preferences = {"listening_provider": "listenbrainz"}

    with (
        patch(
            "app.services.recommendation_engine.connected_providers",
            new_callable=AsyncMock,
            return_value=[(lfm, lfm_creds), (lbz, lbz_creds)],
        ),
        patch(
            "app.services.recommendation_engine.get_provider", side_effect=lambda n: lbz if n == "listenbrainz" else lfm
        ),
    ):
        engine = await HybridRecommendationEngine.for_user(user, db=None)

    assert engine.provider is lbz


@pytest.mark.asyncio
async def test_for_user_nothing_connected_gives_disconnected_engine():
    user = User(id=uuid4(), username="u")
    user.preferences = {}
    with patch(
        "app.services.recommendation_engine.connected_providers",
        new_callable=AsyncMock,
        return_value=[],
    ):
        engine = await HybridRecommendationEngine.for_user(user, db=None)

    assert engine.is_connected is False
