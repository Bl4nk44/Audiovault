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
    """
    import aiohttp
    from app.core.config import settings

    github_url = "https://api.github.com/repos/Bl4nk44/Audiovault/releases/latest"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(github_url) as response:
                if response.status == 200:
                    data = await response.json()
                    latest_version = data.get("tag_name", "").lstrip("v")
                    current_version = settings.VERSION.lstrip("v")
                    
                    # Simple string comparison or semantic versioning check
                    # Assuming semantic versioning (major.minor.patch)
                    # For now, just string equality or simple inequality
                     
                    update_available = latest_version != current_version
                    
                    return {
                        "current_version": current_version,
                        "latest_version": latest_version,
                        "update_available": update_available,
                        "release_url": data.get("html_url")
                    }
                else:
                    logger.warning(f"Failed to fetch updates from GitHub: {response.status}")
                    return {"error": "Could not fetch updates"}
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
        return {"error": str(e)}
