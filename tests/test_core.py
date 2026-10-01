"""Checks that do not refit the full model."""

import pandas as pd

from hospital_readmission.prepare import age_midpoint, diag_group, load
from hospital_readmission.stats import chi_square, two_proportion


def test_age_midpoint_and_diagnosis_groups():
    assert age_midpoint("[70-80)") == 75
    assert age_midpoint("[0-10)") == 5
    assert diag_group("428") == "Circulatory"
    assert diag_group("250.83") == "Diabetes"
    assert diag_group("V57") == "External/Supplementary (V/E)"
    assert diag_group("?") == "Unknown"


def test_avoidable_cost_identity():
    readmissions = 22609
    assert round(readmissions * 0.27 * 15000) == 91566450


def test_two_proportion_and_chi_square():
    result = two_proportion(50, 100, 30, 100)
    assert result["diff"] == 0.2
    assert result["z"] > 0
    table = chi_square([(10, 10), (20, 5)])
    assert table["dof"] == 1
    assert table["p"] < 0.05


def test_kaggle_cleaning_matches_the_guide():
    df, meta = load()
    assert meta["source_kind"] == "kaggle"
    assert meta["source_rows"] == 66587
    assert meta["source_columns"] == 49
    assert meta["duplicate_rows_removed"] == 17676
    assert meta["analysis_rows"] == 48911
    assert meta["unique_patients"] == 39650
    assert meta["readmitted_n"] == 22609
    assert meta["x1_none"] > 0 and meta["x2_none"] > 0
    assert "diag_4" not in df.columns and "diag_5" not in df.columns
    assert "index" not in df.columns
    assert set(df["readmitted"].unique()) == {0, 1}
    assert df["patient_id"].nunique() == 39650
    # The published age table.
    age = df.groupby("age")["readmitted"].agg(["size", "sum"])
    assert int(age.loc["[70-80)", "size"]) == 12478
    assert int(age.loc["[70-80)", "sum"]) == 6019
    assert int((df["weight"] != "Not recorded").sum()) == 1557
    assert int((df["diabetesMed"] == "Yes").sum()) == 37640
    # None stayed text long enough to be counted, and is not a positive HbA1c.
    assert int(df["hba1c_measured"].sum()) < len(df)
    assert int(df.loc[df["A1Cresult"] == "None", "hba1c_measured"].sum()) == 0
