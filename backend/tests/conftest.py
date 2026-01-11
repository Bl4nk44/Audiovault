import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.main import app
from app.db.database import get_db
from unittest.mock import MagicMock, patch
import os

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
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
    from app.core.cache import cache_manager as real_cache_manager
    from unittest.mock import AsyncMock

    # Patch the methods on the instance itself so all references see the mock
    with patch.object(real_cache_manager, "connect", new_callable=AsyncMock) as mock_connect, \
         patch.object(real_cache_manager, "close", new_callable=AsyncMock) as mock_close, \
         patch.object(real_cache_manager, "get", new_callable=AsyncMock) as mock_get, \
         patch.object(real_cache_manager, "set", new_callable=AsyncMock) as mock_set:
        
        # Also mock the redis attribute if accessed directly
        real_cache_manager.redis = MagicMock()
        mock_get.return_value = None
        
        yield real_cache_manager
        
        # Cleanup
        real_cache_manager.redis = None


@pytest.fixture(scope="function")
async def mock_scheduler():
    """Mock scheduler service to prevent background tasks during tests."""
    with patch("app.services.scheduler.scheduler_service.start"), \
         patch("app.services.scheduler.scheduler_service.stop"), \
         patch("app.services.scheduler.scheduler_service.scheduler.shutdown"):
        yield

@pytest.fixture(scope="function")
async def mock_download_manager():
    """Mock download manager worker to prevent background tasks."""
    with patch("app.services.download_manager.download_manager.start_worker"), \
         patch("app.services.download_manager.download_manager.resume_pending_downloads"):
        yield

@pytest.fixture(scope="function")
async def client(
    db_session: AsyncSession, mock_cache_manager, mock_scheduler, mock_download_manager
) -> AsyncGenerator[AsyncClient, None]:
    """Create a new FastAPI TestClient that uses the `db_session` fixture and mocked cache."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Mock download_dir to use a temp dir
    import tempfile

    temp_dir = os.path.join(tempfile.gettempdir(), "audiovault_test_downloads")
    with patch("app.core.config.settings.DOWNLOAD_DIR", temp_dir):
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://localhost"
        ) as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="session", autouse=True)
async def cleanup_engine():
    yield
    await engine.dispose()

