"""
Pytest fixtures for ICDE backend tests.
"""
import os
import tempfile
import pytest
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
# Import all models to ensure they're registered with Base.metadata
from app.models.dataset import Dataset, DatasetFile, DatasetLineage, DatasetType
from app.models.script import Script
from app.config import UPLOAD_DIR


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test."""
    # Use in-memory SQLite with check_same_thread=False for multi-threaded access
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()

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
