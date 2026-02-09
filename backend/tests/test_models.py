"""
Tests for Dataset and Script models.
TDD: Write tests first, then implement.
"""
import pytest
import json
from datetime import datetime


class TestDatasetModel:
    """Tests for extended Dataset model with versioning and lineage."""

    def test_create_raw_dataset(self, test_db):
        """Test creating a RAW dataset with basic fields."""
        from app.models.dataset import Dataset, DatasetType

        dataset = Dataset(
            name="Study_ABC_2024-03-01",
            description="Initial data export",
            type=DatasetType.RAW,
            crf_version="v1.0",
            crf_name="Study ABC Protocol",
            patient_id_column="SUBJID",
            row_count=150,
            column_count=45,
        )
        test_db.add(dataset)
        test_db.commit()

        assert dataset.id is not None
        assert dataset.type == DatasetType.RAW
        assert dataset.crf_version == "v1.0"
        assert dataset.parent_dataset_id is None
        assert dataset.source_dataset_id is None
        assert dataset.script_id is None

    def test_create_version_dataset(self, test_db):
        """Test creating a new version of a dataset."""
        from app.models.dataset import Dataset, DatasetType

        # Create parent (v1)
        parent = Dataset(
            name="Study_ABC_2024-03-01",
            type=DatasetType.RAW,
            crf_version="v1.0",
            patient_id_column="SUBJID",
            row_count=150,
            column_count=45,
        )
        test_db.add(parent)
        test_db.commit()

        # Create child (v2) - new version
        child = Dataset(
            name="Study_ABC_2024-03-15",
            type=DatasetType.RAW,
            crf_version="v1.1",
            patient_id_column="SUBJID",
            row_count=162,
            column_count=46,
            parent_dataset_id=parent.id,
            diff_summary=json.dumps({
                "patients_added": ["P151", "P152"],
                "patients_removed": [],
                "columns_added": ["NEW_COL"],
                "total_cells_changed": 45
            })
        )
        test_db.add(child)
        test_db.commit()

        assert child.parent_dataset_id == parent.id
        assert child.parent_dataset is not None
        assert child.parent_dataset.id == parent.id

        # Check diff summary
        diff = json.loads(child.diff_summary)
        assert "P151" in diff["patients_added"]
        assert diff["total_cells_changed"] == 45

    def test_create_derived_dataset(self, test_db):
        """Test creating a derived dataset from a source with a script."""
        from app.models.dataset import Dataset, DatasetType
        from app.models.script import Script

        # Create source dataset
        source = Dataset(
            name="Study_ABC_2024-03-01",
            type=DatasetType.RAW,
            patient_id_column="SUBJID",
            row_count=150,
            column_count=45,
        )
        test_db.add(source)
        test_db.commit()

        # Create script
        script = Script(
            name="create_fas",
            display_name="FAS Analysis Set",
            description="Generate Full Analysis Set",
            code="def transform(df): return df[df['RANDFL']=='Y']",
            language="python",
        )
        test_db.add(script)
        test_db.commit()

        # Create derived dataset
        derived = Dataset(
            name="Study_ABC_2024-03-01_FAS",
            type=DatasetType.DERIVED,
            patient_id_column="SUBJID",
            row_count=142,
            column_count=45,
            source_dataset_id=source.id,
            script_id=script.id,
        )
        test_db.add(derived)
        test_db.commit()

        assert derived.type == DatasetType.DERIVED
        assert derived.source_dataset_id == source.id
        assert derived.script_id == script.id
        assert derived.source_dataset.id == source.id
        assert derived.script.name == "create_fas"

    def test_dataset_is_stale(self, test_db):
        """Test marking a derived dataset as stale when source updates."""
        from app.models.dataset import Dataset, DatasetType

        source = Dataset(
            name="Study_ABC_2024-03-01",
            type=DatasetType.RAW,
            row_count=150,
        )
        test_db.add(source)
        test_db.commit()

        derived = Dataset(
            name="Study_ABC_2024-03-01_FAS",
            type=DatasetType.DERIVED,
            source_dataset_id=source.id,
            row_count=142,
            is_stale=False,
        )
        test_db.add(derived)
        test_db.commit()

        # Mark as stale
        derived.is_stale = True
        derived.stale_reason = "Source dataset updated: Study_ABC_2024-03-15"
        test_db.commit()

        assert derived.is_stale is True
        assert "Source dataset updated" in derived.stale_reason


class TestScriptModel:
    """Tests for Script model."""

    def test_create_script(self, test_db, sample_script_code):
        """Test creating a script with all fields."""
        from app.models.script import Script

        script = Script(
            name="create_fas",
            display_name="FAS Generation Script",
            description="Generate Full Analysis Set. Include randomized patients, exclude major protocol deviations.",
            keywords=json.dumps(["FAS", "全分析集", "full analysis set"]),
            language="python",
            code=sample_script_code,
            input_requirements=json.dumps({
                "required_columns": ["RANDFL", "PPROTFL"],
                "patient_id_column": "SUBJID"
            }),
            output_description="DataFrame with FAS patients only",
            created_by="user",
        )
        test_db.add(script)
        test_db.commit()

        assert script.id is not None
        assert script.name == "create_fas"
        assert script.usage_count == 0

        keywords = json.loads(script.keywords)
        assert "FAS" in keywords

    def test_script_created_by_llm(self, test_db):
        """Test creating a script generated by LLM."""
        from app.models.script import Script

        script = Script(
            name="filter_alk_positive",
            display_name="ALK+ Patient Filter",
            description="Filter patients with ALK positive mutation status",
            code="def transform(df): return df[df['ALK_STATUS']=='Positive']",
            created_by="llm",
            created_from_prompt="帮我筛选出ALK阳性的患者",
        )
        test_db.add(script)
        test_db.commit()

        assert script.created_by == "llm"
        assert script.created_from_prompt is not None

    def test_script_versioning(self, test_db):
        """Test script versioning with parent reference."""
        from app.models.script import Script

        # Original script
        v1 = Script(
            name="create_fas",
            display_name="FAS Script v1",
            description="Original FAS script",
            code="def transform(df): return df",
            version=1,
        )
        test_db.add(v1)
        test_db.commit()

        # Updated script
        v2 = Script(
            name="create_fas_v2",
            display_name="FAS Script v2",
            description="Updated FAS script with additional filter",
            code="def transform(df): return df[df['RANDFL']=='Y']",
            version=2,
            parent_script_id=v1.id,
        )
        test_db.add(v2)
        test_db.commit()

        assert v2.parent_script_id == v1.id
        assert v2.version == 2

    def test_script_usage_tracking(self, test_db):
        """Test incrementing script usage count."""
        from app.models.script import Script

        script = Script(
            name="create_fas",
            display_name="FAS Script",
            description="FAS generation",
            code="def transform(df): return df",
        )
        test_db.add(script)
        test_db.commit()

        assert script.usage_count == 0
        assert script.last_used_at is None

        # Simulate usage
        script.usage_count += 1
        script.last_used_at = datetime.utcnow()
        test_db.commit()

        assert script.usage_count == 1
        assert script.last_used_at is not None


class TestDatasetLineage:
    """Tests for dataset lineage tracking."""

    def test_create_lineage_record(self, test_db):
        """Test creating a lineage record between datasets."""
        from app.models.dataset import Dataset, DatasetType, DatasetLineage

        parent = Dataset(name="Parent", type=DatasetType.RAW, row_count=100)
        child = Dataset(name="Child", type=DatasetType.DERIVED, row_count=80)
        test_db.add_all([parent, child])
        test_db.commit()

        lineage = DatasetLineage(
            parent_id=parent.id,
            child_id=child.id,
            relationship="DERIVED_FROM",
        )
        test_db.add(lineage)
        test_db.commit()

        assert lineage.relationship == "DERIVED_FROM"

    def test_get_dataset_children(self, test_db):
        """Test getting all derived datasets from a source."""
        from app.models.dataset import Dataset, DatasetType, DatasetLineage

        source = Dataset(name="Source", type=DatasetType.RAW, row_count=150)
        fas = Dataset(name="FAS", type=DatasetType.DERIVED, row_count=142)
        pps = Dataset(name="PPS", type=DatasetType.DERIVED, row_count=128)
        test_db.add_all([source, fas, pps])
        test_db.commit()

        # Create lineage records
        test_db.add_all([
            DatasetLineage(parent_id=source.id, child_id=fas.id, relationship="DERIVED_FROM"),
            DatasetLineage(parent_id=source.id, child_id=pps.id, relationship="DERIVED_FROM"),
        ])
        test_db.commit()

        # Query children
        children = test_db.query(DatasetLineage).filter(
            DatasetLineage.parent_id == source.id
        ).all()

        assert len(children) == 2

    def test_get_dataset_ancestors(self, test_db):
        """Test tracing back dataset lineage."""
        from app.models.dataset import Dataset, DatasetType

        # Create chain: raw -> fas -> subgroup
        raw = Dataset(name="Raw", type=DatasetType.RAW, row_count=150)
        test_db.add(raw)
        test_db.commit()

        fas = Dataset(
            name="FAS",
            type=DatasetType.DERIVED,
            source_dataset_id=raw.id,
            row_count=142
        )
        test_db.add(fas)
        test_db.commit()

        subgroup = Dataset(
            name="ALK+ Subgroup",
            type=DatasetType.DERIVED,
            source_dataset_id=fas.id,
            row_count=45
        )
        test_db.add(subgroup)
        test_db.commit()

        # Trace back
        assert subgroup.source_dataset_id == fas.id
        assert fas.source_dataset_id == raw.id
        assert raw.source_dataset_id is None
