import asyncio
import os
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from app.db.base import Base
from app.db.database import get_db
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

from sqlalchemy.pool import StaticPool

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session():
    """Create a fresh database session for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def mock_cache_manager():
    """Mock Redis cache manager to avoid connecting to real Redis."""
    from unittest.mock import AsyncMock

    from app.core.cache import cache_manager as real_cache_manager

    # Patch the methods on the instance itself so all references see the mock
    with (
        patch.object(real_cache_manager, "connect", new_callable=AsyncMock),
        patch.object(real_cache_manager, "close", new_callable=AsyncMock),
        patch.object(real_cache_manager, "get", new_callable=AsyncMock) as mock_get,
        patch.object(real_cache_manager, "set", new_callable=AsyncMock),
    ):
        # Also mock the redis attribute if accessed directly
        real_cache_manager.redis = AsyncMock()
        # FastAPILimiter expects simple int (current count) in some versions?
        # If 1000 caused 429, then it interpreted it as usage count.
        real_cache_manager.redis.evalsha.return_value = 1
        mock_get.return_value = None

        # Mock FastAPILimiter to use our mocked redis
        from fastapi_limiter import FastAPILimiter

        if not FastAPILimiter.redis:
            await FastAPILimiter.init(real_cache_manager.redis)

        yield real_cache_manager

        # Cleanup
        real_cache_manager.redis = None


@pytest.fixture(scope="function")
async def mock_scheduler():
    """Mock scheduler service to prevent background tasks during tests."""
    with (
        patch("app.services.scheduler.scheduler_service.start"),
        patch("app.services.scheduler.scheduler_service.stop"),
        patch("app.services.scheduler.scheduler_service.scheduler.shutdown"),
    ):
        yield


@pytest.fixture(scope="function")
async def mock_download_manager():
    """Mock download manager worker to prevent background tasks."""
    from unittest.mock import AsyncMock

    with (
        patch("app.services.download_manager.download_manager.start_worker"),
        patch("app.services.download_manager.download_manager.resume_pending_downloads"),
        patch("app.services.download_manager.download_manager.add_download", new_callable=AsyncMock) as m_add,
        patch("app.services.download_manager.download_manager.pause_download", new_callable=AsyncMock),
        patch("app.services.download_manager.download_manager.resume_download", new_callable=AsyncMock),
        patch("app.services.download_manager.download_manager.restart_all_downloads", new_callable=AsyncMock),
        patch("app.services.download_manager.download_manager.cancel_download", new_callable=AsyncMock),
    ):
        m_add.return_value = {"status": "queued"}
        yield


@pytest.fixture(scope="function")
async def mock_library_maintenance():
    """Mock library maintenance service."""
    from unittest.mock import AsyncMock

    with (
        patch(
            "app.services.library_maintenance.library_maintenance_service.rescan_library_integrity",
            new_callable=AsyncMock,
        ) as m_rescan,
        patch("app.services.library_maintenance.library_maintenance_service.clear_history", new_callable=AsyncMock),
        patch("app.services.library_maintenance.library_maintenance_service.fix_legacy_data", new_callable=AsyncMock),
        patch(
            "app.services.library_maintenance.library_maintenance_service.update_download_item", new_callable=AsyncMock
        ),
    ):
        m_rescan.return_value = 0
        yield


@pytest.fixture(scope="function")
async def client(
    db_session: AsyncSession, mock_cache_manager, mock_scheduler, mock_download_manager, mock_library_maintenance
) -> AsyncGenerator[AsyncClient, None]:
    """Create a new FastAPI TestClient that uses the `db_session` fixture and mocked cache."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async def bypass_limiter():
        return

    for route in app.routes:
        if hasattr(route, "dependencies") and route.dependencies:
            for d in route.dependencies:
                if type(d.dependency).__name__ == "RateLimiter":
                    app.dependency_overrides[d.dependency] = bypass_limiter

    # Mock download_dir to use a temp dir
    import tempfile

    temp_dir = os.path.join(tempfile.gettempdir(), "audiovault_test_downloads")
    with patch("app.core.config.settings.DOWNLOAD_DIR", temp_dir):
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def admin_user(db_session):
    import uuid

    from app.core.security import get_password_hash
    from app.models.user import User

    password = "admin"
    hashed_password = get_password_hash(password)

    user = User(
        id=uuid.uuid4(), username="admin", email="admin@example.com", hashed_password=hashed_password, is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def admin_token_headers(admin_user):
    from app.core.security import create_access_token

    token = create_access_token(subject=admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session", autouse=True)
async def cleanup_engine():
    yield
    await engine.dispose()


@pytest.fixture(scope="function")
async def sample_track(db_session):
    """Create a sample track for testing."""
    import uuid

    from app.models.track import Track

    track = Track(
        id=uuid.uuid4(),
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        spotify_id="test_spotify_id",
        artist_id=uuid.uuid4(),
        album_id=uuid.uuid4(),
        metadata_content={"genre": "Test"},
    )
    db_session.add(track)
    await db_session.commit()
    await db_session.refresh(track)
    return track
