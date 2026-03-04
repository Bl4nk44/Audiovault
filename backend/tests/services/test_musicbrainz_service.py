"""
Tests for MusicBrainzService — TDD Red Phase.

Covers:
- search_track: basic search, empty results, rate limiting
- search_artist: basic search
- search_album: basic search
- get_track_by_isrc: ISRC lookup
- get_artist: artist by MBID
- get_cover_art: Cover Art Archive
- get_artist_top_releases: releases by artist MBID
- Error handling: network errors, malformed responses
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.musicbrainz_service import MusicBrainzService

# --- Fixtures ---


@pytest.fixture
def service() -> MusicBrainzService:
    return MusicBrainzService()


# --- Mock response data ---

MOCK_RECORDING_SEARCH = {
    "recordings": [
        {
            "id": "rec-mbid-1",
            "title": "Smells Like Teen Spirit",
            "length": 301000,
            "score": 100,
            "artist-credit": [
                {
                    "artist": {
                        "id": "artist-mbid-1",
                        "name": "Nirvana",
                    }
                }
            ],
            "releases": [
                {
                    "id": "release-mbid-1",
                    "title": "Nevermind",
                    "date": "1991-09-24",
                }
            ],
            "isrcs": ["USGF19942501"],
        },
        {
            "id": "rec-mbid-2",
            "title": "Smells Like Teen Spirit (Live)",
            "length": 320000,
            "score": 85,
            "artist-credit": [
                {
                    "artist": {
                        "id": "artist-mbid-1",
                        "name": "Nirvana",
                    }
                }
            ],
            "releases": [],
            "isrcs": [],
        },
    ],
    "count": 2,
    "offset": 0,
}

MOCK_RECORDING_SEARCH_EMPTY = {
    "recordings": [],
    "count": 0,
    "offset": 0,
}

MOCK_ARTIST_SEARCH = {
    "artists": [
        {
            "id": "artist-mbid-1",
            "name": "Nirvana",
            "type": "Group",
            "score": 100,
            "country": "US",
            "life-span": {"begin": "1987", "end": "1994", "ended": True},
        }
    ],
    "count": 1,
    "offset": 0,
}

MOCK_RELEASE_SEARCH = {
    "releases": [
        {
            "id": "release-mbid-1",
            "title": "Nevermind",
            "score": 100,
            "date": "1991-09-24",
            "country": "US",
            "artist-credit": [
                {
                    "artist": {
                        "id": "artist-mbid-1",
                        "name": "Nirvana",
                    }
                }
            ],
            "release-group": {"primary-type": "Album"},
            "track-count": 12,
        }
    ],
    "count": 1,
    "offset": 0,
}

MOCK_ISRC_LOOKUP = {
    "recordings": [
        {
            "id": "rec-mbid-1",
            "title": "Smells Like Teen Spirit",
            "length": 301000,
            "artist-credit": [
                {
                    "artist": {
                        "id": "artist-mbid-1",
                        "name": "Nirvana",
                    }
                }
            ],
            "releases": [
                {
                    "id": "release-mbid-1",
                    "title": "Nevermind",
                    "date": "1991-09-24",
                }
            ],
        }
    ]
}

MOCK_ARTIST_LOOKUP = {
    "id": "artist-mbid-1",
    "name": "Nirvana",
    "type": "Group",
    "country": "US",
    "life-span": {"begin": "1987", "end": "1994", "ended": True},
    "disambiguation": "",
}

MOCK_ARTIST_RELEASES = {
    "release-count": 2,
    "release-offset": 0,
    "releases": [
        {
            "id": "release-mbid-1",
            "title": "Nevermind",
            "date": "1991-09-24",
            "status": "Official",
            "release-group": {"primary-type": "Album"},
        },
        {
            "id": "release-mbid-2",
            "title": "In Utero",
            "date": "1993-09-21",
            "status": "Official",
            "release-group": {"primary-type": "Album"},
        },
    ],
}

MOCK_COVER_ART = {
    "images": [
        {
            "front": True,
            "image": "https://coverartarchive.org/release/release-mbid-1/image.jpg",
            "thumbnails": {
                "small": "https://coverartarchive.org/release/release-mbid-1/small.jpg",
                "large": "https://coverartarchive.org/release/release-mbid-1/large.jpg",
                "250": "https://coverartarchive.org/release/release-mbid-1/250.jpg",
                "500": "https://coverartarchive.org/release/release-mbid-1/500.jpg",
            },
        }
    ]
}


def _mock_response(data: dict, status: int = 200):
    """Create a mock aiohttp response."""
    mock = AsyncMock()
    mock.status = status
    mock.json = AsyncMock(return_value=data)
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)
    return mock


def _mock_session(responses: list):
    """Create a mock aiohttp.ClientSession with sequential responses."""
    session = AsyncMock()
    session.get = MagicMock(side_effect=responses)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


# --- search_track Tests ---


@pytest.mark.asyncio
async def test_search_track_returns_formatted_results(service: MusicBrainzService):
    """Search should return list of tracks formatted like other services."""
    mock_resp = _mock_response(MOCK_RECORDING_SEARCH)
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session):
        results = await service.search_track("Nirvana", "Smells Like Teen Spirit", limit=10)

    assert len(results) == 2
    first = results[0]
    assert first["title"] == "Smells Like Teen Spirit"
    assert first["artist"] == "Nirvana"
    assert first["album"] == "Nevermind"
    assert first["duration_ms"] == 301000
    assert first["source"] == "musicbrainz"
    assert first["isrc"] == "USGF19942501"
    assert first["id"] == "rec-mbid-1"


@pytest.mark.asyncio
async def test_search_track_empty_results(service: MusicBrainzService):
    """Search with no results should return empty list."""
    mock_resp = _mock_response(MOCK_RECORDING_SEARCH_EMPTY)
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session):
        results = await service.search_track("NonExistentArtist", "NonExistentTrack")

    assert results == []


@pytest.mark.asyncio
async def test_search_track_handles_missing_releases(service: MusicBrainzService):
    """Track without releases should have album = 'Unknown Album'."""
    mock_resp = _mock_response(MOCK_RECORDING_SEARCH)
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session):
        results = await service.search_track("Nirvana", "Smells Like Teen Spirit")

    second = results[1]
    assert second["album"] == "Unknown Album"


@pytest.mark.asyncio
async def test_search_track_handles_network_error(service: MusicBrainzService):
    """Network errors should return empty list, not raise exception."""
    mock_resp = _mock_response({}, status=503)
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session):
        results = await service.search_track("Nirvana", "Smells Like Teen Spirit")

    assert results == []


# --- search_artist Tests ---


@pytest.mark.asyncio
async def test_search_artist_returns_formatted_results(service: MusicBrainzService):
    """Artist search should return formatted artist dicts."""
    mock_resp = _mock_response(MOCK_ARTIST_SEARCH)
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session):
        results = await service.search_artist("Nirvana", limit=5)

    assert len(results) == 1
    artist = results[0]
    assert artist["name"] == "Nirvana"
    assert artist["id"] == "artist-mbid-1"
    assert artist["source"] == "musicbrainz"
    assert artist["type"] == "artist"


# --- search_album Tests ---


@pytest.mark.asyncio
async def test_search_album_returns_formatted_results(service: MusicBrainzService):
    """Album search should return formatted album dicts."""
    mock_resp = _mock_response(MOCK_RELEASE_SEARCH)
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session):
        results = await service.search_album("Nevermind", artist="Nirvana", limit=5)

    assert len(results) == 1
    album = results[0]
    assert album["title"] == "Nevermind"
    assert album["artist"] == "Nirvana"
    assert album["source"] == "musicbrainz"
    assert album["id"] == "release-mbid-1"


# --- get_track_by_isrc Tests ---


@pytest.mark.asyncio
async def test_get_track_by_isrc_found(service: MusicBrainzService):
    """ISRC lookup should return track data."""
    mock_resp = _mock_response(MOCK_ISRC_LOOKUP)
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await service.get_track_by_isrc("USGF19942501")

    assert result is not None
    assert result["title"] == "Smells Like Teen Spirit"
    assert result["artist"] == "Nirvana"
    assert result["album"] == "Nevermind"
    assert result["id"] == "rec-mbid-1"


@pytest.mark.asyncio
async def test_get_track_by_isrc_not_found(service: MusicBrainzService):
    """Non-existent ISRC should return None."""
    mock_resp = _mock_response({"recordings": []})
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await service.get_track_by_isrc("INVALID000000")

    assert result is None


# --- get_artist Tests ---


@pytest.mark.asyncio
async def test_get_artist_by_mbid(service: MusicBrainzService):
    """Should return artist details by MusicBrainz ID."""
    mock_resp = _mock_response(MOCK_ARTIST_LOOKUP)
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await service.get_artist("artist-mbid-1")

    assert result is not None
    assert result["name"] == "Nirvana"
    assert result["id"] == "artist-mbid-1"
    assert result["source"] == "musicbrainz"
    assert result["type"] == "artist"


@pytest.mark.asyncio
async def test_get_artist_not_found(service: MusicBrainzService):
    """Non-existent MBID should return None."""
    mock_resp = _mock_response({}, status=404)
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await service.get_artist("nonexistent-mbid")

    assert result is None


# --- get_cover_art Tests ---


@pytest.mark.asyncio
async def test_get_cover_art_found(service: MusicBrainzService):
    """Cover Art Archive should return front cover URL."""
    mock_resp = _mock_response(MOCK_COVER_ART)
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session):
        url = await service.get_cover_art("release-mbid-1")

    assert url is not None
    assert "coverartarchive.org" in url


@pytest.mark.asyncio
async def test_get_cover_art_not_found(service: MusicBrainzService):
    """Missing cover art should return None."""
    mock_resp = _mock_response({}, status=404)
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session):
        url = await service.get_cover_art("release-without-art")

    assert url is None


# --- get_artist_top_releases Tests ---


@pytest.mark.asyncio
async def test_get_artist_top_releases(service: MusicBrainzService):
    """Should return list of releases for an artist."""
    mock_resp = _mock_response(MOCK_ARTIST_RELEASES)
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session):
        releases = await service.get_artist_top_releases("artist-mbid-1")

    assert len(releases) == 2
    assert releases[0]["title"] == "Nevermind"
    assert releases[1]["title"] == "In Utero"
    assert releases[0]["source"] == "musicbrainz"


# --- Rate Limiter Tests ---


@pytest.mark.asyncio
async def test_rate_limiter_enforced(service: MusicBrainzService):
    """Consecutive requests should be delayed by at least ~1 second."""
    call_count = 0

    def make_response(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return _mock_response(MOCK_RECORDING_SEARCH_EMPTY)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(side_effect=make_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        start = asyncio.get_event_loop().time()
        await service.search_track("A", "B")
        await service.search_track("C", "D")
        elapsed = asyncio.get_event_loop().time() - start

    # At least 1 second delay between the two calls
    assert elapsed >= 0.9, f"Rate limiter not enforced: {elapsed}s elapsed"


# --- User-Agent Tests ---


@pytest.mark.asyncio
async def test_user_agent_header_set(service: MusicBrainzService):
    """Requests should include a proper User-Agent header (MusicBrainz requirement)."""
    mock_resp = _mock_response(MOCK_RECORDING_SEARCH_EMPTY)
    mock_session = _mock_session([mock_resp])

    with patch("aiohttp.ClientSession", return_value=mock_session) as mock_cls:
        await service.search_track("Test", "Test")

    # Check that session was created with headers containing User-Agent
    # or that the GET request was made with proper headers
    call_args = mock_session.get.call_args
    headers = call_args.kwargs.get("headers", {}) if call_args.kwargs else {}
    # Or headers set at session level
    session_call = mock_cls.call_args
    session_headers = session_call.kwargs.get("headers", {}) if session_call and session_call.kwargs else {}

    all_headers = {**headers, **session_headers}
    assert "User-Agent" in all_headers or any("Audiovault" in str(v) for v in all_headers.values()), (
        "User-Agent header must be set for MusicBrainz API compliance"
    )
