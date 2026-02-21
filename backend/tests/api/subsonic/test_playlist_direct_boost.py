"""
Direct handler calls for playlist coverage boost - Fixed v4.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.subsonic.handlers.playlist import (
    create_playlist,
    delete_playlist,
    get_playlist,
    get_playlists,
    update_playlist,
)
from app.models.download import Download
from app.models.playlist import Playlist, PlaylistTrack
from app.models.track import Track
from app.models.user import User


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def test_user():
    return User(id=1, username="test_user", is_active=True)


@pytest.mark.asyncio
async def test_get_playlists_direct(mock_db, test_user):
    playlist = Playlist(id=uuid.uuid4(), name="My Playlist", owner_id=test_user.id, public=False)

    mock_db.execute.side_effect = [
        MagicMock(scalars=lambda: MagicMock(all=lambda: [playlist])),  # list playlists
        MagicMock(first=lambda: (5, 1500000)),  # song count and duration
        MagicMock(scalar=lambda: test_user.username),  # owner name
    ]

    resp = await get_playlists(username=None, f="json", current_user=test_user, db=mock_db)
    assert resp["subsonic-response"]["playlists"]["playlist"][0]["name"] == "My Playlist"


@pytest.mark.asyncio
async def test_get_playlist_direct(mock_db, test_user):
    playlist_id = uuid.uuid4()
    playlist = Playlist(id=playlist_id, name="Full Playlist", owner_id=test_user.id, public=False)
    track = Track(id=uuid.uuid4(), title="Track in Playlist", duration_ms=100000)
    download = Download(id=1, status="completed")

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: playlist),  # get playlist
        MagicMock(all=lambda: [(None, track, download)]),  # entries
        MagicMock(scalar=lambda: test_user.username),  # owner name
    ]

    resp = await get_playlist(id=str(playlist_id), f="json", current_user=test_user, db=mock_db)
    assert resp["subsonic-response"]["playlist"]["name"] == "Full Playlist"


@pytest.mark.asyncio
async def test_create_playlist_new_direct(mock_db, test_user):
    with patch("app.api.subsonic.handlers.playlist.get_playlist") as mock_get_pl:
        mock_get_pl.return_value = {"subsonic-response": {"status": "ok", "playlist": {"name": "New PL"}}}

        resp = await create_playlist(
            playlist_id_param=None,
            name="New PL",
            song_id=[str(uuid.uuid4())],
            f="json",
            current_user=test_user,
            db=mock_db,
        )
        assert resp["subsonic-response"]["playlist"]["name"] == "New PL"
        assert mock_db.commit.called


@pytest.mark.asyncio
async def test_create_playlist_update_direct(mock_db, test_user):
    playlist_id = uuid.uuid4()
    playlist = Playlist(id=playlist_id, name="Original", owner_id=test_user.id)

    with patch("app.api.subsonic.handlers.playlist.get_playlist") as mock_get_pl:
        mock_get_pl.return_value = {"subsonic-response": {"status": "ok", "playlist": {"name": "Updated"}}}

        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: playlist),  # get existing
            MagicMock(),  # delete tracks execute
        ]

        resp = await create_playlist(
            playlist_id_param=str(playlist_id),
            name="Updated",
            song_id=[str(uuid.uuid4())],
            f="json",
            current_user=test_user,
            db=mock_db,
        )
        assert resp["subsonic-response"]["playlist"]["name"] == "Updated"
        assert playlist.name == "Updated"
        assert mock_db.commit.called


@pytest.mark.asyncio
async def test_update_playlist_full_direct(mock_db, test_user):
    playlist_id = uuid.uuid4()
    playlist = Playlist(id=playlist_id, name="Old Name", owner_id=test_user.id)
    track_to_remove = PlaylistTrack(playlist_id=playlist_id, track_id=uuid.uuid4(), order=0)

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: playlist),  # get playlist
        MagicMock(scalars=lambda: MagicMock(all=lambda: [track_to_remove])),  # tracks to remove
        MagicMock(scalars=lambda: MagicMock(all=lambda: [])),  # reorder remaining
        MagicMock(scalar=lambda: 0),  # max order for add
    ]

    resp = await update_playlist(
        playlist_id_param=str(playlist_id),
        name="New Name",
        song_index_to_remove=[0],
        song_id_to_add=[str(uuid.uuid4())],
        f="json",
        current_user=test_user,
        db=mock_db,
    )
    assert resp["subsonic-response"]["status"] == "ok"
    assert playlist.name == "New Name"
    assert mock_db.delete.called


@pytest.mark.asyncio
async def test_delete_playlist_direct(mock_db, test_user):
    playlist_id = uuid.uuid4()
    playlist = Playlist(id=playlist_id, name="To Delete", owner_id=test_user.id)

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: playlist),  # get playlist
    ]

    resp = await delete_playlist(id=str(playlist_id), f="json", current_user=test_user, db=mock_db)
    assert resp["subsonic-response"]["status"] == "ok"
    mock_db.delete.assert_called_once_with(playlist)
