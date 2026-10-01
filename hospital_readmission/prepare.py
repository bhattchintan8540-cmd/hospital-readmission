"""Load and clean the Kaggle hospital administration file only.

Source: https://www.kaggle.com/datasets/shivavashishtha/hospital-administration-data/
The archive contains HA Data.csv (66,587 rows, 49 columns). No other database is used.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

KAGGLE_DOWNLOAD_URL = (
    "https://www.kaggle.com/api/v1/datasets/download/"
    "shivavashishtha/hospital-administration-data"
)
KAGGLE_PAGE = "https://www.kaggle.com/datasets/shivavashishtha/hospital-administration-data/"

# Appendix A of the solution guide. X1 is max glucose serum, X2 is HbA1c.
MEDICATIONS = [
    ("X3", "metformin", "Metformin"),
    ("X4", "repaglinide", "Repaglinide"),
    ("X5", "nateglinide", "Nateglinide"),
    ("X6", "chlorpropamide", "Chlorpropamide"),
    ("X7", "glimepiride", "Glimepiride"),
    ("X8", "acetohexamide", "Acetohexamide"),
    ("X9", "glipizide", "Glipizide"),
    ("X10", "glyburide", "Glyburide"),
    ("X11", "tolbutamide", "Tolbutamide"),
    ("X12", "pioglitazone", "Pioglitazone"),
    ("X13", "rosiglitazone", "Rosiglitazone"),
    ("X14", "acarbose", "Acarbose"),
    ("X15", "miglitol", "Miglitol"),
    ("X16", "troglitazone", "Troglitazone"),
    ("X17", "tolazamide", "Tolazamide"),
    ("X18", "examide", "Examide"),
    ("X19", "citoglipton", "Citoglipton"),
    ("X20", "insulin", "Insulin"),
    ("X21", "glyburide-metformin", "Glyburide-metformin"),
    ("X22", "glipizide-metformin", "Glipizide-metformin"),
    ("X23", "glimepiride-pioglitazone", "Glimepiride-pioglitazone"),
    ("X24", "metformin-rosiglitazone", "Metformin-rosiglitazone"),
    ("X25", "metformin-pioglitazone", "Metformin-pioglitazone"),
]

# Patients discharged expired or to hospice are not at risk of readmission.
EXPIRED_OR_HOSPICE = {11, 13, 14, 19, 20, 21}

AGE_ORDER = [
    "[0-10)",
    "[10-20)",
    "[20-30)",
    "[30-40)",
    "[40-50)",
    "[50-60)",
    "[60-70)",
    "[70-80)",
    "[80-90)",
    "[90-100)",
]

DISCHARGE_LABELS = {
    1: "Home",
    6: "Home with health service",
    8: "Home with health service",
    3: "Skilled nursing / ICF",
    4: "Skilled nursing / ICF",
    24: "Skilled nursing / ICF",
    22: "Rehab",
    2: "Other facility",
    5: "Other facility",
    9: "Other facility",
    10: "Other facility",
    15: "Other facility",
    16: "Other facility",
    17: "Other facility",
    23: "Other facility",
    27: "Other facility",
    28: "Other facility",
    29: "Other facility",
    30: "Other facility",
    7: "Left against advice",
    11: "Expired/Hospice",
    13: "Expired/Hospice",
    14: "Expired/Hospice",
    19: "Expired/Hospice",
    20: "Expired/Hospice",
    21: "Expired/Hospice",
}


def ensure_kaggle_csv() -> Path:
    """Download the Kaggle archive if the CSV is not already stored locally."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_DIR / "Hospital_Administration_Database.csv"
    if csv_path.exists():
        return csv_path
    zip_path = DATA_DIR / "hospital-administration-data.zip"
    urlretrieve(KAGGLE_DOWNLOAD_URL, zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        csv_names = [name for name in names if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise RuntimeError(f"Expected one CSV in the Kaggle archive, found {csv_names}")
        extracted = zf.read(csv_names[0])
    csv_path.write_bytes(extracted)
    return csv_path


def age_midpoint(age: str) -> float:
    text = str(age).strip().replace("[", "").replace(")", "").replace("]", "")
    lo, hi = text.split("-")
    return (float(lo) + float(hi)) / 2.0


def diag_group(code) -> str:
    if pd.isna(code):
        return "Unknown"
    text = str(code).strip()
    if text in {"", "?", "nan"}:
        return "Unknown"
    upper = text.upper()
    if upper.startswith("V") or upper.startswith("E"):
        return "External/Supplementary (V/E)"
    try:
        value = float(text)
    except ValueError:
        return "Other"
    if 250 <= value < 251:
        return "Diabetes"
    chapter = int(value)
    ranges = [
        (390, 459, "Circulatory"),
        (460, 519, "Respiratory"),
        (520, 579, "Digestive"),
        (580, 629, "Genitourinary"),
        (710, 739, "Musculoskeletal"),
        (140, 239, "Neoplasms"),
        (800, 999, "Injury/Poisoning"),
    ]
    for lo, hi, name in ranges:
        if lo <= chapter <= hi:
            return name
    return "Other"


def diag_code3(code) -> str:
    if pd.isna(code):
        return "Unknown"
    text = str(code).strip()
    if text in {"", "?", "nan"}:
        return "Unknown"
    upper = text.upper()
    if upper[0] in {"V", "E"}:
        digits = "".join(ch for ch in upper[1:] if ch.isdigit())
        return upper[0] + digits[:2]
    try:
        return str(int(float(text)))
    except ValueError:
        return text[:3]


def is_diabetes_code(code) -> bool:
    if pd.isna(code):
        return False
    text = str(code).strip()
    if text in {"", "?", "nan"}:
        return False
    try:
        return 250 <= float(text) < 251
    except ValueError:
        return text.startswith("250")


def discharge_group(code) -> str:
    if pd.isna(code) or str(code).strip() in {"", "?", "nan"}:
        return "Unknown"
    try:
        key = int(float(code))
    except ValueError:
        return "Unknown"
    return DISCHARGE_LABELS.get(key, "Unknown")


def _medication_used(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    return (~text.isna() & ~text.isin(["No", "None", "", "nan"])).astype(int)


def _finalize(df: pd.DataFrame, meta: dict) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    df["age_mid"] = df["age"].map(age_midpoint)
    df["diag_1_group"] = df["diag_1"].map(diag_group)
    df["diag_1_code3"] = df["diag_1"].map(diag_code3)
    df["diabetes_dx"] = (
        df["diag_1"].map(is_diabetes_code) | df["diag_2"].map(is_diabetes_code) | df["diag_3"].map(is_diabetes_code)
    ).astype(int)
    df["change_flag"] = (df["change"] == "Ch").astype(int)
    df["diabetes_med_flag"] = (df["diabetesMed"] == "Yes").astype(int)
    df["insulin_status"] = df["insulin"].astype("string").fillna("No")
    df["insulin_used"] = _medication_used(df["insulin"])
    df["hba1c_measured"] = _medication_used(df["A1Cresult"])
    for _code, column, _label in MEDICATIONS:
        df[f"{column}_used"] = _medication_used(df[column])
    df["weight_recorded"] = (df["weight"] != "Not recorded").astype(int)
    if "discharge_disposition_id" in df.columns:
        df["discharge_group"] = df["discharge_disposition_id"].map(discharge_group)
    else:
        df["discharge_group"] = "Not in source file"
    df = df.sort_values("encounter_id").reset_index(drop=True)
    df["row_id"] = np.arange(1, len(df) + 1)
    df["seq_decile"] = pd.qcut(df["encounter_id"].rank(method="first"), 10, labels=list(range(1, 11))).astype(int)
    meta["analysis_rows"] = int(len(df))
    meta["unique_patients"] = int(df["patient_id"].nunique())
    meta["readmitted_n"] = int(df["readmitted"].sum())
    meta["readmission_rate"] = float(df["readmitted"].mean()) if len(df) else float("nan")
    return df, meta


def _standardise_demographics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["race"] = df["race"].replace({"?": "Unknown"}).fillna("Unknown")
    df["gender"] = df["gender"].replace({"Unknown/Invalid": "Unknown"}).fillna("Unknown")
    df["weight"] = df["weight"].replace({"?": "Not recorded"}).fillna("Not recorded")
    df["medical_specialty"] = df["medical_specialty"].replace({"?": "Not recorded"}).fillna("Not recorded")
    return df


def load_kaggle(path: Path) -> tuple[pd.DataFrame, dict]:
    """Cleaning steps in solution-guide section 3.2."""
    # keep_default_na=False is required: X1 and X2 use the text "None" for "test not performed".
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    meta = {
        "source_kind": "kaggle",
        "source_page": KAGGLE_PAGE,
        "source_path": str(path),
        "source_rows": int(len(raw)),
        "source_columns": int(raw.shape[1]),
        "target_definition": "readmitted is already 1 for readmission within 30 days and 0 otherwise.",
        "x1_none": int((raw["X1"] == "None").sum()) if "X1" in raw.columns else 0,
        "x2_none": int((raw["X2"] == "None").sum()) if "X2" in raw.columns else 0,
    }
    if "index" in raw.columns:
        raw = raw.drop(columns=["index"])
        meta["dropped_index"] = True
    dup = int(raw.duplicated().sum())
    meta["duplicate_rows_removed"] = dup
    raw = raw.drop_duplicates(keep="first")
    if "diag_4" in raw.columns and "diag_3" in raw.columns and raw["diag_4"].equals(raw["diag_3"]):
        raw = raw.drop(columns=["diag_4"])
        meta["dropped_diag_4"] = "exact copy of diag_3"
    if "diag_5" in raw.columns:
        raw = raw.drop(columns=["diag_5"])
        meta["dropped_diag_5"] = "non-diagnostic decimals"
    rename = {}
    if "patient_nbr" in raw.columns and "patient_id" not in raw.columns:
        rename["patient_nbr"] = "patient_id"
    if "max_glu_serum" in raw.columns:
        rename["max_glu_serum"] = "X1"
    if "A1Cresult" in raw.columns:
        rename["A1Cresult"] = "X2"
    raw = raw.rename(columns=rename)
    raw = raw.rename(columns={code: column for code, column, _label in MEDICATIONS if code in raw.columns})
    raw["readmitted"] = pd.to_numeric(raw["readmitted"], errors="raise").astype(int)
    for col in [
        "time_in_hospital",
        "num_lab_procedures",
        "num_procedures",
        "num_medications",
        "number_outpatient",
        "number_emergency",
        "number_inpatient",
        "number_diagnoses",
        "encounter_id",
        "patient_id",
    ]:
        raw[col] = pd.to_numeric(raw[col], errors="raise")
    if "discharge_disposition_id" in raw.columns:
        raw["discharge_disposition_id"] = pd.to_numeric(raw["discharge_disposition_id"], errors="coerce")
    if "A1Cresult" not in raw.columns and "X2" in raw.columns:
        raw = raw.rename(columns={"X2": "A1Cresult", "X1": "max_glu_serum"})
    # After rename, medication columns use public names and glucose/HbA1c use UCI names.
    if "max_glu_serum" not in raw.columns and "X1" in raw.columns:
        raw = raw.rename(columns={"X1": "max_glu_serum", "X2": "A1Cresult"})
    raw = _standardise_demographics(raw)
    for col in ["diag_1", "diag_2", "diag_3", "insulin", "A1Cresult", "change", "diabetesMed"]:
        if col not in raw.columns:
            raw[col] = pd.NA
    for _code, column, _label in MEDICATIONS:
        if column not in raw.columns:
            raw[column] = "No"
    meta["expired_hospice_excluded"] = 0
    meta["has_discharge"] = "discharge_disposition_id" in raw.columns
    meta["has_dates"] = any(col in raw.columns for col in ("admission_date", "discharge_date"))
    meta["has_cost"] = any("cost" in col.lower() for col in raw.columns)
    meta["has_satisfaction"] = any("satisf" in col.lower() for col in raw.columns)
    return _finalize(raw, meta)


def load() -> tuple[pd.DataFrame, dict]:
    return load_kaggle(ensure_kaggle_csv())


def cohort_summary(df: pd.DataFrame, meta: dict) -> str:
    buf = io.StringIO()
    print(f"source={meta['source_kind']} rows={meta['analysis_rows']} rate={meta['readmission_rate']:.4f}", file=buf)
    return buf.getvalue()
