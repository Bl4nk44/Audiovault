from unittest.mock import AsyncMock, patch

import pytest
from app.providers.amazon_music_provider import AmazonMusicProvider
from app.providers.tidal_provider import TidalProvider


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def amazon():
    return AmazonMusicProvider()


@pytest.fixture
def tidal():
    return TidalProvider()


TRACK_DICT = {
    "id": "t1",
    "title": "Test Track",
    "artist": "Test Artist",
    "album": "Test Album",
    "duration_ms": 180_000,
    "image_url": "http://img.url",
    "source_url": "https://music.amazon.com/track/t1",
}


# ─── AmazonMusicProvider ─────────────────────────────────────────────────────

def test_amazon_name(amazon):
    assert amazon.name == "amazon_music"


def test_amazon_domains(amazon):
    assert "music.amazon.com" in amazon.domains
    assert "amazon.com" in amazon.domains
    assert "music.amazon.co.uk" in amazon.domains


def test_amazon_can_handle(amazon):
    with patch("app.providers.amazon_music_provider.amazon_music_service") as mock_svc:
        mock_svc.can_handle.side_effect = lambda url: "music.amazon." in url
        assert amazon.can_handle("https://music.amazon.com/albums/B001") is True
        assert amazon.can_handle("https://spotify.com") is False


@pytest.mark.asyncio
async def test_amazon_extract_playlist_no_tracks_returns_none(amazon):
    with patch("app.providers.amazon_music_provider.amazon_music_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[])
        result = await amazon.extract_playlist("https://music.amazon.com/playlists/pl1")
    assert result is None


@pytest.mark.asyncio
async def test_amazon_extract_playlist_with_tracks(amazon):
    with patch("app.providers.amazon_music_provider.amazon_music_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[TRACK_DICT])
        result = await amazon.extract_playlist("https://music.amazon.com/playlists/pl1")

    assert result is not None
    assert len(result.tracks) == 1
    assert result.tracks[0].title == "Test Track"
    assert result.tracks[0].source == "amazon_music"
    assert result.tracks[0].source_id == "t1"
    assert result.description == "Imported from Amazon Music"


@pytest.mark.asyncio
async def test_amazon_extract_playlist_url_is_playlist(amazon):
    track = {**TRACK_DICT, "album": "Playlist Name"}
    with patch("app.providers.amazon_music_provider.amazon_music_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[track])
        result = await amazon.extract_playlist("https://music.amazon.com/playlists/pl1")

    assert result.title == "Playlist Name"


@pytest.mark.asyncio
async def test_amazon_extract_playlist_url_is_album(amazon):
    track = {**TRACK_DICT, "album": "Album Name"}
    with patch("app.providers.amazon_music_provider.amazon_music_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[track])
        result = await amazon.extract_playlist("https://music.amazon.com/albums/B001")

    assert result.title == "Album Name"


@pytest.mark.asyncio
async def test_amazon_extract_playlist_fallback_title(amazon):
    track = {**TRACK_DICT, "album": None}
    with patch("app.providers.amazon_music_provider.amazon_music_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[track])
        result = await amazon.extract_playlist("https://music.amazon.com/playlists/pl1")

    assert result.title == "Amazon Music Playlist"


@pytest.mark.asyncio
async def test_amazon_get_track_found(amazon):
    with patch("app.providers.amazon_music_provider.amazon_music_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[TRACK_DICT])
        result = await amazon.get_track("https://music.amazon.com/track/t1")

    assert result is not None
    assert result.title == "Test Track"
    assert result.artist == "Test Artist"
    assert result.source == "amazon_music"
    assert result.source_id == "t1"


@pytest.mark.asyncio
async def test_amazon_get_track_not_found(amazon):
    with patch("app.providers.amazon_music_provider.amazon_music_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[])
        result = await amazon.get_track("https://music.amazon.com/track/missing")

    assert result is None


# ─── TidalProvider ───────────────────────────────────────────────────────────

def test_tidal_name(tidal):
    assert tidal.name == "tidal"


def test_tidal_domains(tidal):
    assert "tidal.com" in tidal.domains
    assert "listen.tidal.com" in tidal.domains


def test_tidal_can_handle(tidal):
    with patch("app.providers.tidal_provider.tidal_service") as mock_svc:
        mock_svc.can_handle.side_effect = lambda url: "tidal.com" in url
        assert tidal.can_handle("https://tidal.com/browse/track/123") is True
        assert tidal.can_handle("https://spotify.com") is False


@pytest.mark.asyncio
async def test_tidal_extract_playlist_no_tracks_returns_none(tidal):
    with patch("app.providers.tidal_provider.tidal_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[])
        result = await tidal.extract_playlist("https://tidal.com/browse/playlist/pl1")
    assert result is None


@pytest.mark.asyncio
async def test_tidal_extract_playlist_with_tracks(tidal):
    tidal_track = {**TRACK_DICT, "source_url": "https://tidal.com/browse/track/t1"}
    with patch("app.providers.tidal_provider.tidal_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[tidal_track])
        result = await tidal.extract_playlist("https://tidal.com/browse/playlist/pl1")

    assert result is not None
    assert len(result.tracks) == 1
    assert result.tracks[0].source == "tidal"
    assert result.description == "Imported from Tidal"


@pytest.mark.asyncio
async def test_tidal_extract_playlist_url_is_playlist(tidal):
    track = {**TRACK_DICT, "album": "Tidal PL Name"}
    with patch("app.providers.tidal_provider.tidal_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[track])
        result = await tidal.extract_playlist("https://tidal.com/browse/playlist/pl1")

    assert result.title == "Tidal PL Name"


@pytest.mark.asyncio
async def test_tidal_extract_playlist_fallback_title(tidal):
    track = {**TRACK_DICT, "album": None}
    with patch("app.providers.tidal_provider.tidal_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[track])
        result = await tidal.extract_playlist("https://tidal.com/browse/playlist/pl1")

    assert result.title == "Tidal Playlist"


@pytest.mark.asyncio
async def test_tidal_extract_album_fallback_title(tidal):
    track = {**TRACK_DICT, "album": None}
    with patch("app.providers.tidal_provider.tidal_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[track])
        result = await tidal.extract_playlist("https://tidal.com/browse/album/123")

    assert result.title == "Tidal Album"


@pytest.mark.asyncio
async def test_tidal_get_track_found(tidal):
    tidal_track = {**TRACK_DICT, "source_url": "https://tidal.com/browse/track/t1"}
    with patch("app.providers.tidal_provider.tidal_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[tidal_track])
        result = await tidal.get_track("https://tidal.com/browse/track/t1")

    assert result is not None
    assert result.title == "Test Track"
    assert result.source == "tidal"


@pytest.mark.asyncio
async def test_tidal_get_track_not_found(tidal):
    with patch("app.providers.tidal_provider.tidal_service") as mock_svc:
        mock_svc.get_tracks = AsyncMock(return_value=[])
        result = await tidal.get_track("https://tidal.com/browse/track/missing")

    assert result is None
