import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.album import Album
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from app.models.user import User


@pytest.fixture
async def test_user(db_session: AsyncSession):
    user = User(username="pquser", email="pq@example.com", hashed_password=get_password_hash("pqpass"), is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_tracks(db_session: AsyncSession, test_user: User):
    artist = Artist(name="PQ Artist")
    db_session.add(artist)
    await db_session.flush()
    album = Album(title="PQ Album", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()

    tracks = []
    for i in range(3):
        track = Track(title=f"PQ Song {i}", artist_id=artist.id, album_id=album.id)
        db_session.add(track)
        await db_session.flush()
        db_session.add(Download(track_id=track.id, user_id=test_user.id, status="completed", file_path=f"/a/{i}.mp3"))
        tracks.append(track)
    await db_session.commit()
    return tracks


def _auth() -> str:
    return "u=pquser&p=pqpass&c=Symfonium&v=1.13.0&f=json"


@pytest.mark.asyncio
async def test_get_play_queue_empty(client: AsyncClient, test_user: User):
    response = await client.get(f"/rest/getPlayQueue.view?{_auth()}")
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_save_then_get_play_queue(client: AsyncClient, test_user: User, sample_tracks):
    ids = [str(t.id) for t in sample_tracks]
    current = ids[1]
    save_url = f"/rest/savePlayQueue.view?{_auth()}&" + "&".join(f"id={i}" for i in ids)
    save_url += f"&current={current}&position=4200"
    save = await client.get(save_url)
    assert save.status_code == 200
    assert save.json()["subsonic-response"]["status"] == "ok"

    get = await client.get(f"/rest/getPlayQueue.view?{_auth()}")
    assert get.status_code == 200
    pq = get.json()["subsonic-response"]["playQueue"]
    assert pq["current"] == current
    assert pq["position"] == 4200
    assert [e["id"] for e in pq["entry"]] == ids


@pytest.mark.asyncio
async def test_save_play_queue_replaces_previous(client: AsyncClient, test_user: User, sample_tracks):
    ids = [str(t.id) for t in sample_tracks]
    first = await client.get(f"/rest/savePlayQueue.view?{_auth()}&id={ids[0]}&id={ids[1]}")
    assert first.status_code == 200
    second = await client.get(f"/rest/savePlayQueue.view?{_auth()}&id={ids[2]}")
    assert second.status_code == 200

    get = await client.get(f"/rest/getPlayQueue.view?{_auth()}")
    pq = get.json()["subsonic-response"]["playQueue"]
    assert [e["id"] for e in pq["entry"]] == [ids[2]]


@pytest.mark.asyncio
async def test_create_get_delete_bookmark(client: AsyncClient, test_user: User, sample_tracks):
    track_id = str(sample_tracks[0].id)

    create = await client.get(f"/rest/createBookmark.view?{_auth()}&id={track_id}&position=9000&comment=resume+here")
    assert create.status_code == 200
    assert create.json()["subsonic-response"]["status"] == "ok"

    listed = await client.get(f"/rest/getBookmarks.view?{_auth()}")
    bookmarks = listed.json()["subsonic-response"]["bookmarks"]["bookmark"]
    assert len(bookmarks) == 1
    assert bookmarks[0]["position"] == 9000
    assert bookmarks[0]["comment"] == "resume here"
    assert bookmarks[0]["entry"]["id"] == track_id

    deleted = await client.get(f"/rest/deleteBookmark.view?{_auth()}&id={track_id}")
    assert deleted.status_code == 200
    after = await client.get(f"/rest/getBookmarks.view?{_auth()}")
    assert after.json()["subsonic-response"]["bookmarks"]["bookmark"] == []


@pytest.mark.asyncio
async def test_create_bookmark_updates_existing(client: AsyncClient, test_user: User, sample_tracks):
    track_id = str(sample_tracks[0].id)
    await client.get(f"/rest/createBookmark.view?{_auth()}&id={track_id}&position=1000")
    await client.get(f"/rest/createBookmark.view?{_auth()}&id={track_id}&position=5000")

    listed = await client.get(f"/rest/getBookmarks.view?{_auth()}")
    bookmarks = listed.json()["subsonic-response"]["bookmarks"]["bookmark"]
    assert len(bookmarks) == 1
    assert bookmarks[0]["position"] == 5000


@pytest.mark.asyncio
async def test_create_bookmark_invalid_id(client: AsyncClient, test_user: User):
    response = await client.get(f"/rest/createBookmark.view?{_auth()}&id=not-a-uuid&position=0")
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "failed"
    assert body["error"]["code"] == 10


@pytest.mark.asyncio
async def test_create_bookmark_unknown_track(client: AsyncClient, test_user: User):
    response = await client.get(f"/rest/createBookmark.view?{_auth()}&id={uuid.uuid4()}&position=0")
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "failed"
    assert body["error"]["code"] == 70
