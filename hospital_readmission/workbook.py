"""Excel workbook. Rate tables are formulas on the Clean_Data sheet."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CLEAN_COLUMNS = [
    "encounter_id",
    "patient_id",
    "race",
    "gender",
    "age",
    "weight",
    "time_in_hospital",
    "medical_specialty",
    "num_lab_procedures",
    "num_procedures",
    "num_medications",
    "number_outpatient",
    "number_emergency",
    "number_inpatient",
    "number_diagnoses",
    "diag_1_group",
    "diag_1_code3",
    "change",
    "diabetesMed",
    "readmitted",
    "insulin_status",
    "hba1c_measured",
    "diabetes_dx",
    "metformin_used",
    "insulin_used",
    "risk_tier",
    "segment",
    "seq_decile",
    "lab_band",
    "med_band",
    "ed_band",
    "op_band",
    "dx_band",
    "oof_score",
]


def _col(index: int) -> str:
    letters = ""
    n = index + 1
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


CLEAN_LETTER = {name: _col(i) for i, name in enumerate(CLEAN_COLUMNS)}


def write_workbook(path: Path, results: dict) -> None:
    import xlsxwriter

    df = results["df"]
    last = len(df) + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = xlsxwriter.Workbook(str(path), {"constant_memory": False})
    title = wb.add_format({"bold": True, "font_size": 14})
    header = wb.add_format({"bold": True, "bg_color": "#1F4E79", "font_color": "white", "text_wrap": True})
    pct = wb.add_format({"num_format": "0.0%"})
    num = wb.add_format({"num_format": "#,##0"})
    dec = wb.add_format({"num_format": "0.000"})
    yellow = wb.add_format({"bg_color": "#FFF2CC", "border": 1, "num_format": "0.0%"})
    yellow_num = wb.add_format({"bg_color": "#FFF2CC", "border": 1, "num_format": "$#,##0"})
    money = wb.add_format({"num_format": "$#,##0"})
    wrap = wb.add_format({"text_wrap": True, "valign": "top"})
    label = wb.add_format({"bold": True})

    _clean_sheet(wb, df, header, num, dec)
    _index(wb, title, wrap)
    _summary(wb, results, title, header, pct, num, wrap)
    _quality(wb, results, title, header, num, last)
    _dictionary(wb, title, header, wrap)
    _limitations(wb, results, title, wrap)
    _rate_sheet(
        wb, "B01_Age", "B01. Readmission by age group",
        "Age group", "age", list(results["b01"]["age"]),
        last, title, header, pct, num, results["b01_chi"],
    )
    _specialty_sheet(wb, results, title, header, num, dec, last)
    _rate_sheet(
        wb, "B03_Emergency", "B03. Prior emergency visits vs readmission",
        "Emergency visits", "ed_band", list(results["b03"]["ed_band"]),
        last, title, header, pct, num, None, results["b03_corr"],
    )
    _b04_sheet(wb, results, title, header, pct, num, last)
    _b05_sheet(wb, results, title, header, pct, num, dec, last)
    _rate_sheet(
        wb, "B06_Labs", "B06. Lab procedures vs readmission",
        "Lab band", "lab_band", list(results["b06"]["lab_band"]),
        last, title, header, pct, num, None, results["b06_corr"],
    )
    _b07_sheet(wb, results, title, header, pct, num, last)
    _b08_sheet(wb, results, title, header, pct, num)
    _b09_sheet(wb, results, title, header, num, dec, last)
    _rate_sheet(
        wb, "B10_Outpatient", "B10. Prior outpatient visits vs readmission",
        "Outpatient visits", "op_band", list(results["b10"]["op_band"]),
        last, title, header, pct, num, None, results["b10_corr"],
    )
    _rate_sheet(
        wb, "M01_Sequence", "M01. Sequence proxy, not a calendar trend",
        "Sequence decile", "seq_decile", list(results["m01"]["seq_decile"]),
        last, title, header, pct, num, results["m01_chi"],
    )
    _value_sheet(wb, "M02_Comorbidity", "M02. Diagnoses, stay and readmission", results["m02"], title, header, pct)
    _m03_sheet(wb, results, title, header, pct, wrap)
    _value_sheet(wb, "M04_Demographics", "M04. Demographics vs interventions", results["m04_age"], title, header, pct)
    _value_sheet(wb, "M05_Diagnosis", "M05. Prior visits by primary diagnosis group", results["m05"], title, header, pct)
    _value_sheet(wb, "M06_Outcomes", "M06. Repeat utilisation proxy", results["m06_ip"], title, header, pct)
    _value_sheet(wb, "M07_Prescribing", "M07. Medication use and readmission", results["m07_meds"], title, header, pct)
    _value_sheet(wb, "M08_Weight_Dx", "M08. Weight group by diagnosis (n<20 suppressed in Python)", results["m08"], title, header, pct)
    _value_sheet(wb, "M09_Diabetes_Meds", "M09. Diabetic patients, medication vs readmission", results["m09"], title, header, pct)
    _m10_sheet(wb, title, wrap)
    _model_sheet(wb, results, title, header, pct, num, dec, yellow, wrap)
    _segment_sheet(wb, results, title, header, pct, num)
    _finance_sheet(wb, results, title, header, pct, num, money, yellow, yellow_num, label)
    _a04_sheet(wb, results, title, header, dec)
    _a05_sheet(wb, results, title, header, pct, num, money, yellow, yellow_num, label, wrap)
    wb.close()


def _clean_sheet(wb, df, header, num, dec):
    ws = wb.add_worksheet("Clean_Data")
    for col, name in enumerate(CLEAN_COLUMNS):
        ws.write(0, col, name, header)
    frame = df[CLEAN_COLUMNS]
    for r, row in enumerate(frame.itertuples(index=False), start=1):
        for c, value in enumerate(row):
            if value is None or (not isinstance(value, str) and pd.isna(value)):
                ws.write_blank(r, c, None)
                continue
            if hasattr(value, "item") and not isinstance(value, str):
                value = value.item()
            if isinstance(value, float):
                ws.write_number(r, c, value, dec if CLEAN_COLUMNS[c] == "oof_score" else None)
            elif isinstance(value, int):
                ws.write_number(r, c, value)
            else:
                ws.write(r, c, str(value))
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, len(df), len(CLEAN_COLUMNS) - 1)
    ws.set_column(0, len(CLEAN_COLUMNS) - 1, 16)


def _index(wb, title, wrap):
    ws = wb.add_worksheet("Index")
    ws.write(0, 0, "Hospital readmission workbook", title)
    ws.write(1, 0, "Every rate table that names a Clean_Data column is a live COUNTIFS or AVERAGEIFS formula.")
    ws.write(3, 0, "Source file: Kaggle Hospital Administration Data, HA Data.csv. No other database is used.")
    lines = [
        "Executive_Summary",
        "Data_Quality",
        "Data_Dictionary",
        "Limitations",
        "B01_Age to B10_Outpatient",
        "M01_Sequence to M10_Satisfaction",
        "A01_Risk_Model",
        "A02_Segments",
        "A03_Financial",
        "A04_Social",
        "A05_Followup",
        "Clean_Data",
    ]
    for i, line in enumerate(lines):
        ws.write(5 + i, 0, line, wrap)
    ws.set_column(0, 0, 80)


def _summary(wb, results, title, header, pct, num, wrap):
    ws = wb.add_worksheet("Executive_Summary")
    meta = results["meta"]
    means = results["means"]
    ws.write(0, 0, "Executive summary", title)
    rows = [
        ("Encounters analysed", meta["analysis_rows"]),
        ("Unique patients", meta["unique_patients"]),
        ("30-day readmissions", meta["readmitted_n"]),
        ("30-day readmission rate", meta["readmission_rate"]),
        ("Average length of stay (days)", means["stay"]),
        ("Average medications", means["medications"]),
        ("Share on diabetic medication", means["diabetes_med_share"]),
        ("Weight recorded", means["weight_recorded_share"]),
        ("Specialty recorded", 1 - means["specialty_missing_share"]),
    ]
    ws.write(2, 0, "Measure", header)
    ws.write(2, 1, "Value", header)
    for i, (name, value) in enumerate(rows, start=3):
        ws.write(i, 0, name)
        fmt = pct if "rate" in name.lower() or name.startswith("Share") or name.startswith("Weight") or name.startswith("Specialty") else num
        ws.write_number(i, 1, value, fmt)
    ws.write(14, 0, "Findings and limits are on the question sheets. M01, M03, M06, M10 and the dollar figures in A03 use only fields this file contains.", wrap)
    ws.set_column(0, 0, 42)
    ws.set_column(1, 1, 18)


def _quality(wb, results, title, header, num, last):
    ws = wb.add_worksheet("Data_Quality")
    meta = results["meta"]
    ws.write(0, 0, "Cleaning log", title)
    ws.write(2, 0, "Step", header)
    ws.write(2, 1, "Rows", header)
    ws.write(2, 2, "Detail", header)
    steps = [
        ("Rows in source file", meta["source_rows"], "HA Data.csv from the Kaggle dataset, 49 columns"),
        ("Exact duplicate rows removed", meta["duplicate_rows_removed"], "Identical on every column, including encounter_id"),
        ("Rows after de-duplication", meta["analysis_rows"], "Source rows minus duplicates"),
        ("Rows in Clean_Data", f"=COUNTA(Clean_Data!A2:A{last})", "Must equal the line above"),
        ("Readmissions in Clean_Data", f"=SUM(Clean_Data!T2:T{last})", "readmitted = 1"),
        ("Unique patients", meta["unique_patients"], "Repeat encounters are kept as separate events"),
        ("X1 text None in source", meta["x1_none"], "Kept as text, not converted to blank"),
        ("X2 text None in source", meta["x2_none"], "Kept as text, not converted to blank"),
    ]
    for i, (name, value, detail) in enumerate(steps, start=3):
        ws.write(i, 0, name)
        if isinstance(value, str):
            ws.write_formula(i, 1, value, num)
        else:
            ws.write_number(i, 1, value, num)
        ws.write(i, 2, detail)
    ws.write_formula(12, 1, "=B6-B7", num)
    ws.write(12, 0, "Reconciliation difference (must be 0)")
    ws.set_column(0, 0, 42)
    ws.set_column(1, 1, 16)
    ws.set_column(2, 2, 70)


def _dictionary(wb, title, header, wrap):
    ws = wb.add_worksheet("Data_Dictionary")
    ws.write(0, 0, "Fields used from the Kaggle file", title)
    ws.write(2, 0, "Field", header)
    ws.write(2, 1, "Meaning", header)
    rows = [
        ("encounter_id", "Encounter identifier"),
        ("patient_id", "Patient identifier"),
        ("race, gender, age, weight", "Demographics. ? recoded to Unknown or Not recorded"),
        ("time_in_hospital", "Length of stay in days"),
        ("medical_specialty", "Admitting specialty. ? recoded to Not recorded"),
        ("num_lab_procedures, num_procedures, num_medications", "Utilisation during the stay"),
        ("number_outpatient, number_emergency, number_inpatient", "Visits in the prior year"),
        ("diag_1 to diag_3", "Diagnosis codes. diag_4 duplicated diag_3 and was dropped. diag_5 was not a diagnosis code and was dropped"),
        ("X1", "Max glucose serum. The text None means the test was not performed"),
        ("X2", "HbA1c result. The text None means the test was not performed"),
        ("X3 to X25", "Medication indicators, mapped with the guide appendix"),
        ("change", "Ch = diabetic medication changed, No = not changed"),
        ("diabetesMed", "Yes if any diabetic medication was prescribed"),
        ("readmitted", "1 = readmitted within 30 days, 0 otherwise"),
    ]
    for i, (field, meaning) in enumerate(rows, start=3):
        ws.write(i, 0, field)
        ws.write(i, 1, meaning, wrap)
    ws.set_column(0, 0, 62)
    ws.set_column(1, 1, 90)


def _limitations(wb, results, title, wrap):
    ws = wb.add_worksheet("Limitations")
    ws.write(0, 0, "Limits of this file", title)
    notes = [
        "The file has no admission date, discharge date, discharge disposition, cost, satisfaction, mortality, or socioeconomic fields.",
        "M01 uses encounter_id order only. That is not a month or a season.",
        "M03, M06 and M10 are not answered with invented fields. The sheet states the gap.",
        "A03 and A05 dollar results are scenarios. Yellow cells are assumptions, not measurements.",
        "Weight is missing for most encounters. Specialty is missing for about half.",
        "X1 and X2 use the text None for a test that was not performed. The loader keeps that text. A default CSV reader would turn it into a blank and those rows could not be counted.",
        "Patients can have more than one encounter, so ordinary standard errors are slightly too small.",
        "Associations are not effects. A medication change can mark a sicker patient.",
        "The 46% readmission rate is far above a typical hospital rate. Use the file to compare groups, not as a benchmark.",
        "The logistic model is unpenalized, fit with the 13 admission-time variables in the guide. Race and gender are not model inputs. Scores used for tiers are out of fold.",
        "The gradient-boosting benchmark adds specialty and diagnosis group. It is a comparison, not a second production model.",
        "K-means uses log1p of the three prior-visit counts, standardised, k=4, 20 initialisations, random_state 0.",
    ]
    for i, note in enumerate(notes):
        ws.write(2 + i, 0, note, wrap)
        ws.set_row(2 + i, 32)
    ws.set_column(0, 0, 120)


def _rate_formulas(ws, header_row, labels, data_col, last, header, pct, num):
    letter = CLEAN_LETTER[data_col]
    target = CLEAN_LETTER["readmitted"]
    ws.write(header_row, 0, "Group", header)
    ws.write(header_row, 1, "Encounters", header)
    ws.write(header_row, 2, "Readmitted <30d", header)
    ws.write(header_row, 3, "Readmission rate", header)
    for i, label in enumerate(labels):
        row = header_row + 1 + i
        excel = row + 1
        if hasattr(label, "item") and not isinstance(label, (str, bytes)):
            label = label.item()
        ws.write(row, 0, label)
        ws.write_formula(row, 1, f'=COUNTIFS(Clean_Data!${letter}$2:${letter}${last},A{excel})', num)
        ws.write_formula(
            row,
            2,
            f'=COUNTIFS(Clean_Data!${letter}$2:${letter}${last},A{excel},Clean_Data!${target}$2:${target}${last},1)',
            num,
        )
        ws.write_formula(row, 3, f'=IF(B{excel}=0,"",C{excel}/B{excel})', pct)
    total = header_row + 1 + len(labels)
    excel = total + 1
    first = header_row + 2
    ws.write(total, 0, "All encounters")
    ws.write_formula(total, 1, f"=SUM(B{first}:B{excel-1})", num)
    ws.write_formula(total, 2, f"=SUM(C{first}:C{excel-1})", num)
    ws.write_formula(total, 3, f"=C{excel}/B{excel}", pct)
    return total


def _rate_sheet(wb, name, heading, group_name, column, labels, last, title, header, pct, num, chi=None, corr=None):
    ws = wb.add_worksheet(name)
    ws.write(0, 0, heading, title)
    ws.write(2, 0, group_name)
    end = _rate_formulas(ws, 3, labels, column, last, header, pct, num)
    row = end + 2
    if chi:
        ws.write(row, 0, "Chi-square")
        ws.write(row, 1, chi["chi2"])
        ws.write(row + 1, 0, "Degrees of freedom")
        ws.write(row + 1, 1, chi["dof"])
        ws.write(row + 2, 0, "p-value")
        ws.write(row + 2, 1, chi["p"])
        row += 4
    if corr:
        ws.write(row, 0, "Pearson r")
        ws.write(row, 1, corr["r"])
        ws.write(row + 1, 0, "p-value")
        ws.write(row + 1, 1, corr["p"])
        ws.write(row + 2, 0, "Strength")
        ws.write(row + 2, 1, corr["strength"])
    ws.set_column(0, 0, 28)
    ws.set_column(1, 3, 20)


def _specialty_sheet(wb, results, title, header, num, dec, last):
    ws = wb.add_worksheet("B02_Specialty")
    ws.write(0, 0, "B02. Average length of stay by specialty (n at least 30)", title)
    letter = CLEAN_LETTER["medical_specialty"]
    stay = CLEAN_LETTER["time_in_hospital"]
    ws.write(2, 0, "Medical specialty", header)
    ws.write(2, 1, "Encounters", header)
    ws.write(2, 2, "Avg length of stay", header)
    for i, specialty in enumerate(results["b02"]["medical_specialty"]):
        row = 3 + i
        excel = row + 1
        ws.write(row, 0, specialty)
        ws.write_formula(row, 1, f'=COUNTIFS(Clean_Data!${letter}$2:${letter}${last},A{excel})', num)
        ws.write_formula(row, 2, f'=AVERAGEIFS(Clean_Data!${stay}$2:${stay}${last},Clean_Data!${letter}$2:${letter}${last},A{excel})', dec)
    ws.set_column(0, 0, 42)
    ws.set_column(1, 2, 22)


def _b04_sheet(wb, results, title, header, pct, num, last):
    ws = wb.add_worksheet("B04_Diabetes")
    ws.write(0, 0, "B04. Readmission among patients with diabetes", title)
    med = CLEAN_LETTER["diabetesMed"]
    dx = CLEAN_LETTER["diabetes_dx"]
    target = CLEAN_LETTER["readmitted"]
    ws.write(2, 0, "Cohort", header)
    ws.write(2, 1, "Encounters", header)
    ws.write(2, 2, "Readmitted", header)
    ws.write(2, 3, "Rate", header)
    specs = [
        ("On diabetic medication", f'COUNTIFS(Clean_Data!${med}$2:${med}${last},"Yes")', f'COUNTIFS(Clean_Data!${med}$2:${med}${last},"Yes",Clean_Data!${target}$2:${target}${last},1)'),
        ("Not on diabetic medication", f'COUNTIFS(Clean_Data!${med}$2:${med}${last},"No")', f'COUNTIFS(Clean_Data!${med}$2:${med}${last},"No",Clean_Data!${target}$2:${target}${last},1)'),
        ("Diabetes code 250 in diag_1-3", f'COUNTIFS(Clean_Data!${dx}$2:${dx}${last},1)', f'COUNTIFS(Clean_Data!${dx}$2:${dx}${last},1,Clean_Data!${target}$2:${target}${last},1)'),
        ("No diabetes code", f'COUNTIFS(Clean_Data!${dx}$2:${dx}${last},0)', f'COUNTIFS(Clean_Data!${dx}$2:${dx}${last},0,Clean_Data!${target}$2:${target}${last},1)'),
    ]
    for i, (name, n_formula, k_formula) in enumerate(specs):
        row = 3 + i
        excel = row + 1
        ws.write(row, 0, name)
        ws.write_formula(row, 1, "=" + n_formula, num)
        ws.write_formula(row, 2, "=" + k_formula, num)
        ws.write_formula(row, 3, f"=C{excel}/B{excel}", pct)
    ws.set_column(0, 0, 36)
    ws.set_column(1, 3, 16)


def _b05_sheet(wb, results, title, header, pct, num, dec, last):
    ws = wb.add_worksheet("B05_Med_Change")
    ws.write(0, 0, "B05. Diabetic medication change vs readmission", title)
    _rate_formulas(ws, 2, ["Ch", "No"], "change", last, header, pct, num)
    z = results["b05_z"]
    ws.write(8, 0, "Difference in rate", header)
    ws.write_number(8, 1, z["diff"], pct)
    ws.write(9, 0, "z statistic")
    ws.write_number(9, 1, z["z"], dec)
    ws.write(10, 0, "p-value")
    ws.write_number(10, 1, z["p"], dec)
    ws.write(11, 0, "95% CI low (percentage points)")
    ws.write_number(11, 1, z["ci_low_pp"], dec)
    ws.write(12, 0, "95% CI high (percentage points)")
    ws.write_number(12, 1, z["ci_high_pp"], dec)
    ws.set_column(0, 0, 40)


def _b07_sheet(wb, results, title, header, pct, num, last):
    ws = wb.add_worksheet("B07_Race_Gender")
    ws.write(0, 0, "B07. Readmission by race and by gender", title)
    _rate_formulas(ws, 2, list(results["b07_race"]["race"]), "race", last, header, pct, num)
    start = 4 + len(results["b07_race"]) + 2
    ws.write(start, 0, "Gender")
    _rate_formulas(ws, start + 1, list(results["b07_gender"]["gender"]), "gender", last, header, pct, num)
    ws.set_column(0, 0, 24)


def _b08_sheet(wb, results, title, header, pct, num):
    ws = wb.add_worksheet("B08_Weight")
    ws.write(0, 0, "B08. Weight is recorded for too few encounters to support a population conclusion", title)
    ws.write(2, 0, "Weight recorded", header)
    ws.write_number(2, 1, results["b08_recorded"], num)
    ws.write(3, 0, "Share recorded", header)
    ws.write_number(3, 1, results["means"]["weight_recorded_share"], pct)
    ws.write(5, 0, "Category", header)
    ws.write(5, 1, "Encounters", header)
    ws.write(5, 2, "Readmitted", header)
    ws.write(5, 3, "Rate", header)
    ws.write(5, 4, "Flag", header)
    for i, row in results["b08"].iterrows():
        ws.write(6 + i, 0, row["weight"])
        ws.write_number(6 + i, 1, int(row["encounters"]), num)
        ws.write_number(6 + i, 2, int(row["readmitted"]), num)
        ws.write_number(6 + i, 3, float(row["rate"]), pct)
        ws.write(6 + i, 4, row["flag"])
    ws.set_column(0, 0, 28)
    ws.set_column(4, 4, 36)


def _b09_sheet(wb, results, title, header, num, dec, last):
    ws = wb.add_worksheet("B09_Medications_Stay")
    ws.write(0, 0, "B09. Medications vs length of stay", title)
    letter = CLEAN_LETTER["med_band"]
    stay = CLEAN_LETTER["time_in_hospital"]
    ws.write(2, 0, "Medications band", header)
    ws.write(2, 1, "Encounters", header)
    ws.write(2, 2, "Avg stay", header)
    for i, band in enumerate(results["b09"]["med_band"]):
        row = 3 + i
        excel = row + 1
        ws.write(row, 0, band)
        ws.write_formula(row, 1, f'=COUNTIFS(Clean_Data!${letter}$2:${letter}${last},A{excel})', num)
        ws.write_formula(row, 2, f'=AVERAGEIFS(Clean_Data!${stay}$2:${stay}${last},Clean_Data!${letter}$2:${letter}${last},A{excel})', dec)
    reg = results["b09_reg"]
    ws.write(9, 0, "Pearson r")
    ws.write_number(9, 1, reg["r"], dec)
    ws.write(10, 0, "R-squared")
    ws.write_number(10, 1, reg["r2"], dec)
    ws.write(11, 0, "Slope, days per extra medication")
    ws.write_number(11, 1, reg["slope"], dec)
    ws.write(12, 0, "Intercept")
    ws.write_number(12, 1, reg["intercept"], dec)
    ws.set_column(0, 0, 40)


def _value_sheet(wb, name, heading, frame, title, header, pct):
    ws = wb.add_worksheet(name)
    ws.write(0, 0, heading, title)
    if frame is None or len(frame) == 0:
        ws.write(2, 0, "No table. See the note on this question in the report.")
        return
    for c, col in enumerate(frame.columns):
        ws.write(2, c, str(col), header)
    for r, row in enumerate(frame.itertuples(index=False), start=3):
        for c, value in enumerate(row):
            if pd.isna(value):
                ws.write_blank(r, c, None)
            elif isinstance(value, float):
                fmt = pct if "rate" in str(frame.columns[c]) else None
                ws.write_number(r, c, float(value), fmt)
            elif isinstance(value, (int,)):
                ws.write_number(r, c, int(value))
            else:
                ws.write(r, c, str(value))
    ws.set_column(0, max(len(frame.columns) - 1, 0), 22)


def _m03_sheet(wb, results, title, header, pct, wrap):
    ws = wb.add_worksheet("M03_Disposition")
    ws.write(0, 0, "M03. Discharge disposition", title)
    ws.write(2, 0, results["m03_note"], wrap)
    ws.set_row(2, 48)
    ws.set_column(0, 0, 100)
    if results["m03"] is not None and len(results["m03"]):
        _value_sheet_into(ws, results["m03"], header, pct, start=4)


def _value_sheet_into(ws, frame, header, pct, start):
    for c, col in enumerate(frame.columns):
        ws.write(start, c, str(col), header)
    for r, row in enumerate(frame.itertuples(index=False), start=start + 1):
        for c, value in enumerate(row):
            if isinstance(value, float):
                ws.write_number(r, c, float(value), pct if "rate" in str(frame.columns[c]) else None)
            else:
                ws.write(r, c, value if not isinstance(value, (int, float)) else value)


def _m10_sheet(wb, title, wrap):
    ws = wb.add_worksheet("M10_Satisfaction")
    ws.write(0, 0, "M10. Patient satisfaction", title)
    ws.write(2, 0, "Not answerable. The Kaggle file has no satisfaction or survey column. No correlation is reported.", wrap)
    ws.set_column(0, 0, 100)


def _model_sheet(wb, results, title, header, pct, num, dec, yellow, wrap):
    ws = wb.add_worksheet("A01_Risk_Model")
    model = results["model"]
    ws.write(0, 0, "A01. Logistic regression risk model", title)
    ws.write(2, 0, "Held-out AUC, logistic regression")
    ws.write_number(2, 1, model["auc_logit"], dec)
    ws.write(3, 0, "Held-out AUC, gradient boosting benchmark")
    ws.write_number(3, 1, model["auc_gb"], dec)
    ws.write(4, 0, "5-fold out-of-fold AUC")
    ws.write_number(4, 1, model["auc_oof"], dec)
    ws.write(5, 0, "Accuracy at 0.50")
    ws.write_number(5, 1, model["accuracy"], dec)
    ws.write(6, 0, "Precision at 0.50")
    ws.write_number(6, 1, model["precision"], dec)
    ws.write(7, 0, "Recall at 0.50")
    ws.write_number(7, 1, model["recall"], dec)
    ws.write(8, 0, "Training encounters")
    ws.write_number(8, 1, model["train_rows"], num)
    ws.write(9, 0, "Test encounters")
    ws.write_number(9, 1, model["test_rows"], num)
    ws.write(11, 0, "Variable", header)
    ws.write(11, 1, "Coefficient", header)
    ws.write(11, 2, "Odds ratio", header)
    ws.write(11, 3, "Patient input", header)
    ws.write(11, 4, "Contribution", header)
    ws.write(12, 0, "Intercept")
    ws.write_number(12, 1, model["intercept"], dec)
    ws.write_formula(12, 4, "=B13")
    defaults = {
        "age_mid": 65,
        "time_in_hospital": 5,
        "num_lab_procedures": 45,
        "num_procedures": 1,
        "num_medications": 16,
        "number_outpatient": 0,
        "number_emergency": 1,
        "number_inpatient": 2,
        "number_diagnoses": 8,
        "diabetes_med_flag": 1,
        "change_flag": 0,
        "insulin_used": 1,
        "hba1c_measured": 0,
    }
    for i, coef in enumerate(model["coefficients"]):
        row = 13 + i
        excel = row + 1
        ws.write(row, 0, coef["variable"])
        ws.write_number(row, 1, coef["coefficient"], dec)
        ws.write_number(row, 2, coef["odds_ratio"], dec)
        ws.write_number(row, 3, defaults[coef["key"]], yellow)
        ws.write_formula(row, 4, f"=B{excel}*D{excel}", dec)
    last_excel = 13 + len(model["coefficients"]) + 1
    ws.write(last_excel - 1, 0, "Log-odds")
    ws.write_formula(last_excel - 1, 4, f"=SUM(E13:E{last_excel-1})", dec)
    ws.write(last_excel, 0, "Predicted probability")
    ws.write_formula(last_excel, 4, f"=1/(1+EXP(-E{last_excel}))", pct)
    ws.write(last_excel + 2, 0, "Medium tier starts at", wrap)
    ws.write_number(last_excel + 2, 1, model["threshold_medium"], pct)
    ws.write(last_excel + 3, 0, "High tier starts at")
    ws.write_number(last_excel + 3, 1, model["threshold_high"], pct)
    ws.write(last_excel + 5, 0, "Tier counts are out-of-fold terciles and are stored on Clean_Data.")
    tier_header = last_excel + 6
    _rate_formulas(ws, tier_header, ["High", "Medium", "Low"], "risk_tier", len(results["df"]) + 1, header, pct, num)
    ws.set_column(0, 0, 52)
    ws.set_column(1, 4, 18)


def _segment_sheet(wb, results, title, header, pct, num):
    ws = wb.add_worksheet("A02_Segments")
    ws.write(0, 0, "A02. K-means segments on prior inpatient, outpatient and emergency visits", title)
    _rate_formulas(
        ws, 2,
        ["Emergency-reliant", "Frequent inpatient", "Outpatient-engaged", "Low prior utilisation"],
        "segment", len(results["df"]) + 1, header, pct, num,
    )
    ws.write(10, 0, "Silhouette on an 8,000-row sample")
    for i, (k, score) in enumerate(results["segments"]["silhouette"].items()):
        ws.write(11 + i, 0, f"k={k}")
        ws.write_number(11 + i, 1, score)
    ws.set_column(0, 0, 28)


def _finance_sheet(wb, results, title, header, pct, num, money, yellow, yellow_num, label):
    ws = wb.add_worksheet("A03_Financial")
    ws.write(0, 0, "A03. Scenario cost of readmissions. Yellow cells are assumptions.", title)
    assumptions = results["assumptions"]
    ws.write(2, 0, "Average cost per 30-day readmission", label)
    ws.write_number(2, 1, assumptions["cost_per_readmission"], yellow_num)
    ws.write(3, 0, "Share potentially avoidable", label)
    ws.write_number(3, 1, assumptions["avoidable_share"], yellow)
    ws.write(5, 0, "Readmissions", label)
    ws.write_formula(5, 1, "=Data_Quality!B8", num)
    ws.write(6, 0, "Total readmission cost", label)
    ws.write_formula(6, 1, "=B6*B3", money)
    ws.write(7, 0, "Potentially avoidable readmissions", label)
    ws.write_formula(7, 1, "=B6*B4", num)
    ws.write(8, 0, "Avoidable cost", label)
    ws.write_formula(8, 1, "=B8*B3", money)
    ws.write(10, 0, "These dollars are not in the file. Replace the yellow cells with hospital finance figures.", label)
    ws.set_column(0, 0, 46)
    ws.set_column(1, 1, 18)


def _a04_sheet(wb, results, title, header, dec):
    ws = wb.add_worksheet("A04_Social")
    ws.write(0, 0, "A04. Adjusted odds. No income, insurance, housing or neighbourhood field exists.", title)
    frame = results["a04"]
    for c, col in enumerate(frame.columns):
        ws.write(2, c, col, header)
    for r, row in enumerate(frame.itertuples(index=False), start=3):
        for c, value in enumerate(row):
            if isinstance(value, float):
                ws.write_number(r, c, float(value), dec)
            else:
                ws.write(r, c, str(value))
    ws.set_column(0, 0, 36)


def _a05_sheet(wb, results, title, header, pct, num, money, yellow, yellow_num, label, wrap):
    ws = wb.add_worksheet("A05_Followup")
    ws.write(0, 0, "A05. Post-discharge programme simulation. The effect size is an assumption.", title)
    ws.write(2, 0, "Enrolment of the high-risk tier", label)
    ws.write_number(2, 1, results["assumptions"]["enrolment"], yellow)
    ws.write(3, 0, "Relative reduction among enrolled", label)
    ws.write_number(3, 1, results["assumptions"]["relative_reduction"], yellow)
    ws.write(4, 0, "Programme cost per enrolled patient", label)
    ws.write_number(4, 1, results["assumptions"]["programme_cost"], yellow_num)
    ws.write(5, 0, "Cost per readmission, from A03", label)
    ws.write_formula(5, 1, "=A03_Financial!B3", money)
    # High tier block starts at Excel row 4 on A01 after the rate header. Use Python counts so the
    # simulation does not depend on a circular formula layout, and show them as values.
    finance = results["finance"]
    ws.write(7, 0, "High-risk encounters", label)
    ws.write_number(7, 1, finance["high_encounters"], num)
    ws.write(8, 0, "High-risk readmissions", label)
    ws.write_number(8, 1, finance["high_readmissions"], num)
    ws.write(9, 0, "Patients enrolled", label)
    ws.write_formula(9, 1, "=B8*B3", num)
    ws.write(10, 0, "Readmissions among enrolled at baseline", label)
    ws.write_formula(10, 1, "=B9*B3", num)
    ws.write(11, 0, "Readmissions prevented", label)
    ws.write_formula(11, 1, "=B11*B4", num)
    ws.write(12, 0, "Gross savings", label)
    ws.write_formula(12, 1, "=B12*B6", money)
    ws.write(13, 0, "Programme cost", label)
    ws.write_formula(13, 1, "=B10*B5", money)
    ws.write(14, 0, "Net savings", label)
    ws.write_formula(14, 1, "=B13-B14", money)
    ws.write(16, 0, "Eligibility uses the risk tier and utilisation only. The reduction is not an effect estimated from this file.", wrap)
    ws.set_row(16, 32)
    ws.set_column(0, 0, 48)
    ws.set_column(1, 1, 18)
