"""
Service for calculating differences between dataset versions.
"""
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

from .file_parser import FileParser


class DiffCalculator:
    """Calculate differences between two versions of a dataset."""

    def __init__(self, patient_id_column: str = "SUBJID"):
        self.patient_id_column = patient_id_column

    def calculate(
        self,
        v1_path: Path,
        v2_path: Path,
    ) -> Dict[str, Any]:
        """
        Calculate differences between two dataset versions.

        Args:
            v1_path: Path to version 1 (older)
            v2_path: Path to version 2 (newer)

        Returns:
            Dictionary with diff summary
        """
        # Load both datasets
        df1 = FileParser.read_file(v1_path)
        df2 = FileParser.read_file(v2_path)

        # Patient-level diff
        patients_v1 = set(df1[self.patient_id_column].astype(str))
        patients_v2 = set(df2[self.patient_id_column].astype(str))

        patients_added = list(patients_v2 - patients_v1)
        patients_removed = list(patients_v1 - patients_v2)
        patients_common = patients_v1 & patients_v2

        # Find modified patients (common patients with changed data)
        patients_modified = []
        if patients_common:
            for patient_id in patients_common:
                row_v1 = df1[df1[self.patient_id_column].astype(str) == patient_id].iloc[0]
                row_v2 = df2[df2[self.patient_id_column].astype(str) == patient_id].iloc[0]

                # Compare common columns
                common_cols = set(df1.columns) & set(df2.columns)
                for col in common_cols:
                    val1 = row_v1.get(col)
                    val2 = row_v2.get(col)
                    # Handle NaN comparison
                    if pd.isna(val1) and pd.isna(val2):
                        continue
                    if val1 != val2:
                        patients_modified.append(patient_id)
                        break

        # Column-level diff
        columns_v1 = set(df1.columns)
        columns_v2 = set(df2.columns)

        columns_added = list(columns_v2 - columns_v1)
        columns_removed = list(columns_v1 - columns_v2)

        # Calculate total cells changed (for common patients and columns)
        total_cells_changed = 0
        common_cols = columns_v1 & columns_v2

        for patient_id in patients_common:
            row_v1 = df1[df1[self.patient_id_column].astype(str) == patient_id].iloc[0]
            row_v2 = df2[df2[self.patient_id_column].astype(str) == patient_id].iloc[0]

            for col in common_cols:
                val1 = row_v1.get(col)
                val2 = row_v2.get(col)
                if pd.isna(val1) and pd.isna(val2):
                    continue
                if val1 != val2:
                    total_cells_changed += 1

        return {
            'patients_added': patients_added,
            'patients_removed': patients_removed,
            'patients_modified': patients_modified,
            'columns_added': columns_added,
            'columns_removed': columns_removed,
            'total_cells_changed': total_cells_changed,
            'total_rows_v1': len(df1),
            'total_rows_v2': len(df2),
            'total_columns_v1': len(df1.columns),
            'total_columns_v2': len(df2.columns),
        }

    def generate_summary_text(self, diff: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of the diff.

        Args:
            diff: Diff dictionary from calculate()

        Returns:
            Summary text
        """
        lines = []

        # Row changes
        if diff['patients_added']:
            lines.append(f"+ {len(diff['patients_added'])} patients added")
        if diff['patients_removed']:
            lines.append(f"- {len(diff['patients_removed'])} patients removed")
        if diff['patients_modified']:
            lines.append(f"~ {len(diff['patients_modified'])} patients modified")

        # Column changes
        if diff['columns_added']:
            lines.append(f"+ {len(diff['columns_added'])} columns added: {', '.join(diff['columns_added'])}")
        if diff['columns_removed']:
            lines.append(f"- {len(diff['columns_removed'])} columns removed: {', '.join(diff['columns_removed'])}")

        # Total
        if diff['total_cells_changed']:
            lines.append(f"Total cells changed: {diff['total_cells_changed']}")

        if not lines:
            return "No changes detected"

        return "\n".join(lines)
