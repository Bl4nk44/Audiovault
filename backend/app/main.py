import asyncio
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_limiter import FastAPILimiter
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app import models  # noqa: F401 - Ensure models are registered
from app.api.subsonic import router as subsonic_router
from app.api.v1 import (
    artists,
    audit,
    auth,
    dashboard,
    deezer,
    downloads,
    history,
    import_routes,
    lyrics,
    playlists,
    spotify,
    storage,
    stream,
    sync,
    system,
    users,
    watchlist,
    youtube,
)
from app.api.v1 import settings as settings_router
from app.core.cache import cache_manager
from app.core.config import settings
from app.db.base import Base
from app.db.database import AsyncSessionLocal, engine
from app.db.init_data import init_db
from app.services.download_manager import download_manager
from app.services.scheduler import scheduler_service
from app.services.socket_manager import socket_manager
from app.utils.logger import setup_logging

# Setup logging before app startup
setup_logging()

logger = logging.getLogger(__name__)

application = FastAPI(
    title=settings.PROJECT_NAME,
    description="Audiovault API for downloading and managing music",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Trusted Host Middleware (Security)
application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Proxy Headers Middleware (for Reverse Proxies like Nginx/Traefik)


application.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# CORS
origins = settings.BACKEND_CORS_ORIGINS

application.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

application.add_middleware(GZipMiddleware, minimum_size=1000)

# Include Routers
application.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
application.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
application.include_router(downloads.router, prefix="/api/v1/downloads", tags=["downloads"])
application.include_router(artists.router, prefix="/api/v1/artists", tags=["artists"])
application.include_router(watchlist.router, prefix="/api/v1/watchlist", tags=["watchlist"])
application.include_router(import_routes.router, prefix="/api/v1/import", tags=["import"])
application.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])
application.include_router(history.router, prefix="/api/v1/history", tags=["history"])
application.include_router(youtube.router, prefix="/api/v1/youtube", tags=["youtube"])
application.include_router(users.router, prefix="/api/v1/users", tags=["users"])
application.include_router(stream.router, prefix="/api/v1/stream", tags=["stream"])
application.include_router(spotify.router, prefix="/api/v1/spotify", tags=["spotify"])
application.include_router(deezer.router, prefix="/api/v1/deezer", tags=["deezer"])
application.include_router(sync.router, prefix="/api/v1/sync", tags=["sync"])
application.include_router(system.router, prefix="/api/v1/system", tags=["system"])
application.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])
application.include_router(lyrics.router, prefix="/api/v1/lyrics", tags=["lyrics"])
application.include_router(playlists.router, prefix="/api/v1/playlists", tags=["playlists"])
application.include_router(storage.router, prefix="/api/v1/storage", tags=["storage"])

# Subsonic API (compatible with Sonixd, Amperfy, DSub, etc.)
application.include_router(subsonic_router)


@application.get("/")
async def root():
    return {"message": "Welcome to Audiovault API"}


@application.get("/health")
async def health_check():
    return {"status": "healthy"}


@application.get("/api/version")
async def get_version():
    return {"version": settings.VERSION}


# Ensure download directory exists
if not os.path.exists(settings.DOWNLOAD_DIR):
    os.makedirs(settings.DOWNLOAD_DIR)
try:
    os.chmod(settings.DOWNLOAD_DIR, 0o755)
except Exception as e:
    logger.warning(f"Could not set permissions on {settings.DOWNLOAD_DIR}: {e}")

logger.info(f"📂 Mounting StaticFiles from: {settings.DOWNLOAD_DIR}")
try:
    files = os.listdir(settings.DOWNLOAD_DIR)
    logger.info(f"📂 Files in {settings.DOWNLOAD_DIR}: {files}")
except Exception as e:
    logger.error(f"❌ Error listing files: {e}")

application.mount("/stream", StaticFiles(directory=settings.DOWNLOAD_DIR), name="stream")
# Mount static files (avatars, etc.)
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
application.mount("/static", StaticFiles(directory=static_dir), name="static")

application.mount("/socket.io", socket_manager.app)


@application.on_event("startup")
async def startup_event():
    banner = r"""
        _             _ _                       _ _
       / \  _   _  __| (_) _____   ____ _ _   _| | |_
      / _ \| | | |/ _` | |/ _ \ \ / / _` | | | | | __|
     / ___ \ |_| | (_| | | (_) \ V / (_| | |_| | | |_
    /_/   \_\__,_|\__,_|_|\___/ \_/ \__,_|\__,_|_|\__|

    """
    logger.info(banner)
    print(banner)  # Ensure it prints to console even if logs are diverted

    # Create tables with retry logic
    retries = 5
    for i in range(retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            break
        except Exception as e:
            if i == retries - 1:
                raise e
            logger.info(f"Database not ready, retrying in 2 seconds... ({i + 1}/{retries})")
            await asyncio.sleep(2)

    # Init data
    async with AsyncSessionLocal() as session:
        await init_db(session)
        # Resume pending downloads
        await download_manager.resume_pending_downloads(session)

    # Connect to Redis
    await cache_manager.connect()

    # Init Rate Limiter
    if cache_manager.redis:
        await FastAPILimiter.init(cache_manager.redis)

    # Start Scheduler
    scheduler_service.start()


@application.on_event("shutdown")
async def shutdown_event():
    await cache_manager.close()
    scheduler_service.stop()


# Alias for ASGI compatibility (uvicorn looks for 'app' by default)
app = application
