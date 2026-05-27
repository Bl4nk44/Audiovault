"""
Main Subsonic API router.

Mounts all Subsonic API handlers under /rest prefix.
"""

import logging

from fastapi import APIRouter, Depends, Request, Response

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
    """Catch-all for Subsonic to debug 404s."""
    log_line = f"DEBUG 404: {request.method} /rest/{path_name} | Params: {dict(request.query_params)}\n"
    try:
        with open("/app/subsonic_debug.log", "a") as f:
            f.write(log_line)
    except Exception as e:
        logger.warning("Failed to write subsonic debug log: %s", e)
    logger.debug(log_line.rstrip())
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?>\n'
        '<subsonic-response xmlns="http://subsonic.org/restapi" status="failed" version="1.16.1">'
        '<error code="70" message="The requested data was not found"/>'
        "</subsonic-response>",
        media_type="application/xml",
        status_code=404,
    )
