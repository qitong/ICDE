"""
Tests for Script execution service.
TDD: Write tests first, then implement.
"""
import pytest
import pandas as pd
import json


class TestScriptExecutor:
    """Tests for script execution service."""

    def test_execute_simple_filter_script(self, sample_csv_file):
        """Test executing a simple filter script."""
        from app.services.script_executor import ScriptExecutor

        code = '''
import pandas as pd

def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['RANDFL'] == 'Y']
'''
        executor = ScriptExecutor()
        result = executor.execute(code, sample_csv_file)

        assert result.success is True
        assert result.output_df is not None
        assert len(result.output_df) == 4  # 4 patients with RANDFL=Y
        assert result.error is None

    def test_execute_fas_script(self, sample_csv_file):
        """Test executing FAS generation script."""
        from app.services.script_executor import ScriptExecutor

        code = '''
import pandas as pd

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Generate FAS: randomized, no major protocol deviation."""
    fas = df[
        (df['RANDFL'] == 'Y') &
        (df['PPROTFL'] != 'Y')
    ].copy()
    return fas
'''
        executor = ScriptExecutor()
        result = executor.execute(code, sample_csv_file)

        assert result.success is True
        assert len(result.output_df) == 3  # P001, P002, P004 (P003 has PPROTFL=Y, P005 has RANDFL=N)

    def test_execute_script_with_stats(self, sample_csv_file):
        """Test that execution returns statistics."""
        from app.services.script_executor import ScriptExecutor

        code = '''
import pandas as pd

def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['SEX'] == 'M']
'''
        executor = ScriptExecutor()
        result = executor.execute(code, sample_csv_file)

        assert result.success is True
        assert result.stats is not None
        assert result.stats['input_rows'] == 5
        assert result.stats['output_rows'] == 3  # 3 males
        assert result.stats['rows_excluded'] == 2

    def test_execute_script_missing_column(self, sample_csv_file):
        """Test error handling when script references missing column."""
        from app.services.script_executor import ScriptExecutor

        code = '''
import pandas as pd

def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['NONEXISTENT_COL'] == 'Y']
'''
        executor = ScriptExecutor()
        result = executor.execute(code, sample_csv_file)

        assert result.success is False
        assert result.error is not None
        assert "NONEXISTENT_COL" in result.error or "KeyError" in result.error

    def test_execute_script_syntax_error(self, sample_csv_file):
        """Test error handling for script with syntax error."""
        from app.services.script_executor import ScriptExecutor

        code = '''
import pandas as pd

def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['RANDFL' == 'Y'  # Missing bracket
'''
        executor = ScriptExecutor()
        result = executor.execute(code, sample_csv_file)

        assert result.success is False
        assert result.error is not None
        assert "SyntaxError" in result.error or "syntax" in result.error.lower()

    def test_execute_script_no_transform_function(self, sample_csv_file):
        """Test error when script doesn't define transform function."""
        from app.services.script_executor import ScriptExecutor

        code = '''
import pandas as pd

def process(df):  # Wrong function name
    return df
'''
        executor = ScriptExecutor()
        result = executor.execute(code, sample_csv_file)

        assert result.success is False
        assert "transform" in result.error.lower()

    def test_execute_script_returns_non_dataframe(self, sample_csv_file):
        """Test error when script returns non-DataFrame."""
        from app.services.script_executor import ScriptExecutor

        code = '''
import pandas as pd

def transform(df: pd.DataFrame):
    return "not a dataframe"
'''
        executor = ScriptExecutor()
        result = executor.execute(code, sample_csv_file)

        assert result.success is False
        assert "DataFrame" in result.error

    def test_validate_script_syntax(self):
        """Test script syntax validation without execution."""
        from app.services.script_executor import ScriptExecutor

        executor = ScriptExecutor()

        # Valid script
        valid_code = '''
def transform(df):
    return df
'''
        is_valid, error = executor.validate_syntax(valid_code)
        assert is_valid is True
        assert error is None

        # Invalid script
        invalid_code = '''
def transform(df)  # Missing colon
    return df
'''
        is_valid, error = executor.validate_syntax(invalid_code)
        assert is_valid is False
        assert error is not None

    def test_extract_required_columns(self):
        """Test extracting required columns from script code."""
        from app.services.script_executor import ScriptExecutor

        code = '''
import pandas as pd

def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df[
        (df['RANDFL'] == 'Y') &
        (df['PPROTFL'] != 'Y') &
        (df['AGE'] >= 18)
    ]
'''
        executor = ScriptExecutor()
        columns = executor.extract_referenced_columns(code)

        assert 'RANDFL' in columns
        assert 'PPROTFL' in columns
        assert 'AGE' in columns


class TestScriptExecutorWithDatabase:
    """Tests for script execution with database integration."""

    def test_execute_and_save_result(self, test_db, sample_csv_file, test_upload_dir):
        """Test executing a script and saving the result as a new dataset."""
        from app.models.dataset import Dataset, DatasetFile, DatasetType
        from app.models.script import Script
        from app.services.script_executor import ScriptExecutor

        # Create source dataset
        source = Dataset(
            name="Study_ABC_2024-03-01",
            type=DatasetType.RAW,
            folder_path=str(sample_csv_file.parent),
            patient_id_column="SUBJID",
            row_count=5,
        )
        test_db.add(source)
        test_db.commit()

        # Add file to dataset
        source_file = DatasetFile(
            dataset_id=source.id,
            file_name=sample_csv_file.name,
            original_name=sample_csv_file.name,
            file_path=str(sample_csv_file),
            file_type="csv",
            file_size=sample_csv_file.stat().st_size,
            row_count=5,
            column_count=4,
        )
        test_db.add(source_file)
        test_db.commit()

        # Create script
        script = Script(
            name="create_fas",
            display_name="FAS Script",
            description="Generate FAS",
            code='''
import pandas as pd

def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df['RANDFL'] == 'Y') & (df['PPROTFL'] != 'Y')]
''',
        )
        test_db.add(script)
        test_db.commit()

        # Execute
        executor = ScriptExecutor()
        result = executor.execute_and_save(
            script=script,
            source_dataset=source,
            output_name="Study_ABC_2024-03-01_FAS",
            output_dir=test_upload_dir,
            db=test_db,
        )

        assert result.success is True
        assert result.dataset is not None
        assert result.dataset.type == DatasetType.DERIVED
        assert result.dataset.source_dataset_id == source.id
        assert result.dataset.script_id == script.id
        assert result.dataset.row_count == 3

        # Check script usage was updated
        test_db.refresh(script)
        assert script.usage_count == 1


class TestDiffCalculation:
    """Tests for calculating differences between dataset versions."""

    def test_calculate_patient_diff(self, test_upload_dir):
        """Test calculating patient-level differences between versions."""
        from app.services.diff_calculator import DiffCalculator

        # Create v1 data
        v1_data = pd.DataFrame({
            'SUBJID': ['P001', 'P002', 'P003'],
            'AGE': [58, 45, 62],
            'STATUS': ['Active', 'Active', 'Completed']
        })
        v1_path = test_upload_dir / "v1.csv"
        v1_data.to_csv(v1_path, index=False)

        # Create v2 data
        v2_data = pd.DataFrame({
            'SUBJID': ['P001', 'P002', 'P004'],  # P003 removed, P004 added
            'AGE': [58, 46, 51],  # P002 age changed
            'STATUS': ['Active', 'Active', 'Active']
        })
        v2_path = test_upload_dir / "v2.csv"
        v2_data.to_csv(v2_path, index=False)

        calculator = DiffCalculator(patient_id_column='SUBJID')
        diff = calculator.calculate(v1_path, v2_path)

        assert diff['patients_added'] == ['P004']
        assert diff['patients_removed'] == ['P003']
        assert 'P002' in diff['patients_modified']
        assert diff['total_rows_v1'] == 3
        assert diff['total_rows_v2'] == 3

    def test_calculate_column_diff(self, test_upload_dir):
        """Test calculating column-level differences."""
        from app.services.diff_calculator import DiffCalculator

        v1_data = pd.DataFrame({
            'SUBJID': ['P001'],
            'AGE': [58],
            'OLD_COL': ['value']
        })
        v1_path = test_upload_dir / "v1.csv"
        v1_data.to_csv(v1_path, index=False)

        v2_data = pd.DataFrame({
            'SUBJID': ['P001'],
            'AGE': [58],
            'NEW_COL': ['value']  # OLD_COL removed, NEW_COL added
        })
        v2_path = test_upload_dir / "v2.csv"
        v2_data.to_csv(v2_path, index=False)

        calculator = DiffCalculator(patient_id_column='SUBJID')
        diff = calculator.calculate(v1_path, v2_path)

        assert 'NEW_COL' in diff['columns_added']
        assert 'OLD_COL' in diff['columns_removed']
