"""Extended tests for uncovered branches in MusicBrainzService."""

from unittest.mock import AsyncMock, patch

import pytest
from app.services.musicbrainz_service import MusicBrainzService


@pytest.fixture
def service():
    svc = MusicBrainzService()
    # Override rate limit to speed up tests
    svc._rate_limit = AsyncMock()  # type: ignore[method-assign]
    return svc


# ─── _get exception handling ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_request_exception_returns_none(service):
    with patch("aiohttp.ClientSession") as mock_cls:
        mock_session = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_session.get.side_effect = RuntimeError("network error")

        result = await service._get("https://musicbrainz.org/ws/2/recording", {})

    assert result is None


# ─── search_artist no data ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_artist_no_data_returns_empty(service):
    with patch.object(service, "_get", new_callable=AsyncMock, return_value=None):
        result = await service.search_artist("NonExistent")
    assert result == []


# ─── search_album no data ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_album_no_data_returns_empty(service):
    with patch.object(service, "_get", new_callable=AsyncMock, return_value=None):
        result = await service.search_album("NonExistent")
    assert result == []


# ─── get_track_by_isrc no data ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_track_by_isrc_no_data_returns_none(service):
    with patch.object(service, "_get", new_callable=AsyncMock, return_value=None):
        result = await service.get_track_by_isrc("ISRC001")
    assert result is None


@pytest.mark.asyncio
async def test_get_track_by_isrc_empty_recordings_returns_none(service):
    with patch.object(service, "_get", new_callable=AsyncMock, return_value={"recordings": []}):
        result = await service.get_track_by_isrc("ISRC001")
    assert result is None


# ─── get_cover_art fallbacks ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_cover_art_no_data_returns_none(service):
    with patch.object(service, "_get", new_callable=AsyncMock, return_value=None):
        result = await service.get_cover_art("mbid-123")
    assert result is None


@pytest.mark.asyncio
async def test_get_cover_art_no_front_uses_first_image(service):
    data = {"images": [{"front": False, "thumbnails": {"500": "http://500.jpg"}, "image": "http://full.jpg"}]}
    with patch.object(service, "_get", new_callable=AsyncMock, return_value=data):
        result = await service.get_cover_art("mbid-123")
    assert result == "http://500.jpg"


@pytest.mark.asyncio
async def test_get_cover_art_no_images_returns_none(service):
    with patch.object(service, "_get", new_callable=AsyncMock, return_value={"images": []}):
        result = await service.get_cover_art("mbid-123")
    assert result is None


# ─── get_artist_top_releases ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_artist_top_releases_no_data_returns_empty(service):
    with patch.object(service, "_get", new_callable=AsyncMock, return_value=None):
        result = await service.get_artist_top_releases("mbid-123")
    assert result == []


@pytest.mark.asyncio
async def test_get_artist_top_releases_deduplicates_by_title(service):
    data = {
        "releases": [
            {
                "id": "r1",
                "title": "Nevermind",
                "date": "1991",
                "status": "Official",
                "release-group": {"primary-type": "Album"},
            },
            {
                "id": "r2",
                "title": "Nevermind",
                "date": "1992",
                "status": "Official",
                "release-group": {"primary-type": "Album"},
            },
            {
                "id": "r3",
                "title": "In Utero",
                "date": "1993",
                "status": "Official",
                "release-group": {"primary-type": "Album"},
            },
        ]
    }
    with patch.object(service, "_get", new_callable=AsyncMock, return_value=data):
        result = await service.get_artist_top_releases("mbid-123")

    titles = [r["title"] for r in result]
    assert titles.count("Nevermind") == 1
    assert "In Utero" in titles


# ─── _format_recording joinphrase ─────────────────────────────────────────────


def test_format_recording_with_joinphrase(service):
    rec = {
        "id": "rec1",
        "title": "Song",
        "artist-credit": [
            {"artist": {"name": "Artist A"}, "joinphrase": " & "},
            {"artist": {"name": "Artist B"}, "joinphrase": ""},
        ],
        "releases": [],
        "isrcs": ["ISRC001"],
        "length": 180000,
    }
    result = service._format_recording(rec)
    assert "Artist A" in result["artist"]
    assert "&" in result["artist"]
    assert "Artist B" in result["artist"]
