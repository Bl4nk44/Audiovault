import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Iterable, cast

from app.core.config import settings


class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        return record.getMessage().find("/health") == -1


def setup_logging():
    # Define logs directory
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    LOGS_DIR = BASE_DIR / "logs"
    LOGS_DIR.mkdir(exist_ok=True)
    LOG_FILE = LOGS_DIR / "audiovault.log"

    logger = logging.getLogger("uvicorn.access")
    logger.addFilter(HealthCheckFilter())

    # Root logger configuration
    handlers = [
        logging.StreamHandler(sys.stdout),
        TimedRotatingFileHandler(
            filename=LOG_FILE,
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        ),
    ]

    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=cast(Iterable[logging.Handler], handlers),
        force=True,
    )

    # Silence some noisy libraries
    logging.getLogger("passlib").setLevel(logging.ERROR)

    main_logger = logging.getLogger("app")
    main_logger.info(f"Logging setup complete. Logs writing to: {LOG_FILE}")
