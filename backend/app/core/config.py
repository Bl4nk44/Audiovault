import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Audiovault"
    VERSION: str = Path(__file__).parent.parent.parent.joinpath("VERSION").read_text().strip()
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///dummy")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://dummy")

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "unsafe_secret_key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    FIRST_SUPERUSER: str = "admin@example.com"
    FIRST_SUPERUSER_USERNAME: str = "admin"
    FIRST_SUPERUSER_PASSWORD: str = "admin"

    SPOTIFY_CLIENT_ID: str | None = None
    SPOTIFY_CLIENT_SECRET: str | None = None
    SPOTIFY_REDIRECT_URI: str | None = None

    YOUTUBE_API_KEY: str | None = None
    DEEZER_API_KEY: str | None = None

    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", str(Path.home() / "Downloads" / "Audiovault"))
    MAX_PARALLEL_DOWNLOADS: int = 3
    STORAGE_QUOTA_GB: int = 500
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"

    BACKEND_CORS_ORIGINS: list[str] | str = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    ALLOWED_HOSTS: list[str] | str = ["localhost", "127.0.0.1", "0.0.0.0"]

    @field_validator("BACKEND_CORS_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_list_from_str(cls, v: str | list[str]) -> list[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    @field_validator("DOWNLOAD_DIR")
    @classmethod
    def validate_download_dir(cls, v: str) -> str:
        # Fix for Windows running with Docker config
        if os.name == "nt":
            # If path looks like Unix absolute path (e.g. /downloads)
            if v.startswith("/"):
                # Always check for project-local 'downloads' folder first on Windows
                # This fixes the issue where dev environment has files in ./downloads
                # but .env points to /downloads (Docker volume)
                cwd_downloads = os.path.join(os.getcwd(), "downloads")
                if os.path.exists(cwd_downloads):
                    return cwd_downloads

                # Fallback logic if local folder doesn't exist
                if not os.path.exists(v):
                    rel_path = v.lstrip("/")
                    if os.path.exists(rel_path):
                        return rel_path
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
