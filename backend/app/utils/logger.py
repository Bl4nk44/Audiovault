import logging
import sys
from collections.abc import Iterable
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import cast

from app.core.config import settings

_RESET = "\033[0m"
_BOLD = "\033[1m"
_LEVEL_COLORS = {
    logging.DEBUG: "\033[36m",  # cyan
    logging.INFO: "\033[32m",  # green
    logging.WARNING: "\033[33m",  # yellow
    logging.ERROR: "\033[31m",  # red
    logging.CRITICAL: "\033[1;31m",  # bold red
}


class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        return record.getMessage().find("/health") == -1


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        copy = logging.makeLogRecord(record.__dict__)
        color = _LEVEL_COLORS.get(copy.levelno, _RESET)
        copy.levelname = f"{color}{copy.levelname:<8}{_RESET}"
        copy.name = f"\033[90m{copy.name:<30}{_RESET}"
        return super().format(copy)


_STREAM_FORMAT = "%(levelname)s | %(name)s | %(message)s"
_FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"


def setup_logging():
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    LOGS_DIR = BASE_DIR / "logs"
    LOGS_DIR.mkdir(exist_ok=True)
    LOG_FILE = LOGS_DIR / "audiovault.log"

    logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(ColorFormatter(_STREAM_FORMAT))

    file_handler = TimedRotatingFileHandler(
        filename=LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(_FILE_FORMAT))

    logging.basicConfig(
        level=settings.LOG_LEVEL,
        handlers=cast(Iterable[logging.Handler], [stream_handler, file_handler]),
        force=True,
    )

    logging.getLogger("passlib").setLevel(logging.ERROR)

    logging.getLogger("app").info(f"Logging setup complete. Logs writing to: {LOG_FILE}")
