"""
Tests for Subsonic Playlist API endpoints.

Covers:
- getPlaylists.view - list all playlists with songCount
- getPlaylist.view - get playlist with entries
"""

import uuid

import pytest
from app.core.security import get_password_hash
from app.models.download import Download
from app.models.playlist import Playlist, PlaylistTrack
from app.models.track import Track
from app.models.user import User
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a user with real hashed password for Subsonic auth."""
    user = User(
        username="playlistuser",
        email="playlist@test.com",
        hashed_password=get_password_hash("testpass"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def playlist_with_tracks(db_session: AsyncSession, test_user: User):
    """Create a playlist with tracks for testing."""
    # Create tracks with proper duration
    track1 = Track(title="Song One", artist="Artist 1", duration_ms=180000)
    track2 = Track(title="Song Two", artist="Artist 2", duration_ms=240000)
    track3 = Track(title="Song Three", artist="Artist 3", duration_ms=200000)
    db_session.add_all([track1, track2, track3])
    await db_session.flush()

    # Create downloads (required for Subsonic to see tracks)
    dl1 = Download(user_id=test_user.id, track_id=track1.id, status="completed", file_path="/test/song1.mp3")
    dl2 = Download(user_id=test_user.id, track_id=track2.id, status="completed", file_path="/test/song2.mp3")
    dl3 = Download(user_id=test_user.id, track_id=track3.id, status="completed", file_path="/test/song3.mp3")
    db_session.add_all([dl1, dl2, dl3])

    # Create playlist
    playlist = Playlist(name="Test Playlist", owner_id=test_user.id, public=False, comment="Test comment")
    db_session.add(playlist)
    await db_session.flush()

    # Add tracks to playlist
    pt1 = PlaylistTrack(playlist_id=playlist.id, track_id=track1.id, order=0)
    pt2 = PlaylistTrack(playlist_id=playlist.id, track_id=track2.id, order=1)
    pt3 = PlaylistTrack(playlist_id=playlist.id, track_id=track3.id, order=2)
    db_session.add_all([pt1, pt2, pt3])

    await db_session.commit()

    return {
        "user": test_user,
        "playlist": playlist,
        "tracks": [track1, track2, track3],
    }


@pytest.mark.asyncio
async def test_get_playlists_returns_song_count(
    client: AsyncClient, db_session: AsyncSession, playlist_with_tracks
):
    """Test that getPlaylists returns correct songCount."""
    user = playlist_with_tracks["user"]

    response = await client.get(
        f"/rest/getPlaylists.view?u={user.username}&p=testpass&v=1.16.1&c=test&f=json"
    )

    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()

    playlists = data.get("subsonic-response", {}).get("playlists", {}).get("playlist", [])
    assert len(playlists) >= 1

    # Find our test playlist
    test_pl = next((p for p in playlists if p["name"] == "Test Playlist"), None)
    assert test_pl is not None
    assert test_pl["songCount"] == 3, f"Expected 3 songs, got {test_pl['songCount']}"


@pytest.mark.asyncio
async def test_get_playlist_returns_entries(
    client: AsyncClient, db_session: AsyncSession, playlist_with_tracks
):
    """Test that getPlaylist returns entry list with songs."""
    user = playlist_with_tracks["user"]
    playlist = playlist_with_tracks["playlist"]

    response = await client.get(
        f"/rest/getPlaylist.view?id={playlist.id}&u={user.username}&p=testpass&v=1.16.1&c=test&f=json"
    )

    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()

    pl_data = data.get("subsonic-response", {}).get("playlist", {})
    entries = pl_data.get("entry", [])

    assert len(entries) == 3, f"Expected 3 entries, got {len(entries)}"
    assert entries[0]["title"] == "Song One"


@pytest.mark.asyncio
async def test_get_playlist_entries_have_duration(
    client: AsyncClient, db_session: AsyncSession, playlist_with_tracks
):
    """Test that playlist entries have non-zero duration (Sonixd filtering issue)."""
    user = playlist_with_tracks["user"]
    playlist = playlist_with_tracks["playlist"]

    response = await client.get(
        f"/rest/getPlaylist.view?id={playlist.id}&u={user.username}&p=testpass&v=1.16.1&c=test&f=json"
    )

    assert response.status_code == 200
    data = response.json()

    entries = data.get("subsonic-response", {}).get("playlist", {}).get("entry", [])

    for entry in entries:
        assert entry.get("duration", 0) > 0, f"Entry {entry.get('title')} has duration=0!"


@pytest.mark.asyncio
async def test_empty_playlist_returns_zero_songs(
    client: AsyncClient, db_session: AsyncSession, test_user: User
):
    """Test that empty playlist has songCount=0."""
    playlist = Playlist(name="Empty Playlist", owner_id=test_user.id, public=False)
    db_session.add(playlist)
    await db_session.commit()

    response = await client.get(
        f"/rest/getPlaylists.view?u={test_user.username}&p=testpass&v=1.16.1&c=test&f=json"
    )

    assert response.status_code == 200
    data = response.json()

    playlists = data.get("subsonic-response", {}).get("playlists", {}).get("playlist", [])
    empty_pl = next((p for p in playlists if p["name"] == "Empty Playlist"), None)
    assert empty_pl is not None
    assert empty_pl["songCount"] == 0
