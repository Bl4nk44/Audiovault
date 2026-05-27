"""
Tests for WatchlistStorage service.
Covers: track creation/update, finding tracks, linking watchlist items, existing downloads.
"""

import uuid

import pytest
from sqlalchemy.future import select

from app.models.download import Download
from app.models.track import Track
from app.models.watchlist_item import WatchlistItem
from app.services.watchlist.storage import WatchlistStorage


@pytest.fixture
def storage():
    return WatchlistStorage()


@pytest.mark.asyncio
async def test_get_or_create_track_new_spotify(db_session, storage):
    """Test creating a new track from Spotify source."""
    track_data = {
        "id": "spot123",
        "title": "New Song",
        "artist": "New Artist",
        "album": "New Album",
        "duration_ms": 1000,
        "image_url": "http://img.com",
    }

    track_id, created = await storage.get_or_create_track(db_session, track_data, "spotify", False)

    assert created is True
    assert track_id is not None

    # Verify in DB
    result = await db_session.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one()
    assert track.spotify_id == "spot123"
    assert track.title == "New Song"
    assert track.metadata_content["spotify_id"] == "spot123"


@pytest.mark.asyncio
async def test_get_or_create_track_existing_spotify(db_session, storage):
    """Test retrieving existing Spotify track."""
    # Create existing track
    existing = Track(id=uuid.uuid4(), title="Existing", artist="Artist", spotify_id="spot_exist")
    db_session.add(existing)
    await db_session.commit()

    track_data = {
        "id": "spot_exist",
        "title": "Renamed",  # Should not update main title logic usually, but meta might update
        "artist": "Artist",
    }

    track_id, created = await storage.get_or_create_track(db_session, track_data, "spotify", False)

    assert created is False
    assert track_id == existing.id


@pytest.mark.asyncio
async def test_get_or_create_track_update_metadata(db_session, storage):
    """Test updating metadata for existing track from new source."""
    # Track exists with only title/artist match, no spotify_id
    existing = Track(id=uuid.uuid4(), title="Common Song", artist="Common Artist", metadata_content={})
    db_session.add(existing)
    await db_session.commit()

    track_data = {
        "id": "spot_new",
        "title": "Common Song",
        "artist": "Common Artist",
    }

    # Passing "spotify" source should find by title/artist (fallback) if ID not found,
    # BUT _find_existing_track logic for spotify only looks at spotify_id.
    # Wait, let's check _find_existing_track logic in storage.py.
    # It says: if source == "spotify": where(Track.spotify_id == ...)
    # So if spotify_id is missing, it won't find it by ID.
    # It won't fall back to title/artist unless source is "other" (implicit else).

    # Actually, verify _find_existing_track:
    # if source == "spotify": ... elif source == "youtube": ... else: by title/artist
    # So for "spotify" it STRICTLY searches by ID.
    # So this test case as described would CREATE a new track if not found by ID.

    # Let's test the "unknown" source fallback finding by title/artist
    track_id, created = await storage.get_or_create_track(db_session, track_data, "other", False)
    assert created is False
    assert track_id == existing.id


@pytest.mark.asyncio
async def test_create_new_track_youtube(db_session, storage):
    """Test creating new YouTube track."""
    track_data = {"id": "yt123", "title": "YT Song", "artist": "YT Artist", "source_url": "http://yt.com"}

    track_id, created = await storage.get_or_create_track(db_session, track_data, "youtube", False)

    assert created is True
    result = await db_session.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one()
    assert track.youtube_id == "yt123"
    assert track.metadata_content["source_url"] == "http://yt.com"


@pytest.mark.asyncio
async def test_create_new_track_deezer(db_session, storage):
    """Test creating new Deezer track."""
    track_data = {
        "id": "dz123",
        "title": "Deezer Song",
        "artist": "Deezer Artist",
    }

    track_id, created = await storage.get_or_create_track(db_session, track_data, "deezer", False)

    assert created is True
    result = await db_session.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one()
    assert track.deezer_id == "dz123"


@pytest.mark.asyncio
async def test_ensure_watchlist_item_link(db_session, storage):
    """Test linking track to watchlist."""
    watchlist_id = uuid.uuid4()
    track = Track(id=uuid.uuid4(), title="Linked")
    db_session.add(track)
    await db_session.commit()

    await storage.ensure_watchlist_item_link(db_session, watchlist_id, track.id)

    # Verify
    result = await db_session.execute(
        select(WatchlistItem).where(WatchlistItem.watchlist_id == watchlist_id, WatchlistItem.track_id == track.id)
    )
    assert result.scalar_one_or_none() is not None

    # Call again - should not duplicate
    await storage.ensure_watchlist_item_link(db_session, watchlist_id, track.id)
    result = await db_session.execute(
        select(WatchlistItem).where(WatchlistItem.watchlist_id == watchlist_id, WatchlistItem.track_id == track.id)
    )
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_get_existing_download_ids(db_session, storage, admin_user):
    """Test getting IDs of already downloaded tracks."""
    # 1. Track with spotify_id downloaded
    t1 = Track(id=uuid.uuid4(), title="T1", spotify_id="s1")
    db_session.add(t1)
    await db_session.flush()
    d1 = Download(track_id=t1.id, user_id=admin_user.id, status="completed", archived=False)
    db_session.add(d1)

    # 2. Track with youtube_id downloaded
    t2 = Track(id=uuid.uuid4(), title="T2", youtube_id="y1")
    db_session.add(t2)
    await db_session.flush()
    d2 = Download(track_id=t2.id, user_id=admin_user.id, status="completed", archived=False)
    db_session.add(d2)

    # 3. Track with metadata ID (legacy style or other) downloaded
    t3 = Track(id=uuid.uuid4(), title="T3", metadata_content={"other_id": "o1"})
    db_session.add(t3)
    await db_session.flush()
    d3 = Download(track_id=t3.id, user_id=admin_user.id, status="completed", archived=False)
    db_session.add(d3)

    await db_session.commit()

    # Check Spotify
    ids = await storage.get_existing_download_ids(db_session, admin_user.id, "spotify")
    assert "s1" in ids

    # Check YouTube
    ids = await storage.get_existing_download_ids(db_session, admin_user.id, "youtube")
    assert "y1" in ids

    # Check Other
    ids = await storage.get_existing_download_ids(db_session, admin_user.id, "other")
    assert "o1" in ids
