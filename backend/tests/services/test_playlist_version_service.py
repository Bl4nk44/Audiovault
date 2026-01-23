"""
Tests for PlaylistVersionService.
"""

import uuid

import pytest
from app.models.playlist import Playlist, PlaylistTrack
from app.models.playlist_version import PlaylistVersion
from app.models.track import Track
from app.services.playlist_version_service import playlist_version_service
from sqlalchemy import select
from sqlalchemy.orm import selectinload


@pytest.fixture
async def sample_playlist(db_session, admin_user):
    """Create a sample playlist for testing."""
    playlist = Playlist(id=uuid.uuid4(), name="Test Playlist", owner_id=admin_user.id, comment="Original description")
    db_session.add(playlist)
    await db_session.commit()
    # Eagerly load tracks relationship
    result = await db_session.execute(
        select(Playlist).where(Playlist.id == playlist.id).options(selectinload(Playlist.tracks))
    )
    return result.scalar_one()


@pytest.mark.asyncio
async def test_create_snapshot_empty_playlist(db_session, sample_playlist, admin_user):
    """Test creating a snapshot of an empty playlist."""
    version = await playlist_version_service.create_snapshot(db_session, sample_playlist, "CREATE", admin_user.id)

    assert version.version_number == 1
    assert version.playlist_id == sample_playlist.id
    assert version.change_type == "CREATE"
    assert version.tracks_snapshot == []
    assert version.name == sample_playlist.name


@pytest.mark.asyncio
async def test_create_snapshot_with_tracks(db_session, sample_playlist, sample_track, admin_user):
    """Test creating a snapshot of a playlist with tracks."""
    # Add track to playlist
    sample_playlist.tracks.append(PlaylistTrack(playlist_id=sample_playlist.id, track_id=sample_track.id, order=1))
    await db_session.commit()

    # Reload with tracks
    result = await db_session.execute(
        select(Playlist).where(Playlist.id == sample_playlist.id).options(selectinload(Playlist.tracks))
    )
    sample_playlist = result.scalar_one()

    version = await playlist_version_service.create_snapshot(db_session, sample_playlist, "ADD_TRACK", admin_user.id)

    assert version.version_number == 1
    assert len(version.tracks_snapshot) == 1
    assert version.tracks_snapshot[0]["track_id"] == str(sample_track.id)
    assert version.tracks_snapshot[0]["order"] == 1


@pytest.mark.asyncio
async def test_get_next_version_number(db_session, sample_playlist):
    """Test version number incrementing."""
    v1 = await playlist_version_service.get_next_version_number(db_session, sample_playlist.id)
    assert v1 == 1

    # Create fake version
    version = PlaylistVersion(
        playlist_id=sample_playlist.id, version_number=1, name="V1", tracks_snapshot=[], change_type="CREATE"
    )
    db_session.add(version)
    await db_session.commit()

    v2 = await playlist_version_service.get_next_version_number(db_session, sample_playlist.id)
    assert v2 == 2


@pytest.mark.asyncio
async def test_get_versions_list(db_session, sample_playlist, admin_user):
    """Test retrieving version history."""
    await playlist_version_service.create_snapshot(db_session, sample_playlist, "CREATE", admin_user.id)
    await playlist_version_service.create_snapshot(db_session, sample_playlist, "UPDATE", admin_user.id)

    versions = await playlist_version_service.get_versions(db_session, sample_playlist.id)
    assert len(versions) == 2
    assert versions[0].version_number == 2
    assert versions[1].version_number == 1


@pytest.mark.asyncio
async def test_get_specific_version(db_session, sample_playlist, admin_user):
    """Test retrieving a single specific version."""
    await playlist_version_service.create_snapshot(db_session, sample_playlist, "CREATE", admin_user.id)

    version = await playlist_version_service.get_version(db_session, sample_playlist.id, 1)
    assert version is not None
    assert version.version_number == 1

    none_version = await playlist_version_service.get_version(db_session, sample_playlist.id, 2)
    assert none_version is None


@pytest.mark.asyncio
async def test_rollback_to_version_empty(db_session, sample_playlist, admin_user):
    """Test rolling back a playlist to an empty state."""
    v1 = await playlist_version_service.create_snapshot(db_session, sample_playlist, "CREATE", admin_user.id)

    sample_playlist.name = "Modified"
    await db_session.commit()
    await db_session.refresh(sample_playlist)

    await playlist_version_service.rollback_to_version(db_session, sample_playlist, v1, admin_user.id)

    await db_session.refresh(sample_playlist)
    assert sample_playlist.name == "Test Playlist"


@pytest.mark.asyncio
async def test_rollback_to_version_with_tracks(db_session, sample_playlist, sample_track, admin_user):
    """Test rolling back a playlist to a state that had tracks."""
    # 1. Version 1: With one track
    sample_playlist.tracks.append(PlaylistTrack(playlist_id=sample_playlist.id, track_id=sample_track.id, order=1))
    await db_session.commit()

    # Reload with tracks
    result = await db_session.execute(
        select(Playlist).where(Playlist.id == sample_playlist.id).options(selectinload(Playlist.tracks))
    )
    sample_playlist = result.scalar_one()

    v1 = await playlist_version_service.create_snapshot(db_session, sample_playlist, "CREATE", admin_user.id)

    # 2. Version 2: Remove the track
    sample_playlist.tracks = []
    await db_session.commit()

    # Reload with tracks
    result = await db_session.execute(
        select(Playlist).where(Playlist.id == sample_playlist.id).options(selectinload(Playlist.tracks))
    )
    sample_playlist = result.scalar_one()

    await playlist_version_service.create_snapshot(db_session, sample_playlist, "REMOVE_TRACK", admin_user.id)

    # 3. Rollback to V1
    await playlist_version_service.rollback_to_version(db_session, sample_playlist, v1, admin_user.id)

    # Verify playlist state
    playlist_id = sample_playlist.id
    expected_track_id = sample_track.id
    db_session.expire_all()

    # Reload playlist object
    result = await db_session.execute(
        select(Playlist).where(Playlist.id == playlist_id).options(selectinload(Playlist.tracks))
    )
    sample_playlist = result.scalar_one()
    assert len(sample_playlist.tracks) == 1
    assert sample_playlist.tracks[0].track_id == expected_track_id


@pytest.mark.asyncio
async def test_rollback_reordering(db_session, sample_playlist, admin_user):
    """Test rolling back a reordering change."""
    # Create 2 tracks
    t1 = Track(id=uuid.uuid4(), title="T1", artist="A1")
    t2 = Track(id=uuid.uuid4(), title="T2", artist="A2")
    db_session.add_all([t1, t2])
    await db_session.commit()

    # Setup V1: T1 (1) -> T2 (2)
    sample_playlist.tracks.append(PlaylistTrack(playlist_id=sample_playlist.id, track_id=t1.id, order=1))
    sample_playlist.tracks.append(PlaylistTrack(playlist_id=sample_playlist.id, track_id=t2.id, order=2))
    await db_session.commit()

    v1 = await playlist_version_service.create_snapshot(db_session, sample_playlist, "INIT", admin_user.id)

    # Change to V2: T2 (1) -> T1 (2)
    # We need to explicitly update the association objects
    # Reload relation to be sure
    await db_session.refresh(sample_playlist)
    result = await db_session.execute(select(PlaylistTrack).where(PlaylistTrack.playlist_id == sample_playlist.id))
    links = result.scalars().all()
    # Map by track_id
    link_map = {link.track_id: link for link in links}

    link_map[t1.id].order = 2
    link_map[t2.id].order = 1
    await db_session.commit()

    await playlist_version_service.create_snapshot(db_session, sample_playlist, "REORDER", admin_user.id)

    # Verify DB state is flipped
    result_v2 = await db_session.execute(
        select(PlaylistTrack).where(PlaylistTrack.playlist_id == sample_playlist.id).order_by(PlaylistTrack.order)
    )
    tracks_v2 = result_v2.scalars().all()
    assert tracks_v2[0].track_id == t2.id
    assert tracks_v2[1].track_id == t1.id

    # Rollback to V1
    await playlist_version_service.rollback_to_version(db_session, sample_playlist, v1, admin_user.id)

    # Verify DB state is original
    result_final = await db_session.execute(
        select(PlaylistTrack).where(PlaylistTrack.playlist_id == sample_playlist.id).order_by(PlaylistTrack.order)
    )
    tracks_final = result_final.scalars().all()
    assert len(tracks_final) == 2
    assert tracks_final[0].track_id == t1.id
    assert tracks_final[1].track_id == t2.id


@pytest.mark.asyncio
async def test_rollback_metadata_only(db_session, sample_playlist, admin_user):
    """Test rolling back name/comment changes."""
    sample_playlist.name = "Original Name"
    sample_playlist.comment = "Original Comment"
    await db_session.commit()

    v1 = await playlist_version_service.create_snapshot(db_session, sample_playlist, "CREATE", admin_user.id)

    # Change metadata
    sample_playlist.name = "New Name"
    sample_playlist.comment = "New Comment"
    await db_session.commit()

    await playlist_version_service.create_snapshot(db_session, sample_playlist, "UPDATE", admin_user.id)

    # Verify changed
    assert sample_playlist.name == "New Name"

    # Rollback
    await playlist_version_service.rollback_to_version(db_session, sample_playlist, v1, admin_user.id)

    # Refresh
    await db_session.refresh(sample_playlist)
    assert sample_playlist.name == "Original Name"
    assert sample_playlist.comment == "Original Comment"
