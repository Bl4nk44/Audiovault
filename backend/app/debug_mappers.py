import sys
import os

# Add /app to pythonpath if needed
sys.path.append(os.getcwd())

from app.db.base import Base
import app.models
from sqlalchemy.orm import configure_mappers

print("Configuring mappers...")
try:
    configure_mappers()
    print("Mappers OK")
except Exception as e:
    print("-------------------------")
    print(f"ERROR: {e}")
    print("-------------------------")
    sys.exit(1)
