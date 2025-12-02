from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Spotizerr 3.0"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str
    REDIS_URL: str
    
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    SPOTIFY_CLIENT_ID: Optional[str] = None
    SPOTIFY_CLIENT_SECRET: Optional[str] = None
    SPOTIFY_REDIRECT_URI: Optional[str] = None
    
    YOUTUBE_API_KEY: Optional[str] = None
    DEEZER_API_KEY: Optional[str] = None
    
    DOWNLOAD_DIR: str = "/downloads"
    MAX_PARALLEL_DOWNLOADS: int = 3
    STORAGE_QUOTA_GB: int = 500
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
