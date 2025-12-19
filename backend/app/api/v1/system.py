from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
from typing import List
from collections import deque
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/logs", response_model=List[str])
async def get_system_logs(lines: int = Query(500, ge=1, le=5000)):
    """
    Retrieve the last N lines of the system log.
    """
    # Calculate path relative to this file
    # this file: backend/app/api/v1/system.py
    # base dir: backend/
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    LOG_FILE = BASE_DIR / "logs" / "audiovault.log"
    
    if not LOG_FILE.exists():
        return [f"Log file not found at: {LOG_FILE}"]
        
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            # Efficiently read last N lines
            return list(deque(f, lines))
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")

from fastapi.responses import FileResponse

@router.get("/logs/download")
async def download_system_logs():
    """
    Download the full system log file.
    """
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    LOG_FILE = BASE_DIR / "logs" / "audiovault.log"
    
    if not LOG_FILE.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
        
    return FileResponse(
        path=LOG_FILE, 
        filename="audiovault.log", 
        media_type="text/plain"
    )
