import uuid

import pytest
from httpx import AsyncClient

from app.models.artist import Artist
from app.models.starred import StarredArtist, StarredTrack
from app.models.track import Track


@pytest.fixture
def subsonic_auth_params(admin_user):
    return {"u": admin_user.username, "p": "admin", "c": "pytest", "v": "1.16.1", "f": "json"}


@pytest.mark.asyncio
async def test_subsonic_star_unstar(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    track = Track(id=uuid.uuid4(), title="Star Track")
    db_session.add(track)
    await db_session.commit()

    # Star
    params = {**subsonic_auth_params, "id": [str(track.id)]}
    response = await client.get("/rest/star.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "ok"

    # Verify in DB
    from sqlalchemy import select as sqlalchemy_select

    result = await db_session.execute(sqlalchemy_select(StarredTrack).where(StarredTrack.track_id == track.id))
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_subsonic_get_starred(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    artist = Artist(id=uuid.uuid4(), name="Starred Artist")
    db_session.add(artist)
    await db_session.flush()

    starred = StarredArtist(user_id=admin_user.id, artist_id=artist.id)
    db_session.add(starred)
    await db_session.commit()

    response = await client.get("/rest/getStarred.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    assert any(a["name"] == "Starred Artist" for a in data["subsonic-response"]["starred"]["artist"])


@pytest.mark.asyncio
async def test_subsonic_set_rating(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    track = Track(id=uuid.uuid4(), title="Rating Track")
    db_session.add(track)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(track.id), "rating": 5}
    response = await client.get("/rest/setRating.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_subsonic_scrobble(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    track = Track(id=uuid.uuid4(), title="Scrobble Track")
    db_session.add(track)
    await db_session.commit()

    params = {**subsonic_auth_params, "id": str(track.id), "submission": True}
    response = await client.get("/rest/scrobble.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_subsonic_scrobble_unknown_track_is_noop(
    client: AsyncClient, subsonic_auth_params, db_session, admin_user
):
    # Amperfy scrobbles a track id that no longer exists in the library. On
    # Postgres the unguarded INSERT into listening_history violates the track_id
    # FK and returns 500. Scrobbling an unknown id must be a best-effort no-op
    # that returns ok and writes no history/now-playing rows.
    from sqlalchemy import func
    from sqlalchemy import select as sqlalchemy_select

    from app.models.history import ListeningHistory
    from app.models.subsonic import SubsonicNowPlaying

    unknown_uuid = uuid.uuid4()
    params = {**subsonic_auth_params, "id": str(unknown_uuid), "submission": True}
    response = await client.get("/rest/scrobble.view", params=params)
    assert response.status_code == 200
    assert response.json()["subsonic-response"]["status"] == "ok"

    hist = await db_session.scalar(
        sqlalchemy_select(func.count(ListeningHistory.id)).where(ListeningHistory.track_id == unknown_uuid)
    )
    assert hist == 0
    np = await db_session.scalar(
        sqlalchemy_select(func.count(SubsonicNowPlaying.id)).where(SubsonicNowPlaying.track_id == unknown_uuid)
    )
    assert np == 0


@pytest.mark.asyncio
async def test_subsonic_get_now_playing(client: AsyncClient, subsonic_auth_params, db_session, admin_user):
    # This might require an entry in SubsonicNowPlaying table
    response = await client.get("/rest/getNowPlaying.view", params=subsonic_auth_params)
    assert response.status_code == 200
    assert "nowPlaying" in response.json()["subsonic-response"]
