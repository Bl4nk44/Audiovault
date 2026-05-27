import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Audiovault"

    @staticmethod
    def _get_version() -> str:
        try:
            # Try finding VERSION file up to 4 levels up
            # Docker/Prod: backend/ (copied to root of container) -> parent.parent.parent
            # Dev/CI: root -> parent.parent.parent.parent
            path = Path(__file__).resolve()
            for _ in range(4):
                path = path.parent
                version_file = path / "VERSION"
                if version_file.exists():
                    return version_file.read_text().strip()
            return "0.0.0"
        except Exception:
            return "0.0.0"

    VERSION: str = _get_version()
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///dummy")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://dummy")

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "unsafe_secret_key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"  # noqa: S105

    # Spotify — optional: your own app credentials (overrides embedded fallback)
    SPOTIFY_CLIENT_ID: str | None = None
    SPOTIFY_CLIENT_SECRET: str | None = None
    # sp_dc cookie fallback (any free account, ~1 year TTL)
    # How to get: open.spotify.com → DevTools → Application → Cookies → sp_dc
    SPOTIFY_SP_DC: str | None = None
    # Host proxy for embed scraping — run spotify-host-proxy.py on WSL2 host
    SPOTIFY_HOST_PROXY: str | None = None

    # Genius API for lyrics
    GENIUS_API_TOKEN: str | None = None

    # Last.fm API
    LASTFM_API_KEY: str | None = None
    LASTFM_API_SECRET: str | None = None

    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", os.path.join(os.getcwd(), "downloads"))
    MAX_PARALLEL_DOWNLOADS: int = 3
    STORAGE_QUOTA_GB: int = 500
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"
    TIMEZONE: str = os.getenv("TIMEZONE", "UTC")

    BACKEND_CORS_ORIGINS: list[str] | str = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    ALLOWED_HOSTS: list[str] | str = ["localhost", "127.0.0.1", "0.0.0.0"]  # nosec B104  # noqa: S104

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

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
