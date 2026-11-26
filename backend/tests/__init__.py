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


def _cleanup_pytest_uploads() -> None:
    if not _PYTEST_UPLOAD_TMP.exists():
        return
    for root_str, dirs, files in os.walk(_PYTEST_UPLOAD_TMP, topdown=True):
        root = Path(root_str)
        try:
            os.chmod(root, 0o700)
        except OSError:
            pass
        for dname in dirs:
            try:
                os.chmod(root / dname, 0o700)
            except OSError:
                pass
        for fname in files:
            try:
                os.chmod(root / fname, 0o600)
            except OSError:
                pass
    shutil.rmtree(_PYTEST_UPLOAD_TMP, ignore_errors=True)


atexit.register(_cleanup_pytest_uploads)

import app.config as _app_config  # noqa: E402
import app.routers.datasets as _datasets_router  # noqa: E402

_app_config.UPLOAD_DIR = _PYTEST_UPLOAD_TMP
_datasets_router.UPLOAD_DIR = _PYTEST_UPLOAD_TMP
