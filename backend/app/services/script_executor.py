"""
Script execution service for running data transformation scripts.
"""
import re
import ast
import traceback
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Any
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from ..models.dataset import Dataset, DatasetType
from ..models.script import Script
from .file_parser import FileParser


@dataclass
class ExecutionResult:
    """Result of script execution."""
    success: bool
    output_df: Optional[pd.DataFrame] = None
    error: Optional[str] = None
    stats: Optional[dict] = None
    dataset: Optional[Dataset] = None


class ScriptExecutor:
    """Service for executing data transformation scripts."""

    def execute(
        self,
        code: str,
        input_file: Path,
    ) -> ExecutionResult:
        """
        Execute a transformation script on input data.

        Args:
            code: Python script code containing a transform(df) function
            input_file: Path to the input data file

        Returns:
            ExecutionResult with output DataFrame or error
        """
        try:
            # Load input data
            input_df = FileParser.read_file(input_file)
            input_rows = len(input_df)

            # Validate script has transform function
            if 'def transform' not in code:
                return ExecutionResult(
                    success=False,
                    error="Script must define a 'transform(df)' function"
                )

            # Execute script
            namespace = {'pd': pd, 'pandas': pd}
            exec(code, namespace)

            if 'transform' not in namespace:
                return ExecutionResult(
                    success=False,
                    error="Script must define a 'transform(df)' function"
                )

            transform_func = namespace['transform']
            output_df = transform_func(input_df)

            # Validate output
            if not isinstance(output_df, pd.DataFrame):
                return ExecutionResult(
                    success=False,
                    error=f"transform() must return a DataFrame, got {type(output_df).__name__}"
                )

            output_rows = len(output_df)

            return ExecutionResult(
                success=True,
                output_df=output_df,
                stats={
                    'input_rows': input_rows,
                    'output_rows': output_rows,
                    'rows_excluded': input_rows - output_rows,
                }
            )

        except SyntaxError as e:
            return ExecutionResult(
                success=False,
                error=f"SyntaxError: {str(e)}"
            )
        except KeyError as e:
            return ExecutionResult(
                success=False,
                error=f"KeyError: Column {str(e)} not found in dataset"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"{type(e).__name__}: {str(e)}"
            )

    def execute_and_save(
        self,
        script: Script,
        source_dataset: Dataset,
        output_name: str,
        output_dir: Path,
        db: Session,
    ) -> ExecutionResult:
        """
        Execute a script and save the result as a new derived dataset.

        Args:
            script: Script to execute
            source_dataset: Source dataset to transform
            output_name: Name for the output dataset
            output_dir: Directory to save output files
            db: Database session

        Returns:
            ExecutionResult with the created dataset
        """
        # Find the data file in source dataset
        if not source_dataset.files:
            return ExecutionResult(
                success=False,
                error="Source dataset has no files"
            )

        # Use the first file (assuming single file per dataset for MVP)
        source_file = source_dataset.files[0]
        input_path = Path(source_file.file_path)

        if not input_path.exists():
            return ExecutionResult(
                success=False,
                error=f"Source file not found: {input_path}"
            )

        # Execute script
        result = self.execute(script.code, input_path)

        if not result.success:
            return result

        # Create output directory
        import uuid
        dataset_id = str(uuid.uuid4())
        dataset_dir = output_dir / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)

        # Save output file
        output_file = dataset_dir / f"{dataset_id}.parquet"
        result.output_df.to_parquet(output_file, index=False)

        # Also save as CSV for compatibility
        csv_file = dataset_dir / f"{dataset_id}.csv"
        result.output_df.to_csv(csv_file, index=False)

        # Create derived dataset record
        derived_dataset = Dataset(
            id=dataset_id,
            name=output_name,
            type=DatasetType.DERIVED,
            source_dataset_id=source_dataset.id,
            script_id=script.id,
            patient_id_column=source_dataset.patient_id_column,
            row_count=len(result.output_df),
            column_count=len(result.output_df.columns),
            folder_path=str(dataset_dir),
            file_count=1,
            total_size=output_file.stat().st_size,
        )

        db.add(derived_dataset)

        # Update script usage
        script.usage_count += 1
        script.last_used_at = datetime.utcnow()

        db.commit()
        db.refresh(derived_dataset)

        result.dataset = derived_dataset
        return result

    def validate_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate script syntax without executing.

        Args:
            code: Python script code

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"

    def extract_referenced_columns(self, code: str) -> List[str]:
        """
        Extract column names referenced in the script.

        This is a simple regex-based extraction. It looks for patterns like:
        - df['column_name']
        - df["column_name"]

        Args:
            code: Python script code

        Returns:
            List of column names found
        """
        # Pattern to match df['col'] or df["col"]
        pattern = r"df\[[\'\"]([^\'\"]+)[\'\"]\]"
        matches = re.findall(pattern, code)
        return list(set(matches))
