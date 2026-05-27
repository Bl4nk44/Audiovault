import uuid

import pytest
from httpx import AsyncClient


@pytest.fixture
def subsonic_auth_params(admin_user):
    return {
        "u": admin_user.username,
        "p": "admin",
        "c": "pytest",
        "v": "1.16.1",
        "f": "json",
    }


@pytest.mark.asyncio
async def test_get_lyrics_no_id_returns_empty(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "artist": "Test Artist", "title": "Test Title"}
    response = await client.get("/rest/getLyrics.view", params=params)
    assert response.status_code == 200
    data = response.json()
    resp = data["subsonic-response"]
    assert resp["status"] == "ok"
    assert "lyrics" in resp
    assert resp["lyrics"]["artist"] == "Test Artist"
    assert resp["lyrics"]["title"] == "Test Title"
    assert "not available" in resp["lyrics"]["content"]


@pytest.mark.asyncio
async def test_get_lyrics_valid_track_no_lyrics(client: AsyncClient, subsonic_auth_params, db_session):
    from app.models.track import Track

    track = Track(
        id=uuid.uuid4(),
        title="No Lyrics Track",
        artist="Some Artist",
        metadata_content={},
    )
    db_session.add(track)
    await db_session.commit()
    await db_session.refresh(track)

    params = {**subsonic_auth_params, "id": str(track.id)}
    response = await client.get("/rest/getLyrics.view", params=params)
    assert response.status_code == 200
    data = response.json()
    resp = data["subsonic-response"]
    assert resp["status"] == "ok"
    assert "lyrics" in resp
    assert "not available" in resp["lyrics"]["content"]
    assert resp["lyrics"]["artist"] == "Some Artist"


@pytest.mark.asyncio
async def test_get_lyrics_track_with_lyrics(client: AsyncClient, subsonic_auth_params, db_session):
    from app.models.track import Track

    track = Track(
        id=uuid.uuid4(),
        title="Lyrics Track",
        artist="Lyric Artist",
        metadata_content={"lyrics": "Line 1\nLine 2\nLine 3"},
    )
    db_session.add(track)
    await db_session.commit()
    await db_session.refresh(track)

    params = {**subsonic_auth_params, "id": str(track.id)}
    response = await client.get("/rest/getLyrics.view", params=params)
    assert response.status_code == 200
    data = response.json()
    resp = data["subsonic-response"]
    assert resp["status"] == "ok"
    assert resp["lyrics"]["content"] == "Line 1\nLine 2\nLine 3"
    assert resp["lyrics"]["artist"] == "Lyric Artist"
    assert resp["lyrics"]["title"] == "Lyrics Track"


@pytest.mark.asyncio
async def test_get_lyrics_invalid_uuid(client: AsyncClient, subsonic_auth_params):
    params = {**subsonic_auth_params, "id": "not-a-valid-uuid"}
    response = await client.get("/rest/getLyrics.view", params=params)
    assert response.status_code == 200
    data = response.json()
    resp = data["subsonic-response"]
    assert resp["status"] == "ok"
    assert "lyrics" in resp


@pytest.mark.asyncio
async def test_get_lyrics_no_params(client: AsyncClient, subsonic_auth_params):
    response = await client.get("/rest/getLyrics.view", params=subsonic_auth_params)
    assert response.status_code == 200
    data = response.json()
    resp = data["subsonic-response"]
    assert resp["status"] == "ok"
    assert "lyrics" in resp
