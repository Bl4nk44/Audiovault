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
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession, expire_on_commit=False)

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
    with patch("app.core.cache.cache_manager") as mock_cache:
        mock_cache.get.return_value = None
        mock_cache.redis = MagicMock()
        yield mock_cache

@pytest.fixture(scope="function")
async def client(db_session: AsyncSession, mock_cache_manager) -> AsyncGenerator[AsyncClient, None]:
    """Create a new FastAPI TestClient that uses the `db_session` fixture and mocked cache."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    # Mock download_dir to use a temp dir
    with patch("app.core.config.settings.DOWNLOAD_DIR", "/tmp/audiovault_test_downloads"):
        if not os.path.exists("/tmp/audiovault_test_downloads"):
            os.makedirs("/tmp/audiovault_test_downloads", exist_ok=True)
            
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    
    app.dependency_overrides.clear()
