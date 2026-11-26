"""ICDE backend test package initialization.

Ensures test runs always use in-memory SQLite and an isolated temporary upload directory
so `backend/uploads/` and workspace files remain completely untouched.
"""

import atexit
import os
import shutil
import tempfile
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

_PYTEST_UPLOAD_TMP = Path(tempfile.mkdtemp(prefix="icde_test_uploads_"))
os.environ.setdefault("ICDE_UPLOAD_DIR", str(_PYTEST_UPLOAD_TMP))
atexit.register(shutil.rmtree, _PYTEST_UPLOAD_TMP, True)

import app.config as _app_config  # noqa: E402
import app.routers.datasets as _datasets_router  # noqa: E402

_app_config.UPLOAD_DIR = _PYTEST_UPLOAD_TMP
_datasets_router.UPLOAD_DIR = _PYTEST_UPLOAD_TMP
