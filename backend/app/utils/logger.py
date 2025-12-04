import logging
import sys
from app.core.config import settings

class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        return record.getMessage().find("/health") == -1

def setup_logging():
    logger = logging.getLogger("uvicorn.access")
    logger.addFilter(HealthCheckFilter())
    
    # Root logger configuration
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Silence some noisy libraries
    logging.getLogger("passlib").setLevel(logging.ERROR)
