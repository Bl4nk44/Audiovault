"""Extended tests covering uncovered branches in SearchOrchestrator."""

from unittest.mock import AsyncMock, patch

import pytest
from app.services.search_orchestrator import SearchOrchestrator


@pytest.fixture
def orchestrator():
    return SearchOrchestrator()


TRACK = {
    "id": "t1",
    "title": "Song",
    "artist": "Artist",
    "album": "Album",
    "image_url": "http://img",
    "isrc": "ISRC001",
    "source": "deezer",
}


# ─── search_albums ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_albums(orchestrator):
    with (
        patch.object(orchestrator, "_search_deezer_albums", new_callable=AsyncMock) as mock_dz,
        patch.object(orchestrator, "_search_musicbrainz_albums", new_callable=AsyncMock) as mock_mb,
    ):
        mock_dz.return_value = [{"id": "a1", "title": "Album 1", "source": "deezer"}]
        mock_mb.return_value = [{"id": "mb-a1", "title": "Album 1", "source": "musicbrainz"}]

        results = await orchestrator.search_albums("Album 1", limit=5)

    assert len(results) <= 5
    assert any(r["source"] == "deezer" for r in results)


# ─── get_track_details ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_track_details_spotify(orchestrator):
    orchestrator.spotify = AsyncMock()
    orchestrator.spotify.get_track.return_value = {"id": "sp1", "title": "T", "source": "spotify"}

    result = await orchestrator.get_track_details("spotify", "sp1")

    orchestrator.spotify.get_track.assert_called_once_with("sp1")
    assert result["source"] == "spotify"


@pytest.mark.asyncio
async def test_get_track_details_musicbrainz(orchestrator):
    orchestrator.musicbrainz = AsyncMock()
    orchestrator.musicbrainz.get_track_by_isrc.return_value = {"id": "mb1", "source": "musicbrainz"}

    result = await orchestrator.get_track_details("musicbrainz", "mb1")

    orchestrator.musicbrainz.get_track_by_isrc.assert_called_once_with("mb1")


# ─── get_artist_details ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_artist_details_deezer(orchestrator):
    orchestrator.deezer = AsyncMock()
    orchestrator.deezer.get_artist_details.return_value = {"id": "dz1", "name": "A"}

    result = await orchestrator.get_artist_details("deezer", "dz1")

    assert result["name"] == "A"


@pytest.mark.asyncio
async def test_get_artist_details_spotify(orchestrator):
    orchestrator.spotify = AsyncMock()
    orchestrator.spotify.get_artist_details.return_value = {"id": "sp1", "name": "A"}

    result = await orchestrator.get_artist_details("spotify", "sp1")

    orchestrator.spotify.get_artist_details.assert_called_once_with("sp1")


@pytest.mark.asyncio
async def test_get_artist_details_musicbrainz(orchestrator):
    orchestrator.musicbrainz = AsyncMock()
    orchestrator.musicbrainz.get_artist.return_value = {"id": "mb1"}

    result = await orchestrator.get_artist_details("musicbrainz", "mb1")

    orchestrator.musicbrainz.get_artist.assert_called_once_with("mb1")


@pytest.mark.asyncio
async def test_get_artist_details_auto_deezer_first(orchestrator):
    orchestrator.deezer = AsyncMock()
    orchestrator.deezer.get_artist_details.return_value = {"id": "dz1"}
    orchestrator.musicbrainz = AsyncMock()

    result = await orchestrator.get_artist_details("auto", "dz1")

    orchestrator.deezer.get_artist_details.assert_called_once()
    orchestrator.musicbrainz.get_artist.assert_not_called()


@pytest.mark.asyncio
async def test_get_artist_details_auto_falls_back_to_musicbrainz(orchestrator):
    orchestrator.deezer = AsyncMock()
    orchestrator.deezer.get_artist_details.return_value = None
    orchestrator.musicbrainz = AsyncMock()
    orchestrator.musicbrainz.get_artist.return_value = {"id": "mb1"}

    result = await orchestrator.get_artist_details("auto", "mb1")

    orchestrator.musicbrainz.get_artist.assert_called_once_with("mb1")


@pytest.mark.asyncio
async def test_get_artist_details_unknown_source_returns_none(orchestrator):
    result = await orchestrator.get_artist_details("bandcamp", "123")
    assert result is None


# ─── get_album_details ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_album_details_deezer_with_tracks(orchestrator):
    orchestrator.deezer = AsyncMock()
    orchestrator.deezer.get_album_tracks.return_value = [TRACK]

    result = await orchestrator.get_album_details("deezer", "album1")

    assert result is not None
    assert result["source"] == "deezer"
    assert len(result["tracks"]) == 1


@pytest.mark.asyncio
async def test_get_album_details_deezer_no_tracks_returns_none(orchestrator):
    orchestrator.deezer = AsyncMock()
    orchestrator.deezer.get_album_tracks.return_value = []

    result = await orchestrator.get_album_details("deezer", "album1")

    assert result is None


@pytest.mark.asyncio
async def test_get_album_details_spotify(orchestrator):
    orchestrator.spotify = AsyncMock()
    orchestrator.spotify.get_album_details.return_value = {"id": "sp1", "tracks": []}

    result = await orchestrator.get_album_details("spotify", "sp1")

    orchestrator.spotify.get_album_details.assert_called_once_with("sp1")


@pytest.mark.asyncio
async def test_get_album_details_unknown_source_returns_none(orchestrator):
    result = await orchestrator.get_album_details("tidal", "123")
    assert result is None


# ─── get_playlist_details ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_playlist_details_deezer(orchestrator):
    orchestrator.deezer = AsyncMock()
    orchestrator.deezer.get_playlist_details.return_value = {"id": "pl1", "title": "PL"}

    result = await orchestrator.get_playlist_details("deezer", "pl1")

    assert result["title"] == "PL"


@pytest.mark.asyncio
async def test_get_playlist_details_spotify(orchestrator):
    orchestrator.spotify = AsyncMock()
    orchestrator.spotify.get_playlist_details.return_value = {"id": "pl1"}

    result = await orchestrator.get_playlist_details("spotify", "pl1")

    orchestrator.spotify.get_playlist_details.assert_called_once_with("pl1")


@pytest.mark.asyncio
async def test_get_playlist_details_unknown_returns_none(orchestrator):
    result = await orchestrator.get_playlist_details("tidal", "pl1")
    assert result is None


# ─── _search_spotify ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_spotify_exception_returns_empty(orchestrator):
    orchestrator.spotify = AsyncMock()
    orchestrator.spotify.search.side_effect = Exception("Spotify down")

    result = await orchestrator._search_spotify("query", limit=10)

    assert result == []


@pytest.mark.asyncio
async def test_search_spotify_caps_limit_at_10(orchestrator):
    orchestrator.spotify = AsyncMock()
    orchestrator.spotify.search.return_value = []

    await orchestrator._search_spotify("query", limit=50)

    orchestrator.spotify.search.assert_called_once_with("query", limit=10, type="track")


# ─── _search_deezer_artists ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_deezer_artists_deduplicates(orchestrator):
    orchestrator.deezer = AsyncMock()
    orchestrator.deezer.search.return_value = [
        {"id": "1", "artist": "Nirvana", "image_url": "img1"},
        {"id": "2", "artist": "Nirvana", "image_url": "img2"},
        {"id": "3", "artist": "Foo Fighters", "image_url": "img3"},
    ]

    result = await orchestrator._search_deezer_artists("rock", limit=10)

    names = [r["name"] for r in result]
    assert names.count("Nirvana") == 1
    assert "Foo Fighters" in names


@pytest.mark.asyncio
async def test_search_musicbrainz_artists(orchestrator):
    orchestrator.musicbrainz = AsyncMock()
    orchestrator.musicbrainz.search_artist.return_value = [{"id": "mb1", "name": "Nirvana"}]

    result = await orchestrator._search_musicbrainz_artists("Nirvana", limit=5)

    orchestrator.musicbrainz.search_artist.assert_called_once_with("Nirvana", limit=5)
    assert result[0]["name"] == "Nirvana"


# ─── _search_deezer_albums ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_deezer_albums_deduplicates(orchestrator):
    orchestrator.deezer = AsyncMock()
    orchestrator.deezer.search.return_value = [
        {"id": "1", "album": "Nevermind", "artist": "Nirvana", "image_url": "img"},
        {"id": "2", "album": "Nevermind", "artist": "Nirvana", "image_url": "img"},
        {"id": "3", "album": "In Utero", "artist": "Nirvana", "image_url": "img"},
    ]

    result = await orchestrator._search_deezer_albums("Nirvana", limit=10)

    titles = [r["title"] for r in result]
    assert titles.count("Nevermind") == 1
    assert "In Utero" in titles


@pytest.mark.asyncio
async def test_search_musicbrainz_albums(orchestrator):
    orchestrator.musicbrainz = AsyncMock()
    orchestrator.musicbrainz.search_album.return_value = [{"id": "mb1", "title": "Nevermind"}]

    result = await orchestrator._search_musicbrainz_albums("Nevermind", limit=5)

    orchestrator.musicbrainz.search_album.assert_called_once_with("Nevermind", limit=5)


# ─── _deduplicate_results (image preference) ─────────────────────────────────

def test_deduplicate_results_replaces_with_image_version(orchestrator):
    """When duplicate ISRC found and existing has no image, replace with image version."""
    no_image = {"id": "1", "title": "T", "artist": "A", "isrc": "ISRC001", "image_url": None, "source": "mb"}
    with_image = {"id": "2", "title": "T", "artist": "A", "isrc": "ISRC001", "image_url": "http://img", "source": "dz"}

    result = orchestrator._deduplicate_results([no_image, with_image])

    assert len(result) == 1
    assert result[0]["image_url"] == "http://img"


def test_deduplicate_results_title_dedup_replaces_with_image(orchestrator):
    """Title+artist dedup: replaces no-image entry with image entry."""
    no_img = {"id": "1", "title": "Song", "artist": "Artist", "image_url": None}
    with_img = {"id": "2", "title": "Song", "artist": "Artist", "image_url": "http://img"}

    result = orchestrator._deduplicate_results([no_img, with_img])

    assert len(result) == 1
    assert result[0]["image_url"] == "http://img"


# ─── _deduplicate_by_name ─────────────────────────────────────────────────────

def test_deduplicate_by_name_replaces_no_image(orchestrator):
    no_img = {"name": "Nirvana", "image_url": None, "source": "mb"}
    with_img = {"name": "Nirvana", "image_url": "http://img", "source": "dz"}

    result = orchestrator._deduplicate_by_name([no_img, with_img])

    assert len(result) == 1
    assert result[0]["image_url"] == "http://img"


def test_deduplicate_by_name_uses_title_key_for_albums(orchestrator):
    """Entries with 'title' instead of 'name' are also deduplicated."""
    a = {"title": "Album One", "source": "mb", "image_url": None}
    b = {"title": "Album One", "source": "dz", "image_url": "img"}

    result = orchestrator._deduplicate_by_name([a, b])

    assert len(result) == 1


# ─── _search_musicbrainz single-word query ────────────────────────────────────

@pytest.mark.asyncio
async def test_search_musicbrainz_single_word_query(orchestrator):
    orchestrator.musicbrainz = AsyncMock()
    orchestrator.musicbrainz.search_track.return_value = []

    await orchestrator._search_musicbrainz("Nirvana", limit=5)

    orchestrator.musicbrainz.search_track.assert_called_once_with(artist="", title="Nirvana", limit=5)


@pytest.mark.asyncio
async def test_search_musicbrainz_two_word_query(orchestrator):
    orchestrator.musicbrainz = AsyncMock()
    orchestrator.musicbrainz.search_track.return_value = []

    await orchestrator._search_musicbrainz("Nirvana Smells", limit=5)

    orchestrator.musicbrainz.search_track.assert_called_once_with(artist="Nirvana", title="Smells", limit=5)


# ─── resolve_isrc exception ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_isrc_exception_returns_none(orchestrator):
    orchestrator.musicbrainz = AsyncMock()
    orchestrator.musicbrainz.search_track.side_effect = RuntimeError("boom")

    result = await orchestrator.resolve_isrc("Artist", "Track")

    assert result is None
