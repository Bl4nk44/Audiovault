import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.security import get_password_hash
from app.models.playlist import Playlist, PlaylistTrack
from app.models.playlist_version import PlaylistVersion
from app.models.track import Track
from app.models.user import User
from sqlalchemy.exc import IntegrityError


@pytest.fixture
async def sample_playlist(db_session, admin_user):
    playlist = Playlist(name="Test Playlist", owner_id=admin_user.id, public=False)
    db_session.add(playlist)
    await db_session.commit()
    await db_session.refresh(playlist)
    return playlist


@pytest.fixture
async def sample_track(db_session):
    track = Track(id=uuid.uuid4(), title="Test Song", artist="Artist", duration_ms=1000)
    db_session.add(track)
    await db_session.commit()
    return track


@pytest.fixture
async def other_user(db_session):
    u = User(
        id=uuid.uuid4(), username="other", email="other@ex.com", hashed_password=get_password_hash("pw"), is_active=True
    )
    db_session.add(u)
    await db_session.commit()
    return u


@pytest.mark.asyncio
async def test_create_playlist_coverage(client, admin_token_headers):
    data = {"name": "New", "comment": "C", "public": True}
    response = await client.post("/api/v1/playlists/", json=data, headers=admin_token_headers)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_playlist_not_found_scenarios(client, admin_token_headers):
    pid = uuid.uuid4()
    assert (await client.get(f"/api/v1/playlists/{pid}", headers=admin_token_headers)).status_code == 404
    assert (
        await client.put(f"/api/v1/playlists/{pid}", json={"name": "X"}, headers=admin_token_headers)
    ).status_code == 404
    assert (await client.delete(f"/api/v1/playlists/{pid}", headers=admin_token_headers)).status_code == 404
    assert (
        await client.post(
            f"/api/v1/playlists/{pid}/tracks", json={"track_ids": [str(uuid.uuid4())]}, headers=admin_token_headers
        )
    ).status_code == 404
    assert (
        await client.request(
            "DELETE",
            f"/api/v1/playlists/{pid}/tracks",
            json={"track_ids": [str(uuid.uuid4())]},
            headers=admin_token_headers,
        )
    ).status_code == 404
    assert (await client.get(f"/api/v1/playlists/{pid}/export", headers=admin_token_headers)).status_code == 404
    assert (await client.get(f"/api/v1/playlists/{pid}/versions", headers=admin_token_headers)).status_code == 404
    assert (await client.post(f"/api/v1/playlists/{pid}/rollback/1", headers=admin_token_headers)).status_code == 404


@pytest.mark.asyncio
async def test_add_tracks_invalid_ids(client, admin_token_headers, sample_playlist):
    data = {"track_ids": [str(uuid.uuid4())]}
    response = await client.post(
        f"/api/v1/playlists/{sample_playlist.id}/tracks", json=data, headers=admin_token_headers
    )
    assert response.status_code == 400
    assert "No valid track IDs" in response.json()["detail"]


@pytest.mark.asyncio
async def test_add_tracks_integrity_error(client, admin_token_headers, sample_playlist, sample_track):
    data = {"track_ids": [str(sample_track.id)]}
    with patch("app.api.v1.playlists.AsyncSession.commit", side_effect=IntegrityError(None, None, Exception())):
        response = await client.post(
            f"/api/v1/playlists/{sample_playlist.id}/tracks", json=data, headers=admin_token_headers
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_versions_forbidden(client, other_user, sample_playlist):
    from datetime import timedelta

    from app.core.security import create_access_token

    token = create_access_token(subject=other_user.id, expires_delta=timedelta(minutes=15))
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(f"/api/v1/playlists/{sample_playlist.id}/versions", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_rollback_forbidden(client, other_user, sample_playlist):
    from datetime import timedelta

    from app.core.security import create_access_token

    token = create_access_token(subject=other_user.id, expires_delta=timedelta(minutes=15))
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(f"/api/v1/playlists/{sample_playlist.id}/rollback/1", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_rollback_version_not_found(client, admin_token_headers, sample_playlist):
    response = await client.post(f"/api/v1/playlists/{sample_playlist.id}/rollback/999", headers=admin_token_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_playlists_with_tracks(client, admin_token_headers, sample_playlist, sample_track, db_session):
    pt = PlaylistTrack(playlist_id=sample_playlist.id, track_id=sample_track.id, order=1)
    db_session.add(pt)
    await db_session.commit()
    response = await client.get("/api/v1/playlists/", headers=admin_token_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_playlist_details_with_tracks(client, admin_token_headers, sample_playlist, sample_track, db_session):
    pt = PlaylistTrack(playlist_id=sample_playlist.id, track_id=sample_track.id, order=1)
    db_session.add(pt)
    await db_session.commit()
    response = await client.get(f"/api/v1/playlists/{sample_playlist.id}", headers=admin_token_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_playlist_full(client, admin_token_headers, sample_playlist):
    data = {"name": "Updated", "comment": "C", "public": True}
    response = await client.put(f"/api/v1/playlists/{sample_playlist.id}", json=data, headers=admin_token_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_playlist_coverage(client, admin_token_headers, sample_playlist):
    response = await client.delete(f"/api/v1/playlists/{sample_playlist.id}", headers=admin_token_headers)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_remove_tracks_coverage(client, admin_token_headers, sample_playlist, sample_track):
    data = {"track_ids": [str(sample_track.id)]}
    response = await client.request(
        "DELETE", f"/api/v1/playlists/{sample_playlist.id}/tracks", json=data, headers=admin_token_headers
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_export_playlist_full(client, admin_token_headers, sample_playlist, sample_track, db_session):
    sample_track.metadata_content = {"year": 2024, "genre": "Rock"}
    db_session.add(sample_track)
    pt = PlaylistTrack(playlist_id=sample_playlist.id, track_id=sample_track.id, order=1)
    db_session.add(pt)
    await db_session.commit()
    response = await client.get(f"/api/v1/playlists/{sample_playlist.id}/export", headers=admin_token_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_versions_success(client, admin_token_headers, sample_playlist, db_session):
    v = PlaylistVersion(
        playlist_id=sample_playlist.id,
        version_number=1,
        name="V",
        change_type="c",
        tracks_snapshot=[],
        created_at=__import__("datetime").datetime.now(),
    )
    db_session.add(v)
    await db_session.commit()
    response = await client.get(f"/api/v1/playlists/{sample_playlist.id}/versions", headers=admin_token_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_rollback_success(client, admin_token_headers, sample_playlist, sample_track, db_session):
    v = PlaylistVersion(
        playlist_id=sample_playlist.id,
        version_number=1,
        name="V1",
        change_type="create",
        tracks_snapshot=[str(sample_track.id)],
        created_at=__import__("datetime").datetime.now(),
    )
    db_session.add(v)
    await db_session.commit()
    with patch(
        "app.api.v1.playlists.playlist_version_service.rollback_to_version", new_callable=AsyncMock
    ) as mock_rollback:
        mock_rollback.return_value = MagicMock(version_number=2)
        response = await client.post(f"/api/v1/playlists/{sample_playlist.id}/rollback/1", headers=admin_token_headers)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_add_tracks_success_coverage(client, admin_token_headers, sample_playlist, sample_track):
    data = {"track_ids": [str(sample_track.id)]}
    response = await client.post(
        f"/api/v1/playlists/{sample_playlist.id}/tracks", json=data, headers=admin_token_headers
    )
    assert response.status_code == 201
    assert response.json()["added_count"] == 1
