import uuid

import pytest


@pytest.mark.asyncio
async def test_resolve_creates_new_track_no_source(client, admin_token_headers):
    payload = {"title": "New Track", "artist": "New Artist"}
    response = await client.post("/api/v1/metadata/resolve", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Track"
    assert data["artist"] == "New Artist"
    assert "id" in data


@pytest.mark.asyncio
async def test_resolve_creates_spotify_track(client, admin_token_headers):
    payload = {
        "title": "Spotify Track",
        "artist": "Spotify Artist",
        "source": "spotify",
        "source_id": "sp123",
        "album": "SP Album",
        "image_url": "http://img.test/art.jpg",
        "isrc": "USABC1234567",
    }
    response = await client.post("/api/v1/metadata/resolve", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Spotify Track"
    assert data["album"] == "SP Album"


@pytest.mark.asyncio
async def test_resolve_finds_existing_spotify_track(client, admin_token_headers, db_session):
    from app.models.track import Track

    existing_id = uuid.uuid4()
    track = Track(
        id=existing_id,
        title="Existing Spotify",
        artist="Some Artist",
        spotify_id="sp_existing",
        metadata_content={"album": "Existing Album"},
    )
    db_session.add(track)
    await db_session.commit()
    await db_session.refresh(track)

    payload = {"title": "Existing Spotify", "artist": "Some Artist", "source": "spotify", "source_id": "sp_existing"}
    response = await client.post("/api/v1/metadata/resolve", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(existing_id)
    assert data["title"] == "Existing Spotify"


@pytest.mark.asyncio
async def test_resolve_creates_deezer_track_with_isrc(client, admin_token_headers):
    payload = {
        "title": "Deezer Track",
        "artist": "Deezer Artist",
        "source": "deezer",
        "source_id": "dz456",
        "isrc": "FRAB12345678",
    }
    response = await client.post("/api/v1/metadata/resolve", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Deezer Track"


@pytest.mark.asyncio
async def test_resolve_finds_existing_deezer_track(client, admin_token_headers, db_session):
    from app.models.track import Track

    existing_id = uuid.uuid4()
    track = Track(
        id=existing_id,
        title="Existing Deezer",
        artist="Deezer Artist",
        deezer_id="dz_existing",
        metadata_content={},
    )
    db_session.add(track)
    await db_session.commit()
    await db_session.refresh(track)

    payload = {"title": "Existing Deezer", "artist": "Deezer Artist", "source": "deezer", "source_id": "dz_existing"}
    response = await client.post("/api/v1/metadata/resolve", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(existing_id)


@pytest.mark.asyncio
async def test_resolve_creates_youtube_track(client, admin_token_headers):
    payload = {
        "title": "YouTube Track",
        "artist": "YT Artist",
        "source": "youtube",
        "source_id": "ytABC123",
    }
    response = await client.post("/api/v1/metadata/resolve", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "YouTube Track"


@pytest.mark.asyncio
async def test_resolve_finds_existing_youtube_track(client, admin_token_headers, db_session):
    from app.models.track import Track

    existing_id = uuid.uuid4()
    track = Track(
        id=existing_id,
        title="Existing YouTube",
        artist="YT Artist",
        youtube_id="yt_existing",
        metadata_content={},
    )
    db_session.add(track)
    await db_session.commit()
    await db_session.refresh(track)

    payload = {"title": "Existing YouTube", "artist": "YT Artist", "source": "youtube", "source_id": "yt_existing"}
    response = await client.post("/api/v1/metadata/resolve", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(existing_id)


@pytest.mark.asyncio
async def test_resolve_unknown_source_creates_track(client, admin_token_headers):
    payload = {
        "title": "Unknown Source Track",
        "artist": "Unknown Artist",
        "source": "tidal",
        "source_id": "td999",
    }
    response = await client.post("/api/v1/metadata/resolve", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Unknown Source Track"


@pytest.mark.asyncio
async def test_resolve_requires_auth(client):
    payload = {"title": "Track", "artist": "Artist"}
    response = await client.post("/api/v1/metadata/resolve", json=payload)
    assert response.status_code == 401
