import pytest
from app.services.amazon_music_service import amazon_music_service
from app.services.apple_music_service import apple_music_service
from app.services.tidal_service import tidal_service


@pytest.mark.asyncio
async def test_tidal_can_handle():
    assert tidal_service.can_handle("https://tidal.com/browse/track/12345") is True
    assert tidal_service.can_handle("https://google.com") is False


@pytest.mark.asyncio
async def test_amazon_can_handle():
    assert amazon_music_service.can_handle("https://music.amazon.com/albums/B00000") is True
    assert amazon_music_service.can_handle("https://amazon.com/music/player") is True
    assert amazon_music_service.can_handle("https://spotify.com") is False


@pytest.mark.asyncio
async def test_apple_can_handle():
    assert apple_music_service.can_handle("https://music.apple.com/us/album/123") is True
    assert apple_music_service.can_handle("https://apple.co/123") is True
    assert apple_music_service.can_handle("https://youtube.com") is False


@pytest.mark.asyncio
async def test_inheritance_works():
    # Check if get_tracks exists (inherited from BaseMusicService)
    assert hasattr(tidal_service, "get_tracks")
    assert hasattr(amazon_music_service, "get_tracks")
    assert hasattr(apple_music_service, "get_tracks")
