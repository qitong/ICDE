#!/usr/bin/env python3
"""Generate test datasets with lineage relationships for testing the lineage visualization."""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid
import pandas as pd
from datetime import datetime

from app.database import engine, get_db
from app.models.dataset import Dataset, DatasetFile, DatasetType
from app.models.script import Script
from app.models.base import Base
from app.config import UPLOAD_DIR


def generate_test_data():
    """Generate test datasets with various lineage relationships."""

    # Create tables if not exist
    Base.metadata.create_all(bind=engine)

    # Get database session
    db = next(get_db())

    try:
        # ============================================================
        # Dataset 1: RAW dataset - Study ABC v1.0 (Root)
        # ============================================================
        ds1_id = str(uuid.uuid4())
        ds1_folder = UPLOAD_DIR / ds1_id
        ds1_folder.mkdir(parents=True, exist_ok=True)

        # Create sample CSV for dataset 1
        df1 = pd.DataFrame({
            'SUBJID': ['001', '002', '003', '004', '005'],
            'AGE': [45, 52, 38, 61, 55],
            'SEX': ['M', 'F', 'M', 'F', 'M'],
            'RACE': ['WHITE', 'WHITE', 'ASIAN', 'BLACK', 'WHITE'],
            'TRT': ['A', 'B', 'A', 'B', 'A'],
            'AVAL': [12.5, 14.2, 11.8, 15.1, 13.0]
        })

        csv_path1 = ds1_folder / "adsl_v1.csv"
        df1.to_csv(csv_path1, index=False)

        dataset1 = Dataset(
            id=ds1_id,
            name="Study_ABC_v1.0",
            description="Initial CRF data for Study ABC - Version 1.0",
            type=DatasetType.RAW,
            folder_path=str(ds1_folder),
            file_count=1,
            total_size=csv_path1.stat().st_size,
            crf_version="1.0",
            patient_id_column="SUBJID",
            row_count=5,
            column_count=6,
            is_stale=False,
        )
        db.add(dataset1)

        # Add file record
        file1 = DatasetFile(
            id=str(uuid.uuid4()),
            dataset_id=ds1_id,
            file_name="adsl_v1.csv",
            original_name="ADSL_v1.0.csv",
            file_path=str(csv_path1),
            file_type="csv",
            file_size=csv_path1.stat().st_size,
            row_count=5,
            column_count=6,
            parse_status="parsed",
        )
        db.add(file1)

        print(f"✓ Created Dataset 1: {dataset1.name} (RAW, Root)")

        # ============================================================
        # Dataset 2: RAW dataset - Study ABC v1.1 (Version child of DS1)
        # ============================================================
        ds2_id = str(uuid.uuid4())
        ds2_folder = UPLOAD_DIR / ds2_id
        ds2_folder.mkdir(parents=True, exist_ok=True)

        # Create sample CSV for dataset 2 (updated version with more patients)
        df2 = pd.DataFrame({
            'SUBJID': ['001', '002', '003', '004', '005', '006', '007'],
            'AGE': [45, 52, 38, 61, 55, 48, 42],
            'SEX': ['M', 'F', 'M', 'F', 'M', 'F', 'M'],
            'RACE': ['WHITE', 'WHITE', 'ASIAN', 'BLACK', 'WHITE', 'ASIAN', 'WHITE'],
            'TRT': ['A', 'B', 'A', 'B', 'A', 'B', 'A'],
            'AVAL': [12.5, 14.2, 11.8, 15.1, 13.0, 12.8, 11.5],
            'VISITNUM': [1, 1, 1, 1, 1, 1, 1]  # New column in v1.1
        })

        csv_path2 = ds2_folder / "adsl_v1.1.csv"
        df2.to_csv(csv_path2, index=False)

        dataset2 = Dataset(
            id=ds2_id,
            name="Study_ABC_v1.1",
            description="Updated CRF data for Study ABC - Version 1.1 (added 2 new patients)",
            type=DatasetType.RAW,
            folder_path=str(ds2_folder),
            file_count=1,
            total_size=csv_path2.stat().st_size,
            crf_version="1.1",
            patient_id_column="SUBJID",
            row_count=7,
            column_count=7,
            parent_dataset_id=ds1_id,  # Version parent
            is_stale=False,
        )
        db.add(dataset2)

        file2 = DatasetFile(
            id=str(uuid.uuid4()),
            dataset_id=ds2_id,
            file_name="adsl_v1.1.csv",
            original_name="ADSL_v1.1.csv",
            file_path=str(csv_path2),
            file_type="csv",
            file_size=csv_path2.stat().st_size,
            row_count=7,
            column_count=7,
            parse_status="parsed",
        )
        db.add(file2)

        print(f"✓ Created Dataset 2: {dataset2.name} (RAW, Version child of DS1)")

        # ============================================================
        # Script: FAS Population Filter
        # ============================================================
        script_id = str(uuid.uuid4())
        script = Script(
            id=script_id,
            name="fas_population",
            display_name="FAS Population Filter",
            description="Filter for Full Analysis Set population - excludes screen failures",
            code="""
import pandas as pd

def transform(df):
    # FAS Population: All randomized subjects
    # Exclude those with TRT = None or missing
    fas = df[df['TRT'].notna()].copy()
    fas['FASFL'] = 'Y'
    return fas
""",
            language="python",
            input_requirements="DataFrame with TRT column",
            output_description="FAS population with FASFL flag",
            created_by="user",
            usage_count=0,
            version=1,
        )
        db.add(script)

        print(f"✓ Created Script: {script.display_name}")

        # ============================================================
        # Dataset 3: DERIVED dataset - FAS Population (Derived from DS2)
        # ============================================================
        ds3_id = str(uuid.uuid4())
        ds3_folder = UPLOAD_DIR / ds3_id
        ds3_folder.mkdir(parents=True, exist_ok=True)

        # Create FAS dataset (derived from v1.1)
        df3 = df2.copy()
        df3['FASFL'] = 'Y'

        csv_path3 = ds3_folder / "fas_population.csv"
        df3.to_csv(csv_path3, index=False)

        dataset3 = Dataset(
            id=ds3_id,
            name="Study_ABC_FAS",
            description="Full Analysis Set population derived from Study ABC v1.1",
            type=DatasetType.DERIVED,
            folder_path=str(ds3_folder),
            file_count=1,
            total_size=csv_path3.stat().st_size,
            crf_version="1.1",
            patient_id_column="SUBJID",
            row_count=7,
            column_count=8,
            source_dataset_id=ds2_id,  # Derivation source
            script_id=script_id,
            is_stale=False,
        )
        db.add(dataset3)

        file3 = DatasetFile(
            id=str(uuid.uuid4()),
            dataset_id=ds3_id,
            file_name="fas_population.csv",
            original_name="FAS_Population.csv",
            file_path=str(csv_path3),
            file_type="csv",
            file_size=csv_path3.stat().st_size,
            row_count=7,
            column_count=8,
            parse_status="parsed",
        )
        db.add(file3)

        print(f"✓ Created Dataset 3: {dataset3.name} (DERIVED from DS2)")

        # ============================================================
        # Script: PPS Population Filter
        # ============================================================
        script2_id = str(uuid.uuid4())
        script2 = Script(
            id=script2_id,
            name="pps_population",
            display_name="PPS Population Filter",
            description="Filter for Per Protocol Set population - excludes protocol deviations",
            code="""
import pandas as pd

def transform(df):
    # PPS Population: Exclude protocol deviations
    # For demo, exclude subjects with AGE < 40
    pps = df[df['AGE'] >= 40].copy()
    pps['PPSFL'] = 'Y'
    return pps
""",
            language="python",
            input_requirements="DataFrame with AGE column",
            output_description="PPS population with PPSFL flag",
            created_by="user",
            usage_count=0,
            version=1,
        )
        db.add(script2)

        print(f"✓ Created Script: {script2.display_name}")

        # ============================================================
        # Dataset 4: DERIVED dataset - PPS Population (Also derived from DS2)
        # ============================================================
        ds4_id = str(uuid.uuid4())
        ds4_folder = UPLOAD_DIR / ds4_id
        ds4_folder.mkdir(parents=True, exist_ok=True)

        # Create PPS dataset (derived from v1.1, different from FAS)
        df4 = df2[df2['AGE'] >= 40].copy()
        df4['PPSFL'] = 'Y'

        csv_path4 = ds4_folder / "pps_population.csv"
        df4.to_csv(csv_path4, index=False)

        dataset4 = Dataset(
            id=ds4_id,
            name="Study_ABC_PPS",
            description="Per Protocol Set population derived from Study ABC v1.1 (excludes age < 40)",
            type=DatasetType.DERIVED,
            folder_path=str(ds4_folder),
            file_count=1,
            total_size=csv_path4.stat().st_size,
            crf_version="1.1",
            patient_id_column="SUBJID",
            row_count=len(df4),
            column_count=8,
            source_dataset_id=ds2_id,  # Same source as FAS
            script_id=script2_id,
            is_stale=False,
        )
        db.add(dataset4)

        file4 = DatasetFile(
            id=str(uuid.uuid4()),
            dataset_id=ds4_id,
            file_name="pps_population.csv",
            original_name="PPS_Population.csv",
            file_path=str(csv_path4),
            file_type="csv",
            file_size=csv_path4.stat().st_size,
            row_count=len(df4),
            column_count=8,
            parse_status="parsed",
        )
        db.add(file4)

        print(f"✓ Created Dataset 4: {dataset4.name} (DERIVED from DS2)")

        # ============================================================
        # Dataset 5: RAW dataset - Study ABC v1.2 (Stale version child of DS2)
        # ============================================================
        ds5_id = str(uuid.uuid4())
        ds5_folder = UPLOAD_DIR / ds5_id
        ds5_folder.mkdir(parents=True, exist_ok=True)

        # Create v1.2 with more data
        df5 = pd.DataFrame({
            'SUBJID': ['001', '002', '003', '004', '005', '006', '007', '008', '009', '010'],
            'AGE': [45, 52, 38, 61, 55, 48, 42, 59, 47, 53],
            'SEX': ['M', 'F', 'M', 'F', 'M', 'F', 'M', 'F', 'M', 'F'],
            'RACE': ['WHITE', 'WHITE', 'ASIAN', 'BLACK', 'WHITE', 'ASIAN', 'WHITE', 'BLACK', 'WHITE', 'ASIAN'],
            'TRT': ['A', 'B', 'A', 'B', 'A', 'B', 'A', 'B', 'A', 'B'],
            'AVAL': [12.5, 14.2, 11.8, 15.1, 13.0, 12.8, 11.5, 14.8, 13.2, 12.1],
            'VISITNUM': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            'SAFFL': ['Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y']  # New safety flag
        })

        csv_path5 = ds5_folder / "adsl_v1.2.csv"
        df5.to_csv(csv_path5, index=False)

        dataset5 = Dataset(
            id=ds5_id,
            name="Study_ABC_v1.2",
            description="Latest CRF data for Study ABC - Version 1.2 (10 patients, added SAFFL)",
            type=DatasetType.RAW,
            folder_path=str(ds5_folder),
            file_count=1,
            total_size=csv_path5.stat().st_size,
            crf_version="1.2",
            patient_id_column="SUBJID",
            row_count=10,
            column_count=8,
            parent_dataset_id=ds2_id,  # Version parent (v1.1)
            is_stale=False,
        )
        db.add(dataset5)

        file5 = DatasetFile(
            id=str(uuid.uuid4()),
            dataset_id=ds5_id,
            file_name="adsl_v1.2.csv",
            original_name="ADSL_v1.2.csv",
            file_path=str(csv_path5),
            file_type="csv",
            file_size=csv_path5.stat().st_size,
            row_count=10,
            column_count=8,
            parse_status="parsed",
        )
        db.add(file5)

        print(f"✓ Created Dataset 5: {dataset5.name} (RAW, Version child of DS2)")

        # Mark FAS and PPS as stale since source has newer version
        dataset3.is_stale = True
        dataset3.stale_reason = "Source dataset has newer version (v1.2)"
        dataset4.is_stale = True
        dataset4.stale_reason = "Source dataset has newer version (v1.2)"

        print(f"✓ Marked FAS and PPS as stale (source has v1.2)")

        db.commit()

        print("\n" + "="*60)
        print("Test data generation complete!")
        print("="*60)
        print("\nDataset Lineage Structure:")
        print("""
        Study_ABC_v1.0 (RAW, Root)
              │
              ▼ [version]
        Study_ABC_v1.1 (RAW)
              │
        ┌─────┼─────────────┐
        │     │             │
        ▼     ▼             ▼
    [derived] [derived]  [version]
        │     │             │
  Study_ABC_FAS  Study_ABC_PPS  Study_ABC_v1.2
   (DERIVED)     (DERIVED)        (RAW)
   [STALE]       [STALE]
        """)
        print("\nYou can now test the lineage visualization in the frontend!")

    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    generate_test_data()
