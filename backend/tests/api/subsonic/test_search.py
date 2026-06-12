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
    user = User(
        username="testuser", email="test@example.com", hashed_password=get_password_hash("testpass"), is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def sample_data(db_session: AsyncSession, test_user: User):
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    await db_session.flush()

    album = Album(title="Test Album", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()

    track = Track(title="Test Song", artist_id=artist.id, album_id=album.id, metadata_content={"genre": "Test Genre"})
    db_session.add(track)
    await db_session.flush()

    # Add Download
    download = Download(track_id=track.id, user_id=test_user.id, status="completed", file_path="/test_audio/test.mp3")
    db_session.add(download)

    await db_session.commit()
    return artist, album, track


@pytest.mark.asyncio
async def test_search2(client: AsyncClient, test_user: User, sample_data):
    artist, album, track = sample_data
    response = await client.get("/rest/search2.view?query=Test&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "searchResult2" in data["subsonic-response"]
    results = data["subsonic-response"]["searchResult2"]
    assert any(a["name"] == "Test Artist" for a in results.get("artist", []))
    assert any(a["title"] == "Test Album" for a in results.get("album", []))
    assert any(s["title"] == "Test Song" for s in results.get("song", []))


@pytest.mark.asyncio
async def test_search3(client: AsyncClient, test_user: User, sample_data):
    artist, album, track = sample_data
    response = await client.get("/rest/search3.view?query=Test&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "searchResult3" in data["subsonic-response"]
    results = data["subsonic-response"]["searchResult3"]
    assert any(a["name"] == "Test Artist" for a in results.get("artist", []))
    assert any(a["name"] == "Test Album" for a in results.get("album", []))
    assert any(s["title"] == "Test Song" for s in results.get("song", []))


# --- Empty-query "match all" behaviour (OpenSubsonic spec) ---
# Symfonium and other clients enumerate the whole library via search3 with an
# empty query, sent literally as query="" (two quote chars, URL-encoded %22%22),
# query= (empty), or by omitting the parameter entirely. All three MUST return
# the full library, not zero results.
# See: https://github.com/opensubsonic/open-subsonic-api/discussions/4


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query_param",
    [
        "query=%22%22",  # query="" — Symfonium's actual full-sync request
        "query=",  # empty string
        "",  # parameter omitted entirely
    ],
    ids=["quoted-empty", "empty-string", "omitted"],
)
async def test_search3_empty_query_returns_all(client: AsyncClient, test_user: User, sample_data, query_param: str):
    artist, album, track = sample_data
    sep = "&" if query_param else ""
    url = f"/rest/search3.view?{query_param}{sep}u=testuser&p=testpass&c=Symfonium&v=1.13.0&f=json"
    response = await client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    results = data["subsonic-response"]["searchResult3"]
    assert any(a["name"] == "Test Artist" for a in results.get("artist", []))
    assert any(a["name"] == "Test Album" for a in results.get("album", []))
    assert any(s["title"] == "Test Song" for s in results.get("song", []))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query_param",
    ["query=%22%22", "query=", ""],
    ids=["quoted-empty", "empty-string", "omitted"],
)
async def test_search2_empty_query_returns_all(client: AsyncClient, test_user: User, sample_data, query_param: str):
    artist, album, track = sample_data
    sep = "&" if query_param else ""
    url = f"/rest/search2.view?{query_param}{sep}u=testuser&p=testpass&c=DSub&v=1.13.0&f=json"
    response = await client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    results = data["subsonic-response"]["searchResult2"]
    assert any(a["name"] == "Test Artist" for a in results.get("artist", []))
    assert any(a["title"] == "Test Album" for a in results.get("album", []))
    assert any(s["title"] == "Test Song" for s in results.get("song", []))


# --- Substreamer regression guard ---
# Substreamer browses folder-style: getIndexes -> getMusicDirectory -> getAlbumList.
# This already works today; the empty-query fix must not change it.


@pytest.mark.asyncio
async def test_substreamer_folder_browse_unchanged(client: AsyncClient, test_user: User, sample_data):
    artist, album, track = sample_data
    auth = "u=testuser&p=testpass&c=Substreamer&v=1.13.0&f=json"

    idx = await client.get(f"/rest/getIndexes.view?{auth}")
    assert idx.status_code == 200
    index = idx.json()["subsonic-response"]["indexes"]
    artists = [a for letter in index.get("index", []) for a in letter.get("artist", [])]
    assert any(a["name"] == "Test Artist" for a in artists)

    root = await client.get(f"/rest/getMusicDirectory.view?id=1&{auth}")
    assert root.status_code == 200
    children = root.json()["subsonic-response"]["directory"]["child"]
    assert any(c["title"] == "Test Artist" for c in children)

    art = await client.get(f"/rest/getMusicDirectory.view?id={artist.id}&{auth}")
    assert art.status_code == 200
    art_children = art.json()["subsonic-response"]["directory"]["child"]
    assert any(c["title"] == "Test Album" for c in art_children)

    alist = await client.get(f"/rest/getAlbumList.view?type=alphabeticalByName&{auth}")
    assert alist.status_code == 200
    assert "subsonic-response" in alist.json()
