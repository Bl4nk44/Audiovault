import asyncio
import logging
from collections import deque
from pathlib import Path

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_log_file_path() -> Path:
    # Calculate path relative to this file
    # this file: backend/app/api/v1/system.py
    # base dir: backend/
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    return base_dir / "logs" / "audiovault.log"


def _read_last_lines(file_path: Path, lines_count: int) -> list[str]:
    try:
        if not file_path.exists():
            return [f"Log file not found at: {file_path}"]
        with open(file_path, encoding="utf-8", errors="replace") as f:  # nosemgrep: path-traversal
            return list(deque(f, lines_count))
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        raise e


@router.get("/logs", response_model=list[str])
async def get_system_logs(lines: Annotated[int, Query(ge=1, le=5000)] = 500):
    """
    Retrieve the last N lines of the system log asynchronously.
    """
    log_file = _get_log_file_path()

    try:
        import functools

        loop = asyncio.get_event_loop()
        # Use run_in_executor to avoid blocking the event loop with file I/O
        return await loop.run_in_executor(None, functools.partial(_read_last_lines, log_file, lines))
    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to read logs")


@router.get("/logs/download")
async def download_system_logs():
    """
    Download the full system log file.
    """
    log_file = _get_log_file_path()

    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log file not found")

    return FileResponse(path=log_file, filename="audiovault.log", media_type="text/plain")


async def _check_production_update(settings):
    import aiohttp

    github_url = "https://api.github.com/repos/Bl4nk44/Audiovault/releases/latest"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(github_url) as response:
                if response.status == 200:
                    data = await response.json()
                    latest_tag = data.get("tag_name", "").lstrip("v")
                    current_ver = settings.VERSION.lstrip("v")

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
                        "release_url": data.get("html_url"),
                    }
                else:
                    logger.warning(f"Failed to fetch updates from GitHub (Prod): {response.status}")
                    return {"error": "Could not fetch updates"}
    except Exception as e:
        logger.error(f"Error checking for updates (Prod): {e}")
        return {"error": str(e)}


def _get_local_git_sha(git_dir: Path) -> str:
    """Read local Git HEAD SHA."""
    try:
        head_file = git_dir / "HEAD"
        if head_file.exists():
            ref = head_file.read_text().strip()
            if ref.startswith("ref:"):
                ref_path = git_dir / ref[5:].strip()
                result = ref_path.read_text().strip() if ref_path.exists() else "unknown (packed)"
                return result
            # Detached HEAD
            return ref
    except Exception:
        pass
    return "unknown"


async def _check_development_update():
    import aiohttp

    # Check local git HEAD
    git_dir = Path("/app/.git")
    if not git_dir.exists():
        # Fallback if .git not mounted
        logger.warning("Development mode but .git not found. Cannot check for commit updates.")
        return {"update_available": False, "latest_version": "Unknown (No .git)"}

    local_sha = _get_local_git_sha(git_dir)

    try:
        # Check remote 'dev' branch
        github_url = "https://api.github.com/repos/Bl4nk44/Audiovault/commits/dev"
        async with aiohttp.ClientSession() as session:
            async with session.get(github_url) as response:
                if response.status == 200:
                    data = await response.json()

                    # Handling dictionary return typing securely
                    remote_sha = data.get("sha")
                    remote_sha_str = str(remote_sha) if remote_sha else "unknown"

                    update_available = local_sha != remote_sha

                    return {
                        "current_version": str(local_sha)[:7] if local_sha else "unknown",
                        "latest_version": remote_sha_str[:7],
                        "update_available": update_available,
                        "release_url": data.get("html_url"),
                    }
                else:
                    logger.warning(f"Failed to fetch updates from GitHub (Dev): {response.status}")
                    return {"error": "Could not fetch updates"}

    except Exception as e:
        logger.error(f"Error checking for updates (Dev): {e}")
        return {"error": str(e)}


@router.get("/check-update")
async def check_for_updates():
    """
    Check for available updates on GitHub.

    Logic depends on ENVIRONMENT:
    - production: Compare VERSION file with latest GitHub Release tag.
    - development: Compare local git HEAD with latest commit on 'dev' branch.
    """
    from app.core.config import settings

    if settings.ENVIRONMENT == "production":
        return await _check_production_update(settings)
    else:
        return await _check_development_update()


@router.get("/stats")
async def get_system_stats():
    """
    Get system statistics (CPU, RAM, Disk, Network).
    Requires psutil to be installed.
    """
    try:
        import psutil
    except ImportError:
        raise HTTPException(status_code=503, detail="psutil library is not installed. Statistics are unavailable.")

    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=None)

        # Memory
        mem = psutil.virtual_memory()
        ram_total = mem.total
        ram_used = mem.used
        ram_percent = mem.percent

        # Disk
        disk = psutil.disk_usage("/")
        disk_total = disk.total
        disk_used = disk.used
        disk_percent = disk.percent

        # Network (Bytes since boot)
        net = psutil.net_io_counters()
        net_sent = net.bytes_sent
        net_recv = net.bytes_recv

        return {
            "cpu": {"percent": cpu_percent},
            "memory": {"total": ram_total, "used": ram_used, "percent": ram_percent},
            "disk": {"total": disk_total, "used": disk_used, "percent": disk_percent},
            "network": {"sent": net_sent, "recv": net_recv},
        }
    except Exception as e:
        logger.error(f"Error gathering system stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to gather system stats: {str(e)}")
