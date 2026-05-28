import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator

from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.providers import provider_manager
from app.schemas.metadata import PlaylistMetadata
from app.utils.log_sanitize import sanitize_log

router = APIRouter()
logger = logging.getLogger(__name__)


class ImportRequest(BaseModel):
    url: str

    @property
    def is_valid_domain(self) -> bool:
        from urllib.parse import urlparse

        allowed_domains = {
            "spotify.com",
            "open.spotify.com",
            "tidal.com",
            "listen.tidal.com",
            "music.apple.com",
            "apple.co",
            "youtube.com",
            "www.youtube.com",
            "youtu.be",
            "music.youtube.com",
            "deezer.com",
            "www.deezer.com",
            "soundcloud.com",
            "m.soundcloud.com",
            "music.amazon.com",
            "amazon.com",
        }
        try:
            parsed = urlparse(self.url)

            # Check scheme
            if parsed.scheme not in ("http", "https"):
                return False

            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]

            # Check for exact matches or subdomains (simplified for now to exact allowed list or ends with)
            return any(domain == allowed or domain.endswith("." + allowed) for allowed in allowed_domains)
        except Exception:
            return False

    @model_validator(mode="after")
    def validate_url(self):
        if not self.is_valid_domain:
            raise ValueError(f"Invalid URL: {self.url}. Domain not supported or invalid scheme.")
        return self


@router.post(
    "/playlist",
    response_model=PlaylistMetadata,
    responses={404: {"description": "Not found"}, 500: {"description": "Internal server error"}},
)
async def import_playlist(
    request: ImportRequest,
    _: Annotated[User, Depends(get_current_active_user)] = ...,
):
    """
    Import a playlist from a URL (Tidal, SoundCloud, Apple Music, etc.)
    using the Universal Provider system.
    Returns the extracted metadata for preview.
    """
    logger.info("Importing playlist from URL: %s", sanitize_log(request.url))

    try:
        playlist = await provider_manager.extract_playlist(request.url)
        if not playlist:
            raise HTTPException(
                status_code=404,
                detail="Could not extract playlist. Provider returned no data.",
            )

        logger.info(
            f"Extracted {len(playlist.tracks)} tracks from {playlist.title}"
        )  # nosemgrep: python.fastapi.log.tainted-log-injection-stdlib-fastapi.tainted-log-injection-stdlib-fastapi
        return playlist

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
