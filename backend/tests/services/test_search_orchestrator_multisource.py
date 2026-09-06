"""Multi-source track search — YouTube, SoundCloud and Apple Music are part of
the ``source="all"`` aggregation, not just Deezer/MusicBrainz/Spotify."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.search_orchestrator import SearchOrchestrator


@pytest.fixture
def orchestrator() -> SearchOrchestrator:
    return SearchOrchestrator()


YT = [{"id": "yt1", "title": "Blinding Lights", "artist": "The Weeknd", "source": "youtube", "isrc": None}]
SC = [{"id": "sc1", "title": "Some Bootleg", "artist": "DJ Nobody", "source": "soundcloud"}]
AP = [{"id": "ap1", "title": "Blinding Lights", "artist": "The Weeknd", "source": "apple_music", "isrc": None}]
DZ = [{"id": "dz1", "title": "Save Your Tears", "artist": "The Weeknd", "source": "deezer", "isrc": "USUG12001657"}]


@pytest.mark.asyncio
async def test_all_source_aggregates_youtube_soundcloud_apple(orchestrator: SearchOrchestrator):
    with (
        patch.object(orchestrator, "_search_deezer", new_callable=AsyncMock, return_value=DZ),
        patch.object(orchestrator, "_search_musicbrainz", new_callable=AsyncMock, return_value=[]),
        patch.object(orchestrator, "_search_spotify", new_callable=AsyncMock, return_value=[]),
        patch.object(orchestrator, "_search_youtube", new_callable=AsyncMock, return_value=YT) as m_yt,
        patch.object(orchestrator, "_search_soundcloud", new_callable=AsyncMock, return_value=SC) as m_sc,
        patch.object(orchestrator, "_search_apple", new_callable=AsyncMock, return_value=AP) as m_ap,
    ):
        results = await orchestrator.search_tracks("the weeknd", source="all", limit=20)

    m_yt.assert_awaited_once()
    m_sc.assert_awaited_once()
    m_ap.assert_awaited_once()
    sources = {r["source"] for r in results}
    assert {"deezer", "youtube", "soundcloud"}.issubset(sources)


@pytest.mark.asyncio
async def test_all_source_interleaves_so_full_deezer_page_does_not_bury_others(orchestrator: SearchOrchestrator):
    """Deezer returns a full page of 20; the limited response must still surface
    YouTube / SoundCloud results, not 20 Deezer rows."""
    dz_full = [
        {"id": f"dz{i}", "title": f"Deezer Song {i}", "artist": "A", "source": "deezer", "isrc": f"X{i:04d}"}
        for i in range(20)
    ]
    yt3 = [
        {"id": f"yt{i}", "title": f"YT Song {i}", "artist": "B", "source": "youtube", "isrc": None} for i in range(3)
    ]
    sc2 = [{"id": f"sc{i}", "title": f"SC Song {i}", "artist": "C", "source": "soundcloud"} for i in range(2)]

    with (
        patch.object(orchestrator, "_search_deezer", new_callable=AsyncMock, return_value=dz_full),
        patch.object(orchestrator, "_search_musicbrainz", new_callable=AsyncMock, return_value=[]),
        patch.object(orchestrator, "_search_spotify", new_callable=AsyncMock, return_value=[]),
        patch.object(orchestrator, "_search_youtube", new_callable=AsyncMock, return_value=yt3),
        patch.object(orchestrator, "_search_soundcloud", new_callable=AsyncMock, return_value=sc2),
        patch.object(orchestrator, "_search_apple", new_callable=AsyncMock, return_value=[]),
    ):
        results = await orchestrator.search_tracks("q", source="all", limit=20)

    assert len(results) == 20
    sources = [r["source"] for r in results]
    assert sources.count("youtube") == 3
    assert sources.count("soundcloud") == 2
    # first rows alternate rather than being 20x deezer
    assert sources[:3] == ["deezer", "youtube", "soundcloud"]


def test_interleave_by_source_round_robins_and_keeps_order(orchestrator: SearchOrchestrator):
    rows = [
        {"source": "deezer", "id": "d1"},
        {"source": "deezer", "id": "d2"},
        {"source": "deezer", "id": "d3"},
        {"source": "youtube", "id": "y1"},
        {"source": "youtube", "id": "y2"},
    ]
    out = orchestrator._interleave_by_source(rows)
    assert [r["id"] for r in out] == ["d1", "y1", "d2", "y2", "d3"]


@pytest.mark.asyncio
async def test_all_source_dedupes_across_new_providers_by_title_artist(orchestrator: SearchOrchestrator):
    """YouTube + Apple both return 'Blinding Lights' with no ISRC → collapsed to one."""
    with (
        patch.object(orchestrator, "_search_deezer", new_callable=AsyncMock, return_value=[]),
        patch.object(orchestrator, "_search_musicbrainz", new_callable=AsyncMock, return_value=[]),
        patch.object(orchestrator, "_search_spotify", new_callable=AsyncMock, return_value=[]),
        patch.object(orchestrator, "_search_youtube", new_callable=AsyncMock, return_value=YT),
        patch.object(orchestrator, "_search_soundcloud", new_callable=AsyncMock, return_value=[]),
        patch.object(orchestrator, "_search_apple", new_callable=AsyncMock, return_value=AP),
    ):
        results = await orchestrator.search_tracks("blinding lights", source="all")

    blinding = [r for r in results if r["title"].lower() == "blinding lights"]
    assert len(blinding) == 1


@pytest.mark.asyncio
async def test_source_youtube_only_hits_youtube_provider(orchestrator: SearchOrchestrator):
    with (
        patch.object(orchestrator, "_search_deezer", new_callable=AsyncMock) as m_dz,
        patch.object(orchestrator, "_search_youtube", new_callable=AsyncMock, return_value=YT) as m_yt,
        patch.object(orchestrator, "_search_soundcloud", new_callable=AsyncMock) as m_sc,
    ):
        results = await orchestrator.search_tracks("the weeknd", source="youtube")

    m_yt.assert_awaited_once()
    m_dz.assert_not_awaited()
    m_sc.assert_not_awaited()
    assert all(r["source"] == "youtube" for r in results)


@pytest.mark.asyncio
async def test_safe_call_returns_empty_on_timeout(orchestrator: SearchOrchestrator):
    async def never_returns():
        import asyncio

        await asyncio.sleep(60)
        return ["nope"]  # pragma: no cover

    results = await orchestrator._safe_call(never_returns(), timeout=0.05)

    assert results == []


@pytest.mark.asyncio
async def test_one_slow_provider_does_not_starve_the_aggregation(orchestrator: SearchOrchestrator):
    """A hanging provider is bounded by _safe_call's timeout; the rest still return."""

    async def slow_soundcloud(*_a, **_kw):
        import asyncio

        await asyncio.sleep(60)
        return []  # pragma: no cover

    real_safe_call = orchestrator._safe_call

    async def fast_timeout_safe_call(coro, timeout=0.05):
        return await real_safe_call(coro, timeout=0.05)

    with (
        patch.object(orchestrator, "_search_deezer", new_callable=AsyncMock, return_value=DZ),
        patch.object(orchestrator, "_search_musicbrainz", new_callable=AsyncMock, return_value=[]),
        patch.object(orchestrator, "_search_spotify", new_callable=AsyncMock, return_value=[]),
        patch.object(orchestrator, "_search_youtube", new_callable=AsyncMock, return_value=YT),
        patch.object(orchestrator, "_search_soundcloud", side_effect=slow_soundcloud),
        patch.object(orchestrator, "_search_apple", new_callable=AsyncMock, return_value=[]),
        patch.object(orchestrator, "_safe_call", side_effect=fast_timeout_safe_call),
    ):
        results = await orchestrator.search_tracks("the weeknd", source="all")

    sources = {r["source"] for r in results}
    assert "deezer" in sources and "youtube" in sources


@pytest.mark.asyncio
async def test_search_youtube_offloads_sync_call_to_thread(orchestrator: SearchOrchestrator):
    fake_yt = type("FakeYT", (), {"search": staticmethod(lambda q, limit, typ: YT)})()
    orchestrator._youtube = fake_yt

    results = await orchestrator._search_youtube("the weeknd", limit=5)

    assert results == YT


@pytest.mark.asyncio
async def test_search_soundcloud_delegates_to_service(orchestrator: SearchOrchestrator):
    orchestrator.soundcloud = AsyncMock()
    orchestrator.soundcloud.search.return_value = SC

    results = await orchestrator._search_soundcloud("bootleg", limit=7)

    orchestrator.soundcloud.search.assert_awaited_once_with("bootleg", limit=7)
    assert results == SC


@pytest.mark.asyncio
async def test_search_apple_delegates_to_service(orchestrator: SearchOrchestrator):
    orchestrator.apple = AsyncMock()
    orchestrator.apple.search.return_value = AP

    results = await orchestrator._search_apple("weeknd", limit=9)

    orchestrator.apple.search.assert_awaited_once_with("weeknd", limit=9)
    assert results == AP
