"""Extended tests covering uncovered branches in HybridRecommendationEngine."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.user import User
from app.schemas.recommendation import RecommendedArtist, RecommendedTrack
from app.services.listening.base import ListeningError, ProviderCredentials
from app.services.recommendation_engine import HybridRecommendationEngine, _is_missing_image

# ─── _is_missing_image ────────────────────────────────────────────────────────


def test_is_missing_image_none():
    assert _is_missing_image(None) is True


def test_is_missing_image_empty_string():
    assert _is_missing_image("") is True


def test_is_missing_image_whitespace():
    assert _is_missing_image("   ") is True


def test_is_missing_image_lastfm_placeholder():
    url = "https://lastfm.freetls.fastly.net/i/u/2a96cbd8b46e442fc41c2b86b821562f.png"
    assert _is_missing_image(url) is True


def test_is_missing_image_alternative_placeholder():
    assert _is_missing_image("https://img/c6f59c1e5e7240a4c0d427abd71f3dbb.png") is True


def test_is_missing_image_real_url():
    assert _is_missing_image("https://cdn.albumart.com/nirvana.jpg") is False


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _fake_provider(name="lastfm"):
    p = AsyncMock()
    p.name = name
    p.get_seeds = AsyncMock(return_value=([("Song", "Artist")], ["Nirvana"]))
    p.get_recommended_artists = AsyncMock(return_value=[])
    return p


@pytest.fixture
def provider():
    return _fake_provider()


@pytest.fixture
def expansion():
    exp = AsyncMock()
    exp.recommend_from_seeds = AsyncMock(return_value=[])
    return exp


@pytest.fixture
def mock_cache():
    cache = AsyncMock()
    cache.get.return_value = None
    return cache


@pytest.fixture
def engine(provider, expansion, mock_cache):
    with patch("app.services.recommendation_engine.cache_manager", mock_cache):
        return HybridRecommendationEngine(
            provider=provider,
            credentials=ProviderCredentials(provider="lastfm", username="lfuser", secret="sk"),
            expansion=expansion,
        )


@pytest.fixture
def user_lf():
    return User(id=uuid4(), username="u")


# ─── _expand_tracks + image backfill ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_expand_missing_images_triggers_deezer(engine, expansion):
    expansion.recommend_from_seeds.return_value = [
        RecommendedTrack(
            name="Track",
            artist="Artist",
            url="https://last.fm/track/1",
            match=0.9,
            image_url="https://img/2a96cbd8b46e442fc41c2b86b821562f.png",
        )
    ]
    mock_deezer = AsyncMock()
    mock_deezer.search.return_value = [{"image_url": "https://cdn.real-cover.com/img.jpg"}]

    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        result = await engine._expand_tracks([("s", "a")], ["a"], variety=False)

    assert result[0].image_url == "https://cdn.real-cover.com/img.jpg"


@pytest.mark.asyncio
async def test_expand_deezer_no_image_leaves_none(engine, expansion):
    expansion.recommend_from_seeds.return_value = [
        RecommendedTrack(name="Track", artist="Artist", url="", match=0.9, image_url=None)
    ]
    mock_deezer = AsyncMock()
    mock_deezer.search.return_value = [{"image_url": None}]

    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        result = await engine._expand_tracks([("s", "a")], [], variety=False)

    assert result[0].image_url is None


@pytest.mark.asyncio
async def test_expand_deezer_exception_is_swallowed(engine, expansion):
    expansion.recommend_from_seeds.return_value = [
        RecommendedTrack(name="T", artist="A", url="", match=0.9, image_url=None)
    ]
    mock_deezer = AsyncMock()
    mock_deezer.search.side_effect = RuntimeError("deezer down")

    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        result = await engine._expand_tracks([("s", "a")], [], variety=False)

    assert result[0].image_url is None


@pytest.mark.asyncio
async def test_expand_no_seeds_returns_empty(engine, expansion):
    result = await engine._expand_tracks([], [], variety=False)
    assert result == []
    expansion.recommend_from_seeds.assert_not_called()


# ─── _gather_seeds ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gather_seeds_swallows_provider_error(engine, provider):
    provider.get_seeds.side_effect = ListeningError("provider down")
    assert await engine._gather_seeds(variety=False) == ([], [])


@pytest.mark.asyncio
async def test_gather_seeds_empty_when_disconnected(mock_cache):
    with patch("app.services.recommendation_engine.cache_manager", mock_cache):
        engine = HybridRecommendationEngine(provider=None, credentials=None)
    assert await engine._gather_seeds(variety=False) == ([], [])


# ─── _fetch_playlists ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_playlists_no_artists_returns_empty(engine):
    assert await engine._fetch_playlists([]) == []


@pytest.mark.asyncio
async def test_fetch_playlists_builds_from_seed_artists(engine):
    mock_deezer = AsyncMock()
    mock_deezer.search_playlists.return_value = [
        {"id": "p1", "title": "This Is Nirvana", "image_url": "img", "track_count": 20},
    ]
    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        result = await engine._fetch_playlists(["Nirvana"])

    assert result[0].title == "This Is Nirvana"


@pytest.mark.asyncio
async def test_fetch_playlists_search_error_returns_empty(engine):
    mock_deezer = AsyncMock()
    mock_deezer.search_playlists.side_effect = RuntimeError("deezer down")
    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        result = await engine._fetch_playlists(["Nirvana"])
    assert result == []


# ─── _fetch_artists ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_artists_disconnected_returns_empty(mock_cache):
    with patch("app.services.recommendation_engine.cache_manager", mock_cache):
        engine = HybridRecommendationEngine(provider=None, credentials=None)
    assert await engine._fetch_artists(variety=False) == []


@pytest.mark.asyncio
async def test_fetch_artists_fills_images_from_deezer(engine, provider):
    provider.get_recommended_artists.return_value = [
        RecommendedArtist(name="Nirvana", url="", match=1.0, image_url="old")
    ]
    mock_deezer = AsyncMock()
    mock_deezer.search.return_value = [{"image_url": "https://cdn.img/nirvana.jpg"}]

    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        result = await engine._fetch_artists(variety=False)

    assert result[0].image_url == "https://cdn.img/nirvana.jpg"


@pytest.mark.asyncio
async def test_fetch_artists_deezer_empty_clears_image(engine, provider):
    provider.get_recommended_artists.return_value = [
        RecommendedArtist(name="Nirvana", url="", match=1.0, image_url="old")
    ]
    mock_deezer = AsyncMock()
    mock_deezer.search.return_value = []

    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        result = await engine._fetch_artists(variety=False)

    assert result[0].image_url is None


@pytest.mark.asyncio
async def test_fetch_artists_provider_error_returns_empty(engine, provider):
    provider.get_recommended_artists.side_effect = ListeningError("down")
    assert await engine._fetch_artists(variety=False) == []


# ─── get_recommendations caching edges ───────────────────────────────────────


@pytest.mark.asyncio
async def test_cache_set_exception_doesnt_raise(engine, expansion, mock_cache, user_lf):
    mock_cache.set.side_effect = RuntimeError("redis down")
    expansion.recommend_from_seeds.return_value = [RecommendedTrack(name="T", artist="A", url="", match=0.9)]

    result = await engine.get_recommendations(user_lf)

    assert len(result.tracks) == 1


@pytest.mark.asyncio
async def test_no_results_are_not_cached(engine, expansion, mock_cache, user_lf):
    expansion.recommend_from_seeds.return_value = []
    engine.provider.get_recommended_artists.return_value = []
    engine.provider.get_seeds.return_value = ([], [])

    await engine.get_recommendations(user_lf)

    mock_cache.set.assert_not_called()
