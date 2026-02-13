#!/usr/bin/env python3
"""
Generate sample data for ICDE demo including:
- Projects with hierarchical structure (Study > Version > Datasets)
- Actual xlsx files with clinical trial data
- Source and derived datasets with relationships
- Example analysis scripts
"""

import os
import sys
import uuid
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, engine
from app.models.base import Base
from app.models import Project, Dataset, DatasetFile, DatasetType, Script


# Configuration
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
SCRIPTS_DIR = Path(__file__).parent.parent / "sample_scripts"


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_adsl_data(n_patients: int = 100) -> pd.DataFrame:
    """Generate ADSL (Subject-Level Analysis Dataset) data."""
    np.random.seed(42)

    # Generate patient IDs
    subjids = [f"SUBJ-{str(i).zfill(4)}" for i in range(1, n_patients + 1)]

    # Demographics
    ages = np.random.normal(55, 12, n_patients).astype(int)
    ages = np.clip(ages, 18, 85)

    sexes = np.random.choice(["M", "F"], n_patients, p=[0.52, 0.48])
    races = np.random.choice(
        ["WHITE", "BLACK", "ASIAN", "OTHER"],
        n_patients,
        p=[0.65, 0.15, 0.12, 0.08]
    )

    # Treatment arms
    arms = np.random.choice(["Treatment A", "Treatment B", "Placebo"], n_patients, p=[0.4, 0.4, 0.2])

    # Analysis populations
    saffl = np.random.choice(["Y", "N"], n_patients, p=[0.95, 0.05])
    ittfl = np.random.choice(["Y", "N"], n_patients, p=[0.98, 0.02])

    # Dates
    base_date = datetime(2024, 1, 1)
    randdt = [base_date + timedelta(days=random.randint(0, 180)) for _ in range(n_patients)]

    # BMI and vital signs at baseline
    heights = np.random.normal(170, 10, n_patients)
    weights = np.random.normal(75, 15, n_patients)
    bmis = weights / ((heights / 100) ** 2)

    return pd.DataFrame({
        "SUBJID": subjids,
        "AGE": ages,
        "SEX": sexes,
        "RACE": races,
        "ARM": arms,
        "SAFFL": saffl,
        "ITTFL": ittfl,
        "RANDDT": randdt,
        "HEIGHT": np.round(heights, 1),
        "WEIGHT": np.round(weights, 1),
        "BMI": np.round(bmis, 1),
    })


def generate_adae_data(adsl_df: pd.DataFrame) -> pd.DataFrame:
    """Generate ADAE (Adverse Events Analysis Dataset) data."""
    np.random.seed(43)

    ae_terms = [
        ("Headache", "NERVOUS SYSTEM DISORDERS"),
        ("Nausea", "GASTROINTESTINAL DISORDERS"),
        ("Fatigue", "GENERAL DISORDERS"),
        ("Dizziness", "NERVOUS SYSTEM DISORDERS"),
        ("Diarrhea", "GASTROINTESTINAL DISORDERS"),
        ("Rash", "SKIN DISORDERS"),
        ("Insomnia", "PSYCHIATRIC DISORDERS"),
        ("Back pain", "MUSCULOSKELETAL DISORDERS"),
        ("Cough", "RESPIRATORY DISORDERS"),
        ("Vomiting", "GASTROINTESTINAL DISORDERS"),
    ]

    severities = ["MILD", "MODERATE", "SEVERE"]
    outcomes = ["RECOVERED", "RECOVERING", "NOT RECOVERED", "RECOVERED WITH SEQUELAE"]

    records = []
    ae_seq = 1

    for _, row in adsl_df.iterrows():
        # Each patient has 0-5 AEs
        n_aes = np.random.poisson(2)
        n_aes = min(n_aes, 5)

        for _ in range(n_aes):
            ae_term, soc = random.choice(ae_terms)
            start_offset = random.randint(1, 90)
            duration = random.randint(1, 30)

            records.append({
                "SUBJID": row["SUBJID"],
                "AESEQ": ae_seq,
                "AETERM": ae_term,
                "AESOC": soc,
                "AESEV": random.choices(severities, weights=[0.6, 0.3, 0.1])[0],
                "AESER": random.choices(["N", "Y"], weights=[0.95, 0.05])[0],
                "AESTDT": row["RANDDT"] + timedelta(days=start_offset),
                "AEENDT": row["RANDDT"] + timedelta(days=start_offset + duration),
                "AEOUT": random.choice(outcomes),
                "ARM": row["ARM"],
            })
            ae_seq += 1

    return pd.DataFrame(records)


def generate_advs_data(adsl_df: pd.DataFrame) -> pd.DataFrame:
    """Generate ADVS (Vital Signs Analysis Dataset) data."""
    np.random.seed(44)

    visits = ["SCREENING", "BASELINE", "WEEK 4", "WEEK 8", "WEEK 12", "END OF STUDY"]
    visit_nums = [1, 2, 3, 4, 5, 6]

    records = []

    for _, row in adsl_df.iterrows():
        base_sbp = np.random.normal(125, 15)
        base_dbp = np.random.normal(80, 10)
        base_hr = np.random.normal(72, 12)
        base_temp = np.random.normal(36.6, 0.3)

        for visit, visitnum in zip(visits, visit_nums):
            # Add some variation per visit
            sbp = base_sbp + np.random.normal(0, 5) - (visitnum * 2 if row["ARM"] != "Placebo" else 0)
            dbp = base_dbp + np.random.normal(0, 3) - (visitnum * 1 if row["ARM"] != "Placebo" else 0)
            hr = base_hr + np.random.normal(0, 5)
            temp = base_temp + np.random.normal(0, 0.2)

            records.append({
                "SUBJID": row["SUBJID"],
                "VISIT": visit,
                "VISITNUM": visitnum,
                "VSTESTCD": "SYSBP",
                "VSTEST": "Systolic Blood Pressure",
                "VSSTRESN": round(sbp, 1),
                "VSSTRESU": "mmHg",
                "ARM": row["ARM"],
            })
            records.append({
                "SUBJID": row["SUBJID"],
                "VISIT": visit,
                "VISITNUM": visitnum,
                "VSTESTCD": "DIABP",
                "VSTEST": "Diastolic Blood Pressure",
                "VSSTRESN": round(dbp, 1),
                "VSSTRESU": "mmHg",
                "ARM": row["ARM"],
            })
            records.append({
                "SUBJID": row["SUBJID"],
                "VISIT": visit,
                "VISITNUM": visitnum,
                "VSTESTCD": "HR",
                "VSTEST": "Heart Rate",
                "VSSTRESN": round(hr, 0),
                "VSSTRESU": "beats/min",
                "ARM": row["ARM"],
            })
            records.append({
                "SUBJID": row["SUBJID"],
                "VISIT": visit,
                "VISITNUM": visitnum,
                "VSTESTCD": "TEMP",
                "VSTEST": "Temperature",
                "VSSTRESN": round(temp, 1),
                "VSSTRESU": "C",
                "ARM": row["ARM"],
            })

    return pd.DataFrame(records)


def generate_adlb_data(adsl_df: pd.DataFrame) -> pd.DataFrame:
    """Generate ADLB (Laboratory Analysis Dataset) data."""
    np.random.seed(45)

    visits = ["SCREENING", "BASELINE", "WEEK 4", "WEEK 8", "WEEK 12"]

    lab_tests = [
        ("ALT", "Alanine Aminotransferase", "U/L", 25, 10, 7, 56),
        ("AST", "Aspartate Aminotransferase", "U/L", 22, 8, 10, 40),
        ("CREAT", "Creatinine", "mg/dL", 1.0, 0.2, 0.6, 1.2),
        ("HGB", "Hemoglobin", "g/dL", 14.0, 1.5, 12.0, 17.5),
        ("WBC", "White Blood Cell Count", "10^9/L", 7.0, 2.0, 4.0, 11.0),
        ("GLUC", "Glucose", "mg/dL", 95, 15, 70, 100),
    ]

    records = []

    for _, row in adsl_df.iterrows():
        for visit_idx, visit in enumerate(visits):
            for testcd, test, unit, mean, std, lln, uln in lab_tests:
                value = np.random.normal(mean, std)
                # Some abnormal values
                if random.random() < 0.05:
                    value = value * random.uniform(1.2, 1.5)

                records.append({
                    "SUBJID": row["SUBJID"],
                    "VISIT": visit,
                    "VISITNUM": visit_idx + 1,
                    "LBTESTCD": testcd,
                    "LBTEST": test,
                    "LBSTRESN": round(value, 2),
                    "LBSTRESU": unit,
                    "LBSTNRLO": lln,
                    "LBSTNRHI": uln,
                    "ARM": row["ARM"],
                })

    return pd.DataFrame(records)


def generate_demographics_summary(adsl_df: pd.DataFrame) -> pd.DataFrame:
    """Generate demographics summary table (derived from ADSL)."""
    results = []

    for arm in adsl_df["ARM"].unique():
        arm_data = adsl_df[adsl_df["ARM"] == arm]
        n_total = len(arm_data)

        # Age stats
        results.append({
            "Category": "Age (years)",
            "Statistic": "n",
            "Treatment": arm,
            "Value": n_total,
        })
        results.append({
            "Category": "Age (years)",
            "Statistic": "Mean (SD)",
            "Treatment": arm,
            "Value": f"{arm_data['AGE'].mean():.1f} ({arm_data['AGE'].std():.1f})",
        })

        # Sex distribution
        for sex in ["M", "F"]:
            n_sex = (arm_data["SEX"] == sex).sum()
            pct = n_sex / n_total * 100
            results.append({
                "Category": "Sex",
                "Statistic": "Male" if sex == "M" else "Female",
                "Treatment": arm,
                "Value": f"{n_sex} ({pct:.1f}%)",
            })

    return pd.DataFrame(results)


def generate_ae_summary(adae_df: pd.DataFrame, adsl_df: pd.DataFrame) -> pd.DataFrame:
    """Generate AE summary table (derived from ADAE and ADSL)."""
    results = []
    arm_counts = adsl_df.groupby("ARM")["SUBJID"].nunique()

    for arm in arm_counts.index:
        arm_aes = adae_df[adae_df["ARM"] == arm]
        n_with_ae = arm_aes["SUBJID"].nunique()
        n_total = arm_counts[arm]
        pct = n_with_ae / n_total * 100

        results.append({
            "Category": "Any AE",
            "Treatment": arm,
            "n": n_with_ae,
            "N": n_total,
            "Percentage": f"{pct:.1f}%",
        })

        # By severity
        for sev in ["MILD", "MODERATE", "SEVERE"]:
            sev_aes = arm_aes[arm_aes["AESEV"] == sev]
            n_with_sev = sev_aes["SUBJID"].nunique()
            pct = n_with_sev / n_total * 100

            results.append({
                "Category": f"{sev.title()} AEs",
                "Treatment": arm,
                "n": n_with_sev,
                "N": n_total,
                "Percentage": f"{pct:.1f}%",
            })

    return pd.DataFrame(results)


def create_xlsx_file(df: pd.DataFrame, file_path: Path, sheet_name: str = "Data"):
    """Save DataFrame to xlsx file."""
    df.to_excel(file_path, sheet_name=sheet_name, index=False)
    return file_path


def create_dataset_with_file(
    db,
    project_id: str,
    dataset_name: str,
    df: pd.DataFrame,
    description: str = None,
    dataset_type: DatasetType = DatasetType.RAW,
    source_dataset_id: str = None,
    script_id: str = None,
    parent_dataset_id: str = None,
    version_name: str = None,
    created_at: datetime = None,
) -> Dataset:
    """Create a dataset with an xlsx file."""
    dataset_id = generate_uuid()
    folder_path = UPLOAD_DIR / dataset_id
    folder_path.mkdir(parents=True, exist_ok=True)

    # Create xlsx file
    file_id = generate_uuid()
    file_name = f"{dataset_name}.xlsx"
    file_path = folder_path / file_name
    create_xlsx_file(df, file_path, sheet_name=dataset_name)

    file_size = file_path.stat().st_size
    row_count, col_count = df.shape

    # Create Dataset
    dataset = Dataset(
        id=dataset_id,
        name=dataset_name,
        description=description or f"{dataset_name} dataset",
        type=dataset_type,
        folder_path=str(folder_path),
        file_count=1,
        total_size=file_size,
        row_count=row_count,
        column_count=col_count,
        project_id=project_id,
        patient_id_column="SUBJID" if "SUBJID" in df.columns else None,
        source_dataset_id=source_dataset_id,
        script_id=script_id,
        parent_dataset_id=parent_dataset_id,
        version_name=version_name,
    )

    # Set custom created_at if provided (for version history demo)
    if created_at:
        dataset.created_at = created_at
        dataset.updated_at = created_at

    # Create DatasetFile
    dataset_file = DatasetFile(
        id=file_id,
        dataset_id=dataset_id,
        file_name=file_name,
        original_name=file_name,
        file_path=str(file_path),
        file_type="xlsx",
        file_size=file_size,
        row_count=row_count,
        column_count=col_count,
        parse_status="parsed",
    )

    if created_at:
        dataset_file.created_at = created_at

    db.add(dataset)
    db.add(dataset_file)

    return dataset


def create_example_scripts(db):
    """Create example analysis scripts with rich LLM-compatible metadata."""
    scripts_data = [
        {
            "name": "count_patients",
            "display_name": "Count Total Patients",
            "description": "Count the total number of unique patients in ADSL dataset. This is a fundamental analysis script used to determine sample sizes for different populations and treatment arms.",
            "code": '''# Count Total Patients
# This script counts unique patients in the ADSL dataset

import pandas as pd

def count_patients(adsl_df: pd.DataFrame, population: str = "all") -> dict:
    """
    Count total number of unique patients.

    Args:
        adsl_df: ADSL DataFrame with SUBJID column
        population: Population to count - "all", "safety", or "itt"

    Returns:
        Dictionary with patient counts
    """
    # Filter by population if specified
    if population == "safety":
        df = adsl_df[adsl_df["SAFFL"] == "Y"]
    elif population == "itt":
        df = adsl_df[adsl_df["ITTFL"] == "Y"]
    else:
        df = adsl_df

    total_patients = df["SUBJID"].nunique()

    # Count by treatment arm
    by_arm = df.groupby("ARM")["SUBJID"].nunique().to_dict()

    # Count by population flags
    safety_pop = adsl_df[adsl_df["SAFFL"] == "Y"]["SUBJID"].nunique()
    itt_pop = adsl_df[adsl_df["ITTFL"] == "Y"]["SUBJID"].nunique()

    return {
        "total_patients": total_patients,
        "by_treatment_arm": by_arm,
        "safety_population": safety_pop,
        "itt_population": itt_pop,
        "population_used": population,
    }

# Example usage:
# result = count_patients(adsl_df)
# print(f"Total patients: {result['total_patients']}")
''',
            "keywords": ["count", "patients", "population", "ADSL", "sample size", "N"],
            "language": "python",
            "input_requirements": "ADSL dataset with SUBJID, ARM, SAFFL, ITTFL columns",
            "output_description": "Dictionary with patient counts by arm and population",
            # New structured metadata
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "adsl_df": {
                        "type": "DataFrame",
                        "description": "Subject-Level Analysis Dataset (ADSL) containing one row per patient with demographics and population flags"
                    },
                    "population": {
                        "type": "string",
                        "description": "Which population to count patients for",
                        "enum": ["all", "safety", "itt"],
                        "default": "all"
                    }
                },
                "required": ["adsl_df"]
            },
            "returns_schema": {
                "type": "dict",
                "description": "Dictionary containing patient counts",
                "properties": {
                    "total_patients": {"type": "int", "description": "Total unique patient count"},
                    "by_treatment_arm": {"type": "dict", "description": "Patient count per treatment arm"},
                    "safety_population": {"type": "int", "description": "Patients in safety population"},
                    "itt_population": {"type": "int", "description": "Patients in ITT population"},
                    "population_used": {"type": "string", "description": "Which population filter was applied"}
                }
            },
            "functions": [
                {"name": "count_patients", "description": "Count unique patients with optional population filter", "is_main": True}
            ],
            "use_cases": [
                "Get total number of patients enrolled in the study",
                "Count patients by treatment arm for disposition table",
                "Determine sample size for safety population analysis",
                "Calculate N for ITT population in efficacy tables",
                "Verify patient counts match protocol requirements"
            ],
            "example_calls": [
                {"input": "count_patients(adsl_df)", "output": "{'total_patients': 100, 'by_treatment_arm': {'Treatment A': 40, 'Treatment B': 40, 'Placebo': 20}, ...}", "description": "Count all patients"},
                {"input": "count_patients(adsl_df, population='safety')", "output": "{'total_patients': 95, 'by_treatment_arm': {...}, 'population_used': 'safety'}", "description": "Count safety population only"}
            ]
        },
        {
            "name": "demographics_summary",
            "display_name": "Demographics Summary Table",
            "description": "Generate summary statistics for patient demographics including age, sex, and race distributions by treatment arm. Produces output suitable for Table 14.1 in clinical study reports.",
            "code": '''# Demographics Summary
# Generate summary statistics for patient demographics

import pandas as pd
import numpy as np

def demographics_summary(adsl_df: pd.DataFrame, variables: list = None) -> pd.DataFrame:
    """
    Generate demographics summary table.

    Args:
        adsl_df: ADSL DataFrame
        variables: List of variables to summarize (default: ["AGE", "SEX", "RACE"])

    Returns:
        Summary DataFrame
    """
    if variables is None:
        variables = ["AGE", "SEX", "RACE"]

    results = []

    for arm in adsl_df["ARM"].unique():
        arm_data = adsl_df[adsl_df["ARM"] == arm]
        n_total = len(arm_data)

        # Age statistics (continuous)
        if "AGE" in variables:
            results.append({
                "Category": "Age (years)",
                "Statistic": "n",
                "Treatment Arm": arm,
                "Value": str(n_total)
            })
            results.append({
                "Category": "Age (years)",
                "Statistic": "Mean (SD)",
                "Treatment Arm": arm,
                "Value": f"{arm_data['AGE'].mean():.1f} ({arm_data['AGE'].std():.1f})"
            })
            results.append({
                "Category": "Age (years)",
                "Statistic": "Median [Min, Max]",
                "Treatment Arm": arm,
                "Value": f"{arm_data['AGE'].median():.0f} [{arm_data['AGE'].min()}, {arm_data['AGE'].max()}]"
            })

        # Sex distribution (categorical)
        if "SEX" in variables:
            for sex, label in [("M", "Male"), ("F", "Female")]:
                n_sex = (arm_data["SEX"] == sex).sum()
                pct = n_sex / n_total * 100
                results.append({
                    "Category": "Sex, n (%)",
                    "Statistic": label,
                    "Treatment Arm": arm,
                    "Value": f"{n_sex} ({pct:.1f}%)"
                })

        # Race distribution (categorical)
        if "RACE" in variables:
            for race in arm_data["RACE"].unique():
                n_race = (arm_data["RACE"] == race).sum()
                pct = n_race / n_total * 100
                results.append({
                    "Category": "Race, n (%)",
                    "Statistic": race.title(),
                    "Treatment Arm": arm,
                    "Value": f"{n_race} ({pct:.1f}%)"
                })

    return pd.DataFrame(results)

# Example usage:
# summary = demographics_summary(adsl_df)
# print(summary.to_string())
''',
            "keywords": ["demographics", "summary", "age", "sex", "race", "baseline", "Table 14.1", "characteristics"],
            "language": "python",
            "input_requirements": "ADSL dataset with AGE, SEX, RACE, ARM columns",
            "output_description": "DataFrame with demographics summary by treatment arm in CSR format",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "adsl_df": {
                        "type": "DataFrame",
                        "description": "Subject-Level Analysis Dataset with demographic variables"
                    },
                    "variables": {
                        "type": "list",
                        "description": "List of variables to include in summary",
                        "default": ["AGE", "SEX", "RACE"],
                        "items": {"type": "string", "enum": ["AGE", "SEX", "RACE", "ETHNIC", "COUNTRY", "BMI", "HEIGHT", "WEIGHT"]}
                    }
                },
                "required": ["adsl_df"]
            },
            "returns_schema": {
                "type": "DataFrame",
                "description": "Summary table with columns: Category, Statistic, Treatment Arm, Value"
            },
            "functions": [
                {"name": "demographics_summary", "description": "Generate demographics summary table", "is_main": True}
            ],
            "use_cases": [
                "Generate Table 14.1.1 Demographics and Baseline Characteristics",
                "Summarize patient baseline characteristics for CSR",
                "Compare demographic distributions across treatment arms",
                "Create baseline summary for safety population",
                "Generate demographics table for regulatory submission"
            ],
            "example_calls": [
                {"input": "demographics_summary(adsl_df)", "output": "DataFrame with 15 rows showing Age, Sex, Race by arm", "description": "Full demographics summary"},
                {"input": "demographics_summary(adsl_df, variables=['AGE', 'SEX'])", "output": "DataFrame with Age and Sex only", "description": "Subset of variables"}
            ]
        },
        {
            "name": "ae_summary",
            "display_name": "Adverse Events Summary",
            "description": "Summarize adverse events by system organ class (SOC) and treatment arm. Calculates incidence rates using safety population as denominator. Suitable for safety summary tables in clinical study reports.",
            "code": '''# Adverse Events Summary
# Summarize AEs by system organ class and treatment arm

import pandas as pd

def ae_summary(adae_df: pd.DataFrame, adsl_df: pd.DataFrame, by: str = "SOC") -> pd.DataFrame:
    """
    Generate adverse events summary by SOC or preferred term.

    Args:
        adae_df: ADAE DataFrame
        adsl_df: ADSL DataFrame for denominators
        by: Grouping level - "SOC" for system organ class or "PT" for preferred term

    Returns:
        Summary DataFrame with incidence rates
    """
    results = []

    # Get treatment arm counts (safety population)
    safety_pop = adsl_df[adsl_df["SAFFL"] == "Y"]
    arm_counts = safety_pop.groupby("ARM")["SUBJID"].nunique()

    # Patients with any AE
    for arm in arm_counts.index:
        arm_aes = adae_df[adae_df["ARM"] == arm]
        n_with_ae = arm_aes["SUBJID"].nunique()
        n_total = arm_counts[arm]
        pct = n_with_ae / n_total * 100 if n_total > 0 else 0

        results.append({
            "Category": "Patients with any AE",
            "Treatment Arm": arm,
            "n": n_with_ae,
            "N": n_total,
            "Percentage": f"{pct:.1f}%"
        })

    # By SOC or PT
    group_col = "AESOC" if by == "SOC" else "AETERM"
    for group_val in sorted(adae_df[group_col].unique()):
        for arm in arm_counts.index:
            group_arm_aes = adae_df[(adae_df[group_col] == group_val) & (adae_df["ARM"] == arm)]
            n_with_group = group_arm_aes["SUBJID"].nunique()
            n_total = arm_counts[arm]
            pct = n_with_group / n_total * 100 if n_total > 0 else 0

            results.append({
                "Category": group_val.title() if by == "SOC" else group_val,
                "Treatment Arm": arm,
                "n": n_with_group,
                "N": n_total,
                "Percentage": f"{pct:.1f}%"
            })

    return pd.DataFrame(results)

# Example usage:
# summary = ae_summary(adae_df, adsl_df)
# print(summary.to_string())
''',
            "keywords": ["adverse events", "AE", "safety", "SOC", "summary", "incidence", "TEAE"],
            "language": "python",
            "input_requirements": "ADAE and ADSL datasets",
            "output_description": "DataFrame with AE summary by SOC and treatment arm",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "adae_df": {
                        "type": "DataFrame",
                        "description": "Adverse Events Analysis Dataset with one row per AE"
                    },
                    "adsl_df": {
                        "type": "DataFrame",
                        "description": "Subject-Level Dataset for population denominators"
                    },
                    "by": {
                        "type": "string",
                        "description": "Grouping level for AE summary",
                        "enum": ["SOC", "PT"],
                        "default": "SOC"
                    }
                },
                "required": ["adae_df", "adsl_df"]
            },
            "returns_schema": {
                "type": "DataFrame",
                "description": "Summary table with columns: Category, Treatment Arm, n, N, Percentage"
            },
            "functions": [
                {"name": "ae_summary", "description": "Generate AE incidence table by SOC or PT", "is_main": True}
            ],
            "use_cases": [
                "Generate Table 14.3.1 Overall Adverse Events Summary",
                "Summarize TEAEs by System Organ Class",
                "Calculate AE incidence rates for safety review",
                "Compare adverse event profiles between treatment arms",
                "Create AE overview table for DSMB"
            ],
            "example_calls": [
                {"input": "ae_summary(adae_df, adsl_df)", "output": "DataFrame showing AE incidence by SOC and arm", "description": "Summary by System Organ Class"},
                {"input": "ae_summary(adae_df, adsl_df, by='PT')", "output": "DataFrame showing AE incidence by Preferred Term", "description": "Summary by Preferred Term"}
            ]
        },
        {
            "name": "vital_signs_change",
            "display_name": "Vital Signs Change from Baseline",
            "description": "Calculate and summarize change from baseline for vital signs parameters (blood pressure, heart rate, temperature). Produces summary statistics by visit and treatment arm for efficacy and safety analyses.",
            "code": '''# Vital Signs Change from Baseline
# Calculate and summarize vital sign changes

import pandas as pd
import numpy as np

def vital_signs_change(advs_df: pd.DataFrame, parameters: list = None, visits: list = None) -> pd.DataFrame:
    """
    Calculate change from baseline for vital signs.

    Args:
        advs_df: ADVS DataFrame
        parameters: List of vital signs parameters (default: all)
        visits: List of visits to include (default: post-baseline visits)

    Returns:
        Summary DataFrame with change from baseline statistics
    """
    if parameters is None:
        parameters = advs_df["VSTESTCD"].unique().tolist()

    if visits is None:
        visits = ["WEEK 4", "WEEK 8", "WEEK 12", "END OF STUDY"]

    results = []

    # Get baseline values
    baseline = advs_df[advs_df["VISIT"] == "BASELINE"].copy()
    baseline = baseline.rename(columns={"VSSTRESN": "BASE"})
    baseline = baseline[["SUBJID", "VSTESTCD", "BASE", "ARM"]]

    # Merge with all visits
    merged = advs_df.merge(baseline, on=["SUBJID", "VSTESTCD", "ARM"])
    merged["CHG"] = merged["VSSTRESN"] - merged["BASE"]

    # Summary by visit and test
    for vstestcd in parameters:
        if vstestcd not in merged["VSTESTCD"].unique():
            continue

        test_data = merged[merged["VSTESTCD"] == vstestcd]
        test_name = test_data["VSTEST"].iloc[0] if len(test_data) > 0 else vstestcd
        unit = test_data["VSSTRESU"].iloc[0] if len(test_data) > 0 else ""

        for visit in visits:
            visit_data = test_data[test_data["VISIT"] == visit]
            if len(visit_data) == 0:
                continue

            for arm in sorted(visit_data["ARM"].unique()):
                arm_data = visit_data[visit_data["ARM"] == arm]

                results.append({
                    "Parameter": f"{test_name} ({unit})",
                    "Parameter Code": vstestcd,
                    "Visit": visit,
                    "Treatment Arm": arm,
                    "N": len(arm_data),
                    "Baseline Mean": f"{arm_data['BASE'].mean():.2f}",
                    "Post-Baseline Mean": f"{arm_data['VSSTRESN'].mean():.2f}",
                    "Mean Change": f"{arm_data['CHG'].mean():.2f}",
                    "SD": f"{arm_data['CHG'].std():.2f}",
                })

    return pd.DataFrame(results)

# Example usage:
# changes = vital_signs_change(advs_df)
# print(changes.to_string())
''',
            "keywords": ["vital signs", "change", "baseline", "blood pressure", "CFB", "efficacy"],
            "language": "python",
            "input_requirements": "ADVS dataset with VISIT, VSTESTCD, VSSTRESN columns",
            "output_description": "DataFrame with vital signs changes from baseline by visit and arm",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "advs_df": {
                        "type": "DataFrame",
                        "description": "Vital Signs Analysis Dataset with measurements by visit"
                    },
                    "parameters": {
                        "type": "list",
                        "description": "Vital signs parameters to analyze",
                        "default": None,
                        "items": {"type": "string", "enum": ["SYSBP", "DIABP", "HR", "TEMP", "RESP", "WEIGHT"]}
                    },
                    "visits": {
                        "type": "list",
                        "description": "Visits to include in analysis",
                        "default": ["WEEK 4", "WEEK 8", "WEEK 12", "END OF STUDY"]
                    }
                },
                "required": ["advs_df"]
            },
            "returns_schema": {
                "type": "DataFrame",
                "description": "Summary table with change from baseline statistics including N, Baseline Mean, Post-Baseline Mean, Mean Change, SD"
            },
            "functions": [
                {"name": "vital_signs_change", "description": "Calculate change from baseline for vital signs", "is_main": True}
            ],
            "use_cases": [
                "Analyze blood pressure changes for antihypertensive efficacy",
                "Generate Table 14.2 Vital Signs Summary",
                "Calculate change from baseline for safety review",
                "Compare vital signs trajectories across treatment arms",
                "Assess treatment effect on cardiovascular parameters"
            ],
            "example_calls": [
                {"input": "vital_signs_change(advs_df)", "output": "DataFrame with all VS parameters and visits", "description": "Full vital signs analysis"},
                {"input": "vital_signs_change(advs_df, parameters=['SYSBP', 'DIABP'])", "output": "DataFrame with blood pressure only", "description": "Blood pressure focus"},
                {"input": "vital_signs_change(advs_df, visits=['WEEK 12'])", "output": "DataFrame for Week 12 only", "description": "Single visit analysis"}
            ]
        },
    ]

    created_scripts = {}
    for script_data in scripts_data:
        script = Script(
            id=generate_uuid(),
            name=script_data["name"],
            display_name=script_data["display_name"],
            description=script_data["description"],
            code=script_data["code"],
            keywords=json.dumps(script_data["keywords"], ensure_ascii=False),
            language=script_data["language"],
            input_requirements=script_data["input_requirements"],
            output_description=script_data["output_description"],
            # New structured metadata
            parameters_schema=json.dumps(script_data.get("parameters_schema"), ensure_ascii=False) if script_data.get("parameters_schema") else None,
            returns_schema=json.dumps(script_data.get("returns_schema"), ensure_ascii=False) if script_data.get("returns_schema") else None,
            functions=json.dumps(script_data.get("functions"), ensure_ascii=False) if script_data.get("functions") else None,
            use_cases=json.dumps(script_data.get("use_cases"), ensure_ascii=False) if script_data.get("use_cases") else None,
            example_calls=json.dumps(script_data.get("example_calls"), ensure_ascii=False) if script_data.get("example_calls") else None,
            created_by="user",
            usage_count=random.randint(5, 50),
            version=1,
        )
        db.add(script)
        created_scripts[script_data["name"]] = script

    return created_scripts


def main():
    """Main function to generate all sample data."""
    print("Generating sample data...")

    # Ensure upload directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Create database session
    db = SessionLocal()

    try:
        # Clear existing data
        print("Clearing existing data...")
        db.query(DatasetFile).delete()
        db.query(Dataset).delete()
        db.query(Project).delete()
        db.query(Script).delete()
        db.commit()

        # Create project
        print("Creating project...")
        project = Project(
            id=generate_uuid(),
            name="Hypertension Trial ABC-123",
            description="Phase 3 clinical trial for hypertension treatment",
        )
        db.add(project)
        db.commit()

        # Create scripts first (needed for derived datasets)
        print("Creating example scripts...")
        scripts = create_example_scripts(db)
        db.commit()

        # Generate base data
        print("Generating clinical data...")
        adsl_data = generate_adsl_data(100)
        adae_data = generate_adae_data(adsl_data)
        advs_data = generate_advs_data(adsl_data)
        adlb_data = generate_adlb_data(adsl_data)

        # Create SOURCE datasets with version history
        print("Creating source datasets with version history...")

        # ADSL - Create version chain (v1.0 -> v1.1 -> v2.0)
        # v1.0 - Initial upload (80 patients, 2 months ago)
        adsl_v1_data = generate_adsl_data(80)
        adsl_v1 = create_dataset_with_file(
            db, project.id, "ADSL",
            adsl_v1_data,
            "Subject-Level Analysis Dataset - Initial data cut with 80 subjects",
            DatasetType.RAW,
            version_name="v1.0",
            created_at=datetime.now() - timedelta(days=60),
        )
        db.flush()

        # v1.1 - Minor update (85 patients, 1 month ago)
        adsl_v1_1_data = generate_adsl_data(85)
        adsl_v1_1 = create_dataset_with_file(
            db, project.id, "ADSL",
            adsl_v1_1_data,
            "Subject-Level Analysis Dataset - Updated with 5 additional subjects",
            DatasetType.RAW,
            parent_dataset_id=adsl_v1.id,
            version_name="v1.1",
            created_at=datetime.now() - timedelta(days=30),
        )
        db.flush()

        # v2.0 - Current version (100 patients, now)
        adsl_dataset = create_dataset_with_file(
            db, project.id, "ADSL",
            adsl_data,
            "Subject-Level Analysis Dataset - Final data cut with 100 subjects",
            DatasetType.RAW,
            parent_dataset_id=adsl_v1_1.id,
            version_name="v2.0",
        )

        # ADAE - Create version chain (v1.0 -> v1.1)
        # v1.0 - Initial (based on v1.0 ADSL)
        adae_v1_data = generate_adae_data(adsl_v1_data)
        adae_v1 = create_dataset_with_file(
            db, project.id, "ADAE",
            adae_v1_data,
            "Adverse Events Analysis Dataset - Initial data cut",
            DatasetType.RAW,
            version_name="v1.0",
            created_at=datetime.now() - timedelta(days=45),
        )
        db.flush()

        # v1.1 - Current version
        adae_dataset = create_dataset_with_file(
            db, project.id, "ADAE",
            adae_data,
            "Adverse Events Analysis Dataset - Updated with complete AE data",
            DatasetType.RAW,
            parent_dataset_id=adae_v1.id,
            version_name="v1.1",
        )

        # ADVS - Single version (current)
        advs_dataset = create_dataset_with_file(
            db, project.id, "ADVS",
            advs_data,
            "Vital Signs Analysis Dataset - Contains vital signs measurements by visit",
            DatasetType.RAW,
            version_name="v1.0",
        )

        # ADLB - Single version (current)
        adlb_dataset = create_dataset_with_file(
            db, project.id, "ADLB",
            adlb_data,
            "Laboratory Analysis Dataset - Contains laboratory test results by visit",
            DatasetType.RAW,
            version_name="v1.0",
        )

        db.commit()

        # Create DERIVED datasets
        print("Creating derived datasets...")

        # Demographics summary derived from ADSL
        demo_summary = generate_demographics_summary(adsl_data)
        create_dataset_with_file(
            db, project.id, "ADSL_Demographics_Summary",
            demo_summary,
            "Demographics Summary Table - Derived from ADSL, shows age and sex distribution by treatment",
            DatasetType.DERIVED,
            source_dataset_id=adsl_dataset.id,
            script_id=scripts["demographics_summary"].id,
        )

        # AE summary derived from ADAE and ADSL
        ae_summary = generate_ae_summary(adae_data, adsl_data)
        create_dataset_with_file(
            db, project.id, "ADAE_Safety_Summary",
            ae_summary,
            "Adverse Events Safety Summary - Derived from ADAE, shows AE incidence by severity",
            DatasetType.DERIVED,
            source_dataset_id=adae_dataset.id,
            script_id=scripts["ae_summary"].id,
        )

        # Safety population subset derived from ADSL
        safety_pop = adsl_data[adsl_data["SAFFL"] == "Y"].copy()
        create_dataset_with_file(
            db, project.id, "ADSL_Safety_Population",
            safety_pop,
            "Safety Population - Subset of ADSL containing only subjects in safety population",
            DatasetType.DERIVED,
            source_dataset_id=adsl_dataset.id,
        )

        # ITT population subset derived from ADSL
        itt_pop = adsl_data[adsl_data["ITTFL"] == "Y"].copy()
        create_dataset_with_file(
            db, project.id, "ADSL_ITT_Population",
            itt_pop,
            "ITT Population - Subset of ADSL containing only subjects in ITT population",
            DatasetType.DERIVED,
            source_dataset_id=adsl_dataset.id,
        )

        db.commit()
        print("Sample data generation complete!")

        # Print summary
        print("\n--- Summary ---")
        print(f"Project: {project.name}")

        source_count = db.query(Dataset).filter(Dataset.type == DatasetType.RAW).count()
        derived_count = db.query(Dataset).filter(Dataset.type == DatasetType.DERIVED).count()

        print(f"Source datasets: {source_count}")
        print(f"Derived datasets: {derived_count}")
        print(f"Total datasets: {db.query(Dataset).count()}")
        print(f"Files created: {db.query(DatasetFile).count()}")
        print(f"Scripts created: {db.query(Script).count()}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
