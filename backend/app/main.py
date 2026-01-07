from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging
import asyncio
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.config import settings
from app.utils.logger import setup_logging
from app.api.v1 import (
    artists,
    downloads,
    watchlist,
    import_routes,
    auth,
    dashboard,
    history,
    youtube,
    users,
    stream,
    spotify,
    deezer,
    sync,
    system,
)
from app.api.v1 import settings as settings_router
from app.services.socket_manager import socket_manager
from app.db.database import AsyncSessionLocal
from app.db.init_data import init_db
from app.core.cache import cache_manager
from app.services.scheduler import scheduler_service
from app.services.download_manager import download_manager
from app.db.base import Base
from app.db.database import engine
from fastapi_limiter import FastAPILimiter

# Setup logging before app startup
setup_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Audiovault API for downloading and managing music",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Trusted Host Middleware (Security)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Proxy Headers Middleware (for Reverse Proxies like Nginx/Traefik)


app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# CORS
origins = settings.BACKEND_CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(downloads.router, prefix="/api/v1/downloads", tags=["downloads"])
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
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])


@app.get("/")
async def root():
    return {"message": "Welcome to Audiovault API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/version")
async def get_version():
    return {"version": settings.VERSION}


# Ensure download directory exists
if not os.path.exists(settings.DOWNLOAD_DIR):
    os.makedirs(settings.DOWNLOAD_DIR)

logger.info(f"📂 Mounting StaticFiles from: {settings.DOWNLOAD_DIR}")
try:
    files = os.listdir(settings.DOWNLOAD_DIR)
    logger.info(f"📂 Files in {settings.DOWNLOAD_DIR}: {files}")
except Exception as e:
    logger.error(f"❌ Error listing files: {e}")

app.mount("/stream", StaticFiles(directory=settings.DOWNLOAD_DIR), name="stream")
# Mount static files (avatars, etc.)
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.mount("/socket.io", socket_manager.app)


@app.on_event("startup")
async def startup_event():
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
            logger.info(
                f"Database not ready, retrying in 2 seconds... ({i + 1}/{retries})"
            )
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


@app.on_event("shutdown")
async def shutdown_event():
    await cache_manager.close()
    scheduler_service.stop()
