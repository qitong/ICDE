"""
Pytest fixtures for ICDE backend tests.
"""
import os
import tempfile
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure any default engine initialization uses in-memory SQLite rather than icde.db
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.models.base import Base
# Import all models to ensure they're registered with Base.metadata
from app.models.dataset import Dataset, DatasetFile, DatasetLineage, DatasetType  # noqa: F401
from app.models.script import Script  # noqa: F401
from app.models.chat import Conversation, ChatMessage, LLMSetting  # noqa: F401
from app.models.project import Project  # noqa: F401
import app.config as app_config
import app.routers.datasets as datasets_router
import app.services.llm_service as llm_service_module


@pytest.fixture(autouse=True)
def isolate_upload_and_secret_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect UPLOAD_DIR and SECRET_KEY_FILE to tmp_path so tests never touch workspace files."""
    isolated_upload_dir = tmp_path / "uploads"
    isolated_upload_dir.mkdir(parents=True, exist_ok=True)
    isolated_secret_key = tmp_path / ".icde_secret_key"

    monkeypatch.setattr(app_config, "UPLOAD_DIR", isolated_upload_dir)
    monkeypatch.setattr(datasets_router, "UPLOAD_DIR", isolated_upload_dir)
    monkeypatch.setattr(app_config, "SECRET_KEY_FILE", isolated_secret_key)
    monkeypatch.setattr(llm_service_module, "SECRET_KEY_FILE", isolated_secret_key)
    monkeypatch.delenv("LLM_SECRET_KEY_FILE", raising=False)

    yield {
        "upload_dir": isolated_upload_dir,
        "secret_key_file": isolated_secret_key,
    }


def _create_memory_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, TestSession()


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test with all models registered."""
    engine, session = _create_memory_session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_with_llm():
    """Create a test database with LLM models registered (Conversation, ChatMessage, LLMSetting)."""
    engine, session = _create_memory_session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_upload_dir():
    """Create a temporary upload directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return """SUBJID,AGE,SEX,RANDFL,PPROTFL,SAFFL
P001,58,M,Y,N,Y
P002,45,F,Y,N,Y
P003,62,M,Y,Y,Y
P004,51,F,Y,N,Y
P005,55,M,N,N,N
"""


@pytest.fixture
def sample_csv_file(test_upload_dir, sample_csv_content):
    """Create a sample CSV file for testing."""
    file_path = test_upload_dir / "test_data.csv"
    file_path.write_text(sample_csv_content)
    return file_path


@pytest.fixture
def sample_script_code():
    """Sample script code for FAS generation."""
    return '''
import pandas as pd

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate FAS (Full Analysis Set).
    Include: RANDFL = 'Y'
    Exclude: PPROTFL = 'Y'
    """
    fas = df[
        (df['RANDFL'] == 'Y') &
        (df['PPROTFL'] != 'Y')
    ].copy()
    return fas
'''
