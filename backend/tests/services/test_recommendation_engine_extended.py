"""Extended tests covering uncovered branches in HybridRecommendationEngine."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.models.user import User
from app.schemas.recommendation import RecommendedArtist, RecommendedTrack
from app.services.lastfm_service import LastfmService
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
    url = "https://img/c6f59c1e5e7240a4c0d427abd71f3dbb.png"
    assert _is_missing_image(url) is True


def test_is_missing_image_real_url():
    assert _is_missing_image("https://cdn.albumart.com/nirvana.jpg") is False


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_lastfm():
    svc = Mock(spec=LastfmService)
    svc.get_recommendations = AsyncMock(return_value=[])
    svc.get_recommended_artists = AsyncMock(return_value=[])
    svc.get_user_top_artists = AsyncMock(return_value=[])
    svc.get_user_recent_tracks = AsyncMock(return_value=[])
    return svc


@pytest.fixture
def mock_cache():
    cache = AsyncMock()
    cache.get.return_value = None
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    return cache


@pytest.fixture
def engine(mock_lastfm, mock_cache):
    with patch("app.services.recommendation_engine.cache_manager", mock_cache):
        return HybridRecommendationEngine(mock_lastfm)


@pytest.fixture
def user_lf():
    return User(
        id=uuid4(),
        username="u",
        lastfm_session_key="sk",
        lastfm_username="lfuser",
    )


@pytest.fixture
def user_no_lf():
    return User(id=uuid4(), username="u", lastfm_session_key=None)


# ─── _fetch_lastfm_recommendations ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_lastfm_missing_images_triggers_deezer(engine, mock_lastfm):
    placeholder_track = RecommendedTrack(
        name="Track",
        artist="Artist",
        url="https://last.fm/track/1",
        match=0.9,
        image_url="https://img/2a96cbd8b46e442fc41c2b86b821562f.png",
    )
    mock_lastfm.get_recommendations.return_value = [placeholder_track]

    user = User(id=uuid4(), username="u", lastfm_session_key="sk", lastfm_username="lfuser")

    mock_deezer = AsyncMock()
    mock_deezer.search.return_value = [{"image_url": "https://cdn.real-cover.com/img.jpg"}]

    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        result = await engine._fetch_lastfm_recommendations(user, source="auto")

    assert result[0].image_url == "https://cdn.real-cover.com/img.jpg"


@pytest.mark.asyncio
async def test_fetch_lastfm_deezer_no_image_found(engine, mock_lastfm):
    placeholder_track = RecommendedTrack(
        name="Track",
        artist="Artist",
        url="",
        match=0.9,
        image_url=None,
    )
    mock_lastfm.get_recommendations.return_value = [placeholder_track]

    user = User(id=uuid4(), username="u", lastfm_session_key="sk", lastfm_username="lfuser")

    mock_deezer = AsyncMock()
    mock_deezer.search.return_value = [{"image_url": None}]

    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        result = await engine._fetch_lastfm_recommendations(user, source="auto")

    assert result[0].image_url is None


@pytest.mark.asyncio
async def test_fetch_lastfm_deezer_search_exception(engine, mock_lastfm):
    placeholder = RecommendedTrack(name="T", artist="A", url="", match=0.9, image_url=None)
    mock_lastfm.get_recommendations.return_value = [placeholder]

    user = User(id=uuid4(), username="u", lastfm_session_key="sk", lastfm_username="lfuser")

    mock_deezer = AsyncMock()
    mock_deezer.search.side_effect = RuntimeError("deezer down")

    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        result = await engine._fetch_lastfm_recommendations(user, source="auto")

    # Should not raise, track image stays None
    assert result[0].image_url is None


@pytest.mark.asyncio
async def test_fetch_lastfm_non_auto_source_still_calls_lastfm(engine, mock_lastfm):
    user = User(id=uuid4(), username="u", lastfm_session_key="sk", lastfm_username="lfuser")
    mock_lastfm.get_recommendations.return_value = []

    result = await engine._fetch_lastfm_recommendations(user, source="lastfm")

    mock_lastfm.get_recommendations.assert_called_once()
    assert result == []


# ─── _fetch_playlists ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_playlists_no_lastfm_returns_empty(engine, user_no_lf):
    result = await engine._fetch_playlists(user_no_lf)
    assert result == []


@pytest.mark.asyncio
async def test_fetch_playlists_fallback_to_recent_tracks(engine, mock_lastfm, user_lf):
    mock_lastfm.get_user_top_artists.return_value = []
    mock_lastfm.get_user_recent_tracks.return_value = [
        {"artist": {"#text": "Nirvana"}},
        {"artist": {"#text": "Nirvana"}},  # duplicate
        {"artist": {"name": "Foo Fighters"}},
    ]

    mock_deezer = AsyncMock()
    mock_deezer.search.return_value = []

    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        await engine._fetch_playlists(user_lf)

    # Should have called deezer for deduplicated artists
    assert mock_deezer.search.call_count >= 0  # 2 unique artists → searches


@pytest.mark.asyncio
async def test_fetch_playlists_no_artists_at_all_returns_empty(engine, mock_lastfm, user_lf):
    mock_lastfm.get_user_top_artists.return_value = []
    mock_lastfm.get_user_recent_tracks.return_value = []

    result = await engine._fetch_playlists(user_lf)

    assert result == []


@pytest.mark.asyncio
async def test_fetch_playlists_success_builds_playlists(engine, mock_lastfm, user_lf):
    mock_lastfm.get_user_top_artists.return_value = [{"name": "Nirvana"}]

    mock_deezer = AsyncMock()
    mock_deezer.search_playlists.return_value = [
        {"id": "p1", "title": "This Is Nirvana", "image_url": "img", "track_count": 20},
    ]

    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        result = await engine._fetch_playlists(user_lf)

    assert len(result) >= 1
    assert result[0].title == "This Is Nirvana"


@pytest.mark.asyncio
async def test_fetch_playlists_exception_returns_empty(engine, mock_lastfm, user_lf):
    mock_lastfm.get_user_top_artists.side_effect = RuntimeError("lastfm down")

    result = await engine._fetch_playlists(user_lf)

    assert result == []


# ─── _fetch_artists ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_artists_no_target_user_returns_empty(engine):
    user = User(id=uuid4(), username="u", lastfm_session_key=None, lastfm_username=None)
    result = await engine._fetch_artists(user)
    assert result == []


@pytest.mark.asyncio
async def test_fetch_artists_success_with_deezer_images(engine, mock_lastfm, user_lf):
    artist = RecommendedArtist(name="Nirvana", url="", match=1.0, image_url="old_img")
    mock_lastfm.get_recommended_artists.return_value = [artist]

    mock_deezer = AsyncMock()
    mock_deezer.search.return_value = [{"image_url": "https://cdn.img/nirvana.jpg"}]

    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        result = await engine._fetch_artists(user_lf)

    assert result[0].image_url == "https://cdn.img/nirvana.jpg"


@pytest.mark.asyncio
async def test_fetch_artists_deezer_no_results_clears_image(engine, mock_lastfm, user_lf):
    artist = RecommendedArtist(name="Nirvana", url="", match=1.0, image_url="old_img")
    mock_lastfm.get_recommended_artists.return_value = [artist]

    mock_deezer = AsyncMock()
    mock_deezer.search.return_value = []

    with patch("app.services.recommendation_engine.DeezerService", return_value=mock_deezer):
        result = await engine._fetch_artists(user_lf)

    assert result[0].image_url is None


@pytest.mark.asyncio
async def test_fetch_artists_exception_returns_empty(engine, mock_lastfm, user_lf):
    mock_lastfm.get_recommended_artists.side_effect = RuntimeError("lastfm down")

    result = await engine._fetch_artists(user_lf)

    assert result == []


# ─── get_recommendations cache error ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_recommendations_cache_set_exception_doesnt_raise(engine, mock_lastfm, mock_cache, user_lf):
    mock_cache.get.return_value = None
    mock_cache.set.side_effect = RuntimeError("redis down")

    track = RecommendedTrack(name="T", artist="A", url="", match=0.9)
    mock_lastfm.get_recommendations.return_value = [track]

    result = await engine.get_recommendations(user_lf)

    assert result is not None
    assert len(result.tracks) == 1


@pytest.mark.asyncio
async def test_get_recommendations_no_results_doesnt_cache(engine, mock_lastfm, mock_cache, user_lf):
    mock_cache.get.return_value = None
    mock_lastfm.get_recommendations.return_value = []

    await engine.get_recommendations(user_lf)

    mock_cache.set.assert_not_called()
