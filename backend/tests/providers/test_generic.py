from unittest.mock import MagicMock, patch

import pytest

from app.providers.generic import GenericProvider


@pytest.fixture
def generic_provider():
    return GenericProvider()


@pytest.mark.asyncio
async def test_can_handle(generic_provider):
    # Generic handles everything
    assert generic_provider.can_handle("https://any-site.com") is True


@pytest.mark.asyncio
async def test_extract_playlist(generic_provider):
    mock_info = {
        "title": "Generic List",
        "description": "Desc",
        "uploader": "User",
        "entries": [
            {
                "title": "Generic Track",
                "uploader": "Artist",
                "id": "g1",
                "duration": 60,
                "thumbnail": "thumb1",
                "webpage_url": "url1",
            }
        ],
    }

    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = mock_ydl.return_value
        # Since extract_info is called in executor, we mock it
        mock_instance.extract_info.return_value = mock_info

        result = await generic_provider.extract_playlist("https://generic.com/list")

        assert result is not None
        assert result.title == "Generic List"
        assert len(result.tracks) == 1
        assert result.tracks[0].title == "Generic Track"
        assert result.tracks[0].duration_ms == 60000


@pytest.mark.asyncio
async def test_extract_single_track_as_playlist(generic_provider):
    mock_info = {"_type": "video", "title": "Single Video", "uploader": "Uploader", "id": "v1", "duration": 120}

    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = mock_ydl.return_value
        mock_instance.extract_info.return_value = mock_info

        result = await generic_provider.extract_playlist("https://generic.com/video")

        assert result is not None
        assert len(result.tracks) == 1
        assert result.tracks[0].title == "Single Video"


@pytest.mark.asyncio
async def test_get_track(generic_provider):
    mock_info = {"entries": [{"title": "Track 1", "id": "1"}]}

    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = mock_ydl.return_value
        mock_instance.extract_info.return_value = mock_info

        result = await generic_provider.get_track("https://generic.com/track")
        assert result is not None
        assert result.title == "Track 1"


@pytest.mark.asyncio
async def test_extraction_failure(generic_provider):
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = mock_ydl.return_value
        mock_instance.extract_info.side_effect = Exception("Fail")

        result = await generic_provider.extract_playlist("https://fail.com")
        assert result is None


@pytest.mark.asyncio
async def test_extract_playlist_passes_proxy_to_ytdlp(generic_provider):
    captured: dict = {}

    def fake_ytdl(opts):
        captured.update(opts)
        instance = MagicMock()
        instance.extract_info.return_value = {"title": "t", "entries": []}
        return instance

    with (
        patch("app.utils.ydl.settings") as mock_settings,
        patch("app.providers.generic.yt_dlp.YoutubeDL", side_effect=fake_ytdl),
    ):
        mock_settings.DOWNLOAD_PROXY = "http://privoxy:8118"
        await generic_provider.extract_playlist("https://generic.com/list")

    assert captured["proxy"] == "http://privoxy:8118"
