import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse, RecommendedPlaylist, RecommendedTrack
from app.services.recommendation_engine import HybridRecommendationEngine


@pytest.fixture
def mock_lastfm():
    return AsyncMock()


@pytest.fixture
def engine(mock_lastfm):
    return HybridRecommendationEngine(mock_lastfm)


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.lastfm_username = "test_lastfm_user"
    user.lastfm_session_key = "test_session_key"
    user.username = "test_user"
    return user


@pytest.fixture(autouse=True)
def mock_cache():
    with patch("app.services.recommendation_engine.cache_manager", new_callable=AsyncMock) as m:
        yield m


@pytest.mark.asyncio
async def test_engine_get_cached(engine, mock_user, mock_cache):
    # Valid RecommendationResponse JSON
    resp = RecommendationResponse(
        tracks=[RecommendedTrack(name="Cached Track", artist="Artist", url="http://url")],
        source="cache",
        lastfm_connected=True,
    )
    mock_cache.get.return_value = resp.model_dump_json()

    recs = await engine.get_recommendations(mock_user)
    assert len(recs.tracks) == 1
    assert recs.tracks[0].name == "Cached Track"
    assert recs.cache_status == "miss"  # RecommendationResponse default is "miss"


@pytest.mark.asyncio
async def test_engine_fetch_lastfm(engine, mock_user, mock_lastfm, mock_cache):
    # Ensure cache miss
    mock_cache.get.return_value = None

    mock_lastfm.get_recommendations.return_value = [
        RecommendedTrack(name="LastFM Track", artist="Artist", url="http://url", score=10.0)
    ]
    mock_lastfm.get_recommended_artists.return_value = []

    with patch.object(engine, "_fetch_playlists", new_callable=AsyncMock) as mock_playlists:
        mock_playlists.return_value = []

        response = await engine.get_recommendations(mock_user, source="auto")
        assert len(response.tracks) == 1
        assert response.tracks[0].name == "LastFM Track"
        assert mock_cache.set.called


@pytest.mark.asyncio
async def test_engine_fetch_playlists_fallback(engine, mock_user, mock_lastfm, mock_cache):
    # No lastfm results, fallback to playlists
    mock_cache.get.return_value = None
    mock_lastfm.get_recommendations.return_value = []
    mock_lastfm.get_recommended_artists.return_value = []

    with patch.object(engine, "_fetch_playlists", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [RecommendedPlaylist(id="p1", title="Playlist Result", url="http://url")]

        response = await engine.get_recommendations(mock_user)
        assert len(response.playlists) == 1
        assert response.playlists[0].title == "Playlist Result"


@pytest.mark.asyncio
async def test_is_missing_image():
    from app.services.recommendation_engine import _is_missing_image

    assert _is_missing_image(None) is True
    assert _is_missing_image("") is True
    assert _is_missing_image("http://last.fm/placeholder/2a96cbd8b46e442fc41c2b86b821562f.png") is True
    assert _is_missing_image("http://real-image.png") is False


@pytest.mark.asyncio
async def test_engine_fetch_lastfm_with_spotify_images(engine, mock_user, mock_lastfm):
    # Test lines 80-93: spotify image search success and error
    mock_lastfm.get_recommendations.return_value = [
        RecommendedTrack(name="No Image", artist="Artist", url="http://url", image_url="")
    ]
    mock_lastfm.get_recommended_artists.return_value = []

    with patch("app.services.recommendation_engine.SpotifyService") as mock_spotify_cls:
        mock_spotify = mock_spotify_cls.return_value
        # First call success, second call error
        mock_spotify.search.side_effect = [
            [{"image_url": "http://spotify-img.png"}],  # test line 89 return
            Exception("Spotify fail"),  # test line 92-93
        ]

        # We need another track to trigger the second call if we want to test exception
        mock_lastfm.get_recommendations.return_value.append(
            RecommendedTrack(name="Fail Track", artist="Artist", url="http://url", image_url="")
        )

        response = await engine.get_recommendations(mock_user, force_refresh=True)
        assert response.tracks[0].image_url == "http://spotify-img.png"
        assert response.tracks[1].image_url == ""  # Failed search


@pytest.mark.asyncio
async def test_engine_fetch_playlists_top_artists_fallback(engine, mock_user, mock_lastfm):
    # Test lines 118-130: Fallback to recent tracks
    mock_lastfm.get_user_top_artists.return_value = []
    mock_lastfm.get_user_recent_tracks.return_value = [{"artist": {"name": "Recent Artist"}}]

    with patch("app.services.recommendation_engine.SpotifyService") as mock_spotify_cls:
        mock_spotify = mock_spotify_cls.return_value
        mock_spotify.search.return_value = [{"id": "p1", "title": "Playlist", "image_url": "img"}]

        # Triggering _fetch_playlists via get_recommendations
        mock_lastfm.get_recommendations.return_value = []
        mock_lastfm.get_recommended_artists.return_value = []

        response = await engine.get_recommendations(mock_user)
        assert len(response.playlists) > 0
        assert response.playlists[0].source == "spotify"


@pytest.mark.asyncio
async def test_engine_playlists_search_error(engine, mock_user, mock_lastfm):
    # Test lines 158 and 183-185: Search error and overall playlists error
    mock_lastfm.get_user_top_artists.return_value = [{"name": "Artist"}]

    with patch("app.services.recommendation_engine.SpotifyService") as mock_spotify_cls:
        mock_spotify = mock_spotify_cls.return_value
        mock_spotify.search.side_effect = Exception("Search error")

        # Test line 158: individual search fail
        playlists = await engine._fetch_playlists(mock_user)
        assert playlists == []

    # Test line 183-185: exception in _fetch_playlists
    with patch.object(engine.lastfm, "get_user_top_artists", side_effect=Exception("Lastfm fail")):
        playlists = await engine._fetch_playlists(mock_user)
        assert playlists == []


@pytest.mark.asyncio
async def test_engine_force_artist_images(engine, mock_user, mock_lastfm):
    # Test lines 218-246: Forcing artist images from Spotify
    mock_lastfm.get_recommendations.return_value = []
    from app.schemas.recommendation import RecommendedArtist

    mock_lastfm.get_recommended_artists.return_value = [
        RecommendedArtist(name="Artist1", url="http://url", image_url="lastfm-img")
    ]

    with patch("app.services.recommendation_engine.SpotifyService") as mock_spotify_cls:
        mock_spotify = mock_spotify_cls.return_value
        mock_spotify.search.return_value = [{"image_url": "http://spotify-img.png"}]

        response = await engine.get_recommendations(mock_user)
        assert response.artists[0].image_url == "http://spotify-img.png"


@pytest.mark.asyncio
async def test_engine_cache_error(engine, mock_user, mock_lastfm, mock_cache):
    # Test line 271: Caching error
    mock_lastfm.get_recommendations.return_value = [RecommendedTrack(name="T1", artist="A", url="http://url")]
    mock_lastfm.get_recommended_artists.return_value = []
    mock_cache.set.side_effect = Exception("Redis fail")

    # Should not raise exception, just log it
    response = await engine.get_recommendations(mock_user)
    assert len(response.tracks) == 1
