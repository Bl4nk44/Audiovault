import pytest
from httpx import AsyncClient
from app.models.user import User
from app.models.download import Download
from app.models.track import Track
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

# Assuming client and db_session fixtures are from conftest.py



from app.core.dependencies import get_current_active_user
from app.main import app

@pytest.fixture
def override_auth_dependency(db_session):
    # Creates a user and overrides the dependency to return it
    user_id = uuid.uuid4()
    user = User(id=user_id, email="api_test@example.com", username="apitest", hashed_password="pw", is_active=True)
    
    async def get_test_user():
        return user
        
    app.dependency_overrides[get_current_active_user] = get_test_user
    return user

@pytest.mark.asyncio
async def test_get_library(client: AsyncClient, db_session: AsyncSession, override_auth_dependency):
    user = override_auth_dependency
    db_session.add(user)
    
    track = Track(title="Lib Track", artist="Artist", duration_ms=1000)
    db_session.add(track)
    await db_session.flush()
    
    dl = Download(
        id=uuid.uuid4(),
        user_id=user.id,
        track_id=track.id,
        status="completed",
        source="spotify",
        file_path="/tmp/test_lib.mp3"
    )
    dl.track = track # Manual rel assignment for unit test, but here it's full integration?
    # In full integration with DB, relationship loads via foreign keys.
    # But since SQLite in-memory, we must ensure flush/commit happens.
    
    db_session.add(dl)
    await db_session.commit()
    
    response = await client.get("/api/v1/downloads/library")
    print(f"DEBUG: {response.text}")
    assert response.status_code == 200, f"Status code {response.status_code}, response: {response.text}"
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["track"]["title"] == "Lib Track"

@pytest.mark.asyncio
async def test_get_queue(client: AsyncClient, db_session: AsyncSession, override_auth_dependency):
    user = override_auth_dependency
    # User already added by fixture? No, fixture returns object but doesn't persist if we don't ADD it in fixture or test.
    # The fixture above defines the object. I should add it to DB in the test body to be safely scoped.
    # But db connection is shared.
    
    # wait, if I use the SAME override_auth_dependency in multiple tests, I might duplicate insert if I am not careful.
    # But scope is function? No default scope for fixture is function. So new user each time.
    
    # Logic in test_get_library:
    # user = override ...
    # db_session.add(user) -> OK.
    
    track = Track(title="Queue Track", artist="QArtist", duration_ms=200)
    db_session.add(track)
    await db_session.flush()
    
    dl = Download(
        id=uuid.uuid4(),
        user_id=user.id,
        track_id=track.id,
        status="downloading",
        source="youtube"
    )
    db_session.add(dl)
    await db_session.commit()
    
    response = await client.get("/api/v1/downloads/queue")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "downloading"

@pytest.mark.asyncio
async def test_update_library_item(client: AsyncClient, db_session: AsyncSession, override_auth_dependency):
    user = override_auth_dependency
    db_session.add(user)
    
    track = Track(title="Orig Title", artist="Orig Artist", duration_ms=100)
    db_session.add(track)
    await db_session.flush()
    
    dl = Download(
        id=uuid.uuid4(),
        user_id=user.id,
        track_id=track.id,
        status="completed"
    )
    db_session.add(dl)
    await db_session.commit()
    
    updates = {"title": "New Title"}
    response = await client.put(f"/api/v1/downloads/library/{dl.id}", json=updates)
    
    assert response.status_code == 200
    
    # Verify DB
    await db_session.refresh(track)
    assert track.title == "New Title"

@pytest.mark.asyncio
async def test_update_library_item_not_found(client: AsyncClient, override_auth_dependency):
    # Don't add any item
    random_id = uuid.uuid4()
    response = await client.put(f"/api/v1/downloads/library/{random_id}", json={"title": "fail"})
    assert response.status_code == 404
