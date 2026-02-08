import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/icde.db")

# File uploads
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

# File size limit (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

# Preview settings
PREVIEW_ROWS = 10
MAX_SAMPLE_VALUES = 5
