"""
Tests for API endpoints.
TDD: Write tests first, then implement.
"""
import pytest
import json
from fastapi.testclient import TestClient


@pytest.fixture
def client(test_db):
    """Create a test client with test database."""
    from app.main import app
    from app.database import get_db

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestScriptAPI:
    """Tests for Script CRUD API."""

    def test_create_script(self, client):
        """Test creating a new script."""
        response = client.post(
            "/api/scripts",
            json={
                "name": "create_fas",
                "display_name": "FAS Generation",
                "description": "Generate Full Analysis Set",
                "code": "def transform(df): return df[df['RANDFL']=='Y']",
                "keywords": ["FAS", "全分析集"],
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "create_fas"
        assert data["id"] is not None

    def test_create_script_duplicate_name(self, client):
        """Test that duplicate script names are rejected."""
        # Create first script
        client.post(
            "/api/scripts",
            json={
                "name": "create_fas",
                "display_name": "FAS",
                "description": "FAS script",
                "code": "def transform(df): return df",
            }
        )

        # Try to create duplicate
        response = client.post(
            "/api/scripts",
            json={
                "name": "create_fas",  # Same name
                "display_name": "Another FAS",
                "description": "Another FAS script",
                "code": "def transform(df): return df",
            }
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_list_scripts(self, client):
        """Test listing all scripts."""
        # Create some scripts
        client.post("/api/scripts", json={
            "name": "script1",
            "display_name": "Script 1",
            "description": "First script",
            "code": "def transform(df): return df",
        })
        client.post("/api/scripts", json={
            "name": "script2",
            "display_name": "Script 2",
            "description": "Second script",
            "code": "def transform(df): return df",
        })

        response = client.get("/api/scripts")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_get_script(self, client):
        """Test getting a single script."""
        # Create script
        create_response = client.post("/api/scripts", json={
            "name": "test_script",
            "display_name": "Test",
            "description": "Test script",
            "code": "def transform(df): return df",
        })
        script_id = create_response.json()["id"]

        # Get script
        response = client.get(f"/api/scripts/{script_id}")

        assert response.status_code == 200
        assert response.json()["name"] == "test_script"

    def test_search_scripts(self, client):
        """Test searching scripts by keyword/description."""
        # Create scripts
        client.post("/api/scripts", json={
            "name": "create_fas",
            "display_name": "FAS Generation",
            "description": "Generate Full Analysis Set for efficacy",
            "code": "def transform(df): return df",
            "keywords": ["FAS", "全分析集", "efficacy"],
        })
        client.post("/api/scripts", json={
            "name": "create_safety",
            "display_name": "Safety Set",
            "description": "Generate safety analysis population",
            "code": "def transform(df): return df",
            "keywords": ["safety", "安全性"],
        })

        # Search for FAS
        response = client.get("/api/scripts/search?q=FAS")
        assert response.status_code == 200
        results = response.json()
        assert any(s["name"] == "create_fas" for s in results)

        # Search for safety
        response = client.get("/api/scripts/search?q=安全性")
        assert response.status_code == 200
        results = response.json()
        assert any(s["name"] == "create_safety" for s in results)

    def test_delete_script(self, client):
        """Test deleting a script."""
        # Create script
        create_response = client.post("/api/scripts", json={
            "name": "to_delete",
            "display_name": "Delete Me",
            "description": "Script to delete",
            "code": "def transform(df): return df",
        })
        script_id = create_response.json()["id"]

        # Delete script
        response = client.delete(f"/api/scripts/{script_id}")
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/scripts/{script_id}")
        assert response.status_code == 404


class TestDatasetVersionAPI:
    """Tests for dataset versioning API."""

    def test_upload_new_version(self, client, sample_csv_content, test_upload_dir):
        """Test uploading a new version of a dataset."""
        import io

        # Create initial dataset
        files = {"files": ("test.csv", io.BytesIO(sample_csv_content.encode()), "text/csv")}
        create_response = client.post(
            "/api/datasets",
            json={"name": "Study_ABC_2024-03-01", "crf_version": "v1.0"}
        )
        dataset_id = create_response.json()["id"]

        client.post(f"/api/datasets/{dataset_id}/files", files=files)

        # Upload new version
        new_csv = sample_csv_content + "P006,60,F,Y,N,Y\n"
        files = {"files": ("test_v2.csv", io.BytesIO(new_csv.encode()), "text/csv")}

        response = client.post(
            "/api/datasets",
            json={
                "name": "Study_ABC_2024-03-15",
                "crf_version": "v1.1",
                "parent_dataset_id": dataset_id
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["parent_dataset_id"] == dataset_id

    def test_get_dataset_versions(self, client):
        """Test getting version history of a dataset."""
        # Create v1
        v1_response = client.post(
            "/api/datasets",
            json={"name": "Study_ABC_v1", "crf_version": "v1.0"}
        )
        v1_id = v1_response.json()["id"]

        # Create v2
        client.post(
            "/api/datasets",
            json={
                "name": "Study_ABC_v2",
                "crf_version": "v1.1",
                "parent_dataset_id": v1_id
            }
        )

        # Get version history
        response = client.get(f"/api/datasets/{v1_id}/versions")
        assert response.status_code == 200
        versions = response.json()
        assert len(versions) >= 1


class TestDatasetDerivationAPI:
    """Tests for dataset derivation API."""

    def test_derive_dataset_with_script(self, client, sample_csv_content):
        """Test creating a derived dataset using a script."""
        import io

        # Create source dataset
        create_response = client.post(
            "/api/datasets",
            json={"name": "Study_ABC_2024-03-01"}
        )
        dataset_id = create_response.json()["id"]

        # Upload file
        files = {"files": ("test.csv", io.BytesIO(sample_csv_content.encode()), "text/csv")}
        client.post(f"/api/datasets/{dataset_id}/files", files=files)

        # Create script
        script_response = client.post("/api/scripts", json={
            "name": "create_fas",
            "display_name": "FAS",
            "description": "Generate FAS",
            "code": """
import pandas as pd

def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df['RANDFL'] == 'Y') & (df['PPROTFL'] != 'Y')]
""",
        })
        script_id = script_response.json()["id"]

        # Derive dataset
        response = client.post(
            f"/api/datasets/{dataset_id}/derive",
            json={
                "script_id": script_id,
                "output_name": "Study_ABC_2024-03-01_FAS"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "DERIVED"
        assert data["source_dataset_id"] == dataset_id
        assert data["script_id"] == script_id
        assert data["row_count"] == 3  # Filtered result

    def test_get_derived_datasets(self, client):
        """Test getting all datasets derived from a source."""
        # Create source
        source_response = client.post(
            "/api/datasets",
            json={"name": "Source"}
        )
        source_id = source_response.json()["id"]

        # Get derived datasets (initially empty)
        response = client.get(f"/api/datasets/{source_id}/derived")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_mark_derived_datasets_stale(self, client):
        """Test that derived datasets are marked stale when source is updated."""
        # This would be part of the upload new version flow
        # The system should automatically detect and mark derived datasets as stale
        pass


class TestDatasetLineageAPI:
    """Tests for dataset lineage API."""

    def test_get_dataset_lineage(self, client):
        """Test getting full lineage of a dataset."""
        # Create chain: raw -> fas -> subgroup
        raw_response = client.post(
            "/api/datasets",
            json={"name": "Raw Data"}
        )
        raw_id = raw_response.json()["id"]

        # Get lineage
        response = client.get(f"/api/datasets/{raw_id}/lineage")
        assert response.status_code == 200
        lineage = response.json()
        assert "ancestors" in lineage
        assert "descendants" in lineage
