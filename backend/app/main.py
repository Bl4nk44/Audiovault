from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

from app.api.v1 import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)

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

@app.get("/")
async def root():
    return {"message": "Welcome to Spotizerr 3.0 API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

from fastapi.staticfiles import StaticFiles
import os

# Ensure download directory exists
if not os.path.exists(settings.DOWNLOAD_DIR):
    os.makedirs(settings.DOWNLOAD_DIR)

app.mount("/stream", StaticFiles(directory=settings.DOWNLOAD_DIR), name="stream")

from app.services.socket_manager import socket_manager
app.mount("/", socket_manager.app)

from app.db.database import AsyncSessionLocal
from app.db.init_data import init_db

# Import models to ensure they are registered
from app.models.user import User
from app.models.track import Track
from app.models.download import Download
from app.models.credentials import ServiceCredentials
from app.models.watchlist import Watchlist
from app.models.history import ListeningHistory
from app.models.recommendation import PlaylistRecommendation
from app.models.profile import ListenerProfile

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
            print(f"Database not ready, retrying in 2 seconds... ({i+1}/{retries})")
            await asyncio.sleep(2)

    # Init data
    async with AsyncSessionLocal() as session:
        await init_db(session)
