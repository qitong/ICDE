import json
from pathlib import Path
from typing import Tuple, List, Any, Optional
import pandas as pd
import numpy as np

from ..config import PREVIEW_ROWS, MAX_SAMPLE_VALUES
from ..schemas.dataset import ColumnInfo


class FileParser:
    """Service for parsing Excel and CSV files."""

    @staticmethod
    def read_file(file_path: Path) -> pd.DataFrame:
        """Read a file into a pandas DataFrame."""
        suffix = file_path.suffix.lower()

        if suffix == ".csv":
            return pd.read_csv(file_path)
        elif suffix == ".xlsx":
            return pd.read_excel(file_path, engine="openpyxl")
        elif suffix == ".xls":
            return pd.read_excel(file_path, engine="xlrd")
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    @staticmethod
    def infer_data_type(series: pd.Series) -> str:
        """Infer the data type of a pandas Series."""
        # Drop NA values for type inference
        non_null = series.dropna()

        if len(non_null) == 0:
            return "text"

        dtype = series.dtype

        # Check for numeric types
        if pd.api.types.is_numeric_dtype(dtype):
            return "numeric"

        # Check for datetime
        if pd.api.types.is_datetime64_any_dtype(dtype):
            return "date"

        # Try to parse as datetime
        if dtype == object:
            try:
                pd.to_datetime(non_null.head(100), errors="raise")
                return "date"
            except (ValueError, TypeError):
                pass

        # Check if categorical (few unique values relative to total)
        unique_ratio = len(non_null.unique()) / len(non_null)
        if unique_ratio < 0.1 and len(non_null.unique()) < 50:
            return "categorical"

        return "text"

    @staticmethod
    def get_sample_values(series: pd.Series, max_values: int = MAX_SAMPLE_VALUES) -> List[str]:
        """Get sample values from a Series."""
        unique_values = series.dropna().unique()[:max_values]
        return [str(v) for v in unique_values]

    @classmethod
    def parse_file(cls, file_path: Path) -> Tuple[int, int, List[ColumnInfo], str]:
        """
        Parse a file and extract metadata.

        Returns:
            Tuple of (row_count, column_count, column_info_list, column_info_json)
        """
        df = cls.read_file(file_path)

        row_count = len(df)
        column_count = len(df.columns)

        columns: List[ColumnInfo] = []
        for col_name in df.columns:
            series = df[col_name]
            col_info = ColumnInfo(
                name=str(col_name),
                data_type=cls.infer_data_type(series),
                non_null_count=int(series.notna().sum()),
                unique_count=int(series.nunique()),
                sample_values=cls.get_sample_values(series),
            )
            columns.append(col_info)

        column_info_json = json.dumps([col.model_dump() for col in columns])

        return row_count, column_count, columns, column_info_json

    @staticmethod
    def convert_to_serializable(value: Any) -> Any:
        """Convert a value to a JSON-serializable type."""
        if value is None or pd.isna(value):
            return None
        if isinstance(value, (np.integer, np.int64, np.int32)):
            return int(value)
        if isinstance(value, (np.floating, np.float64, np.float32)):
            if np.isnan(value) or np.isinf(value):
                return None
            return float(value)
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, (pd.Timestamp, np.datetime64)):
            return str(value)
        if isinstance(value, (pd.Timedelta, np.timedelta64)):
            return str(value)
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        # Fallback to string for any other types
        try:
            return str(value)
        except Exception:
            return None

    @classmethod
    def get_preview(cls, file_path: Path, file_id: str, file_name: str) -> dict:
        """Get a preview of the file including sample rows."""
        df = cls.read_file(file_path)

        row_count = len(df)
        column_count = len(df.columns)

        columns: List[ColumnInfo] = []
        for col_name in df.columns:
            series = df[col_name]
            col_info = ColumnInfo(
                name=str(col_name),
                data_type=cls.infer_data_type(series),
                non_null_count=int(series.notna().sum()),
                unique_count=int(series.nunique()),
                sample_values=cls.get_sample_values(series),
            )
            columns.append(col_info)

        # Get sample rows
        sample_df = df.head(PREVIEW_ROWS)
        # Convert to records with proper type handling for JSON serialization
        sample_rows = []
        for _, row in sample_df.iterrows():
            row_dict = {}
            for col in df.columns:
                row_dict[str(col)] = cls.convert_to_serializable(row[col])
            sample_rows.append(row_dict)

        return {
            "file_id": file_id,
            "file_name": file_name,
            "row_count": row_count,
            "column_count": column_count,
            "columns": [col.model_dump() for col in columns],
            "sample_rows": sample_rows,
        }
