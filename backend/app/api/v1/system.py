from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
from typing import List
from collections import deque
import logging
import asyncio
from fastapi.responses import FileResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_log_file_path() -> Path:
    # Calculate path relative to this file
    # this file: backend/app/api/v1/system.py
    # base dir: backend/
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    return base_dir / "logs" / "audiovault.log"


def _read_last_lines(file_path: Path, lines_count: int) -> List[str]:
    try:
        if not file_path.exists():
            return [f"Log file not found at: {file_path}"]
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return list(deque(f, lines_count))
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        raise e


@router.get("/logs", response_model=List[str])
async def get_system_logs(lines: int = Query(500, ge=1, le=5000)):
    """
    Retrieve the last N lines of the system log asynchronously.
    """
    log_file = _get_log_file_path()

    try:
        loop = asyncio.get_event_loop()
        # Use run_in_executor to avoid blocking the event loop with file I/O
        return await loop.run_in_executor(None, _read_last_lines, log_file, lines)
    except Exception as e:
        # Rethrow as HTTP exception if it wasn't handled inside (though helper re-raises)
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")


@router.get("/logs/download")
async def download_system_logs():
    """
    Download the full system log file.
    """
    log_file = _get_log_file_path()

    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log file not found")

    return FileResponse(
        path=log_file, filename="audiovault.log", media_type="text/plain"
    )


@router.get("/check-update")
async def check_for_updates():
    """
    Check for available updates on GitHub.
    
    Logic depends on ENVIRONMENT:
    - production: Compare VERSION file with latest GitHub Release tag.
    - development: Compare local git HEAD with latest commit on 'dev' branch.
    """
    import aiohttp
    from app.core.config import settings
    
    # 1. PRODUCTION CHECK (Releases)
    if settings.ENVIRONMENT == "production":
        github_url = "https://api.github.com/repos/Bl4nk44/Audiovault/releases/latest"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(github_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        latest_tag = data.get("tag_name", "").lstrip("v")
                        current_ver = settings.VERSION.lstrip("v")
                        
                        # Helper to parse version string to tuple of ints
                        def parse_version(v_str):
                            try:
                                # Remove any suffixes like -beta, -rc for basic comparison if needed
                                # or keep it simple: take first 3 parts
                                base = v_str.split("-")[0]
                                return tuple(map(int, base.split(".")))
                            except (ValueError, AttributeError):
                                return (0, 0, 0)

                        latest_tuple = parse_version(latest_tag)
                        current_tuple = parse_version(current_ver)
                        
                        # Only notify if latest is strictly greater than current
                        update_available = latest_tuple > current_tuple
                        
                        return {
                            "current_version": current_ver,
                            "latest_version": latest_tag,
                            "update_available": update_available,
                            "release_url": data.get("html_url")
                        }
                    else:
                        logger.warning(f"Failed to fetch updates from GitHub (Prod): {response.status}")
                        return {"error": "Could not fetch updates"}
        except Exception as e:
             logger.error(f"Error checking for updates (Prod): {e}")
             return {"error": str(e)}

    # 2. DEVELOPMENT CHECK (Commits)
    else:
        # Check local git HEAD
        git_dir = Path("/app/.git")
        if not git_dir.exists():
             # Fallback if .git not mounted
             logger.warning("Development mode but .git not found. Cannot check for commit updates.")
             return {"update_available": False, "latest_version": "Unknown (No .git)"}
             
        try:
            # Read local HEAD SHA
            head_file = git_dir / "HEAD"
            if head_file.exists():
                ref = head_file.read_text().strip()
                if ref.startswith("ref:"):
                    ref_path = git_dir / ref[5:].strip()
                    if ref_path.exists():
                        local_sha = ref_path.read_text().strip()
                    else:
                        local_sha = "unknown"
                else:
                    local_sha = ref # Detached HEAD
            else:
                 local_sha = "unknown"

            # Check remote 'dev' branch
            github_url = "https://api.github.com/repos/Bl4nk44/Audiovault/commits/dev"
            async with aiohttp.ClientSession() as session:
                async with session.get(github_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        remote_sha = data.get("sha")
                        
                        update_available = local_sha != remote_sha
                        
                        return {
                            "current_version": local_sha[:7],
                            "latest_version": remote_sha[:7],
                            "update_available": update_available,
                            "release_url": data.get("html_url")
                        }
                    else:
                         logger.warning(f"Failed to fetch updates from GitHub (Dev): {response.status}")
                         return {"error": "Could not fetch updates"}
                         
        except Exception as e:
            logger.error(f"Error checking for updates (Dev): {e}")
            return {"error": str(e)}
