from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.utils.logger import setup_logging

# Setup logging before app startup
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Audiovault API for downloading and managing music",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

from app.api.v1 import artists, downloads, metadata, watchlist, import_routes, auth, dashboard, history, youtube, users, stream, spotify, deezer, sync, network
from app.api.v1 import settings as settings_router

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(downloads.router, prefix="/api/v1/downloads", tags=["downloads"])
app.include_router(metadata.router, prefix="/api/v1/metadata", tags=["metadata"])
app.include_router(artists.router, prefix="/api/v1/artists", tags=["artists"])
app.include_router(watchlist.router, prefix="/api/v1/watchlist", tags=["watchlist"])
app.include_router(import_routes.router, prefix="/api/v1/import", tags=["import"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(history.router, prefix="/api/v1/history", tags=["history"])
app.include_router(youtube.router, prefix="/api/v1/youtube", tags=["youtube"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(stream.router, prefix="/api/v1/stream", tags=["stream"])
app.include_router(spotify.router, prefix="/api/v1/spotify", tags=["spotify"])
app.include_router(deezer.router, prefix="/api/v1/deezer", tags=["deezer"])
app.include_router(sync.router, prefix="/api/v1/sync", tags=["sync"])
app.include_router(network.router, prefix="/api/v1/network", tags=["network"])

# CORS
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/")
async def root():
    return {"message": "Welcome to Audiovault API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/version")
async def get_version():
    return {"version": settings.VERSION}

from fastapi.staticfiles import StaticFiles
import os

# Ensure download directory exists
if not os.path.exists(settings.DOWNLOAD_DIR):
    os.makedirs(settings.DOWNLOAD_DIR)

# Debug: List files in download directory on startup
import logging
logger = logging.getLogger(__name__)

logger.info(f"📂 Mounting StaticFiles from: {settings.DOWNLOAD_DIR}")
try:
    files = os.listdir(settings.DOWNLOAD_DIR)
    logger.info(f"📂 Files in {settings.DOWNLOAD_DIR}: {files}")
except Exception as e:
    logger.error(f"❌ Error listing files: {e}")

app.mount("/stream", StaticFiles(directory=settings.DOWNLOAD_DIR), name="stream")

from app.services.socket_manager import socket_manager
app.mount("/socket.io", socket_manager.app)

from app.db.database import AsyncSessionLocal
from app.db.init_data import init_db

# Import models to ensure they are registered
from app.models.user import User
from app.models.track import Track
from app.models.download import Download
from app.models.credentials import ServiceCredentials
from app.models.watchlist import Watchlist
from app.models.history import ListeningHistory


@app.on_event("startup")
async def startup_event():
    # Create tables with retry logic
    from app.db.base import Base
    from app.db.database import engine
    import asyncio
    from sqlalchemy.exc import OperationalError
    
    retries = 5
    for i in range(retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            break
        except Exception as e:
            if i == retries - 1:
                raise e
            logger.info(f"Database not ready, retrying in 2 seconds... ({i+1}/{retries})")
            await asyncio.sleep(2)

    # Init data
    async with AsyncSessionLocal() as session:
        await init_db(session)
        
        # Resume pending downloads
        from app.services.download_manager import download_manager
        await download_manager.resume_pending_downloads(session)

    # Connect to Redis
    from app.core.cache import cache_manager
    await cache_manager.connect()
    
    # Init Rate Limiter
    from fastapi_limiter import FastAPILimiter
    if cache_manager.redis:
        await FastAPILimiter.init(cache_manager.redis)

    # Start Scheduler
    from app.services.scheduler import scheduler_service
    scheduler_service.start()

@app.on_event("shutdown")
async def shutdown_event():
    from app.core.cache import cache_manager
    await cache_manager.close()
    
    from app.services.scheduler import scheduler_service
    scheduler_service.stop()
