from unittest.mock import AsyncMock, patch

import pytest

from app.providers.soundcloud_provider import SoundCloudProvider


@pytest.fixture
def soundcloud_provider():
    return SoundCloudProvider()


@pytest.mark.asyncio
async def test_can_handle(soundcloud_provider):
    with patch("app.providers.soundcloud_provider.soundcloud_service") as mock_service:
        mock_service.can_handle.side_effect = lambda url: "soundcloud.com" in url
        assert soundcloud_provider.can_handle("https://soundcloud.com/user/track") is True
        assert soundcloud_provider.can_handle("https://spotify.com") is False


@pytest.mark.asyncio
async def test_extract_playlist(soundcloud_provider):
    with patch("app.providers.soundcloud_provider.soundcloud_service") as mock_service:
        mock_service.get_tracks = AsyncMock(
            return_value=[
                {
                    "id": "s1",
                    "title": "SC Track 1",
                    "artist": "SC Artist 1",
                    "album": "SC Album",
                    "duration_ms": 1000,
                    "image_url": "img1",
                    "source_url": "url1",
                }
            ]
        )

        result = await soundcloud_provider.extract_playlist("https://soundcloud.com/user/sets/my-set")

        assert result is not None
        assert result.title == "SoundCloud Set"  # based on 'sets' in URL
        assert len(result.tracks) == 1
        assert result.tracks[0].title == "SC Track 1"
        assert result.tracks[0].source == "soundcloud"


@pytest.mark.asyncio
async def test_get_track(soundcloud_provider):
    with patch("app.providers.soundcloud_provider.soundcloud_service") as mock_service:
        mock_service.get_tracks = AsyncMock(
            return_value=[
                {
                    "id": "s1",
                    "title": "SC Track 1",
                    "artist": "SC Artist 1",
                    "album": "SC Album",
                    "duration_ms": 1000,
                    "image_url": "img1",
                    "source_url": "url1",
                }
            ]
        )

        result = await soundcloud_provider.get_track("https://soundcloud.com/user/track-1")

        assert result is not None
        assert result.title == "SC Track 1"
        assert result.source_id == "s1"
        assert result.source == "soundcloud"
