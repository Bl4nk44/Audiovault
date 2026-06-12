"""
Main Subsonic API router.

Mounts all Subsonic API handlers under /rest prefix.
"""

import logging

from fastapi import APIRouter, Depends, Request

from app.api.subsonic.handlers import (
    browse,
    info,
    lists,
    lyrics,
    media,
    playlist,
    search,
    system,  # Contains ping, getLicense, getToken
    user,
)
from app.schemas.subsonic.base import subsonic_error
from app.utils.log_sanitize import sanitize_log

logger = logging.getLogger(__name__)


def log_subsonic_request(request: Request):
    """Debug log for Subsonic requests to identify mobile client issues."""
    path = request.url.path
    params = dict(request.query_params)
    # Mask sensitive params
    if "p" in params:
        params["p"] = "***"
    if "t" in params:
        params["t"] = "***"

    log_line = f"DEBUG: {path} | Params: {params}\n"
    try:
        with open("/app/subsonic_debug.log", "a") as f:
            f.write(log_line)
    except Exception as e:
        logger.warning("Failed to write subsonic debug log: %s", e)
    logger.debug(log_line.rstrip())


# Create main router with logging dependency
router = APIRouter(
    prefix="/rest", tags=["subsonic"], dependencies=[Depends(log_subsonic_request)], redirect_slashes=False
)

# Include all handler routers
router.include_router(system.router)
router.include_router(browse.router)
router.include_router(search.router)
router.include_router(media.router)
router.include_router(playlist.router)
router.include_router(user.router)
router.include_router(lists.router)
router.include_router(lyrics.router)
router.include_router(info.router)


@router.api_route("/{path_name:path}", methods=["GET", "POST"])
def catch_all_subsonic(request: Request, path_name: str):
    """
    Catch-all for unknown Subsonic methods.

    Subsonic clients expect HTTP 200 with an error envelope for every request; a
    raw HTTP 404 makes some clients abort the whole sync. Return error code 70
    ("not found") with HTTP 200 in the format the client requested.
    """
    safe_method = sanitize_log(request.method)
    safe_path = sanitize_log(path_name)
    safe_params = sanitize_log(dict(request.query_params))
    log_line = f"DEBUG 404: {safe_method} /rest/{safe_path} | Params: {safe_params}\n"
    try:
        with open("/app/subsonic_debug.log", "a") as f:
            f.write(log_line)
    except Exception as e:
        logger.warning("Failed to write subsonic debug log: %s", e)
    logger.debug("%s", log_line.rstrip())
    response_format = request.query_params.get("f", "xml")
    return subsonic_error(70, "The requested data was not found", f=response_format)
