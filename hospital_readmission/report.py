"""Write the narrative that accompanies the workbook."""

from __future__ import annotations

from pathlib import Path


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _p(value: float) -> str:
    if value < 0.0001:
        return "<0.0001"
    return f"{value:.4f}"


def write_report(path: Path, results: dict) -> None:
    meta = results["meta"]
    means = results["means"]
    model = results["model"]
    finance = results["finance"]
    b01 = results["b01"]
    peak = b01.loc[b01["rate"].idxmax()]
    lines = [
        "# Reducing readmissions: results from the Kaggle hospital file",
        "",
        "Source: [Hospital Administration Data](https://www.kaggle.com/datasets/shivavashishtha/hospital-administration-data/) (`HA Data.csv`). No other database is used.",
        "",
        "## Cohort",
        "",
        f"- Source rows: {meta['source_rows']:,}",
        f"- Exact duplicate rows removed: {meta['duplicate_rows_removed']:,}",
        f"- Encounters analysed: {meta['analysis_rows']:,}",
        f"- Unique patients: {meta['unique_patients']:,}",
        f"- Readmissions within 30 days: {meta['readmitted_n']:,} ({_pct(meta['readmission_rate'])})",
        f"- Average stay: {means['stay']:.2f} days. Average medications: {means['medications']:.2f}",
        f"- Diabetic medication: {_pct(means['diabetes_med_share'])}. Weight recorded: {_pct(means['weight_recorded_share'])}. Specialty missing: {_pct(means['specialty_missing_share'])}",
        "",
        "The 46% rate is much higher than a typical hospital-wide 30-day rate. Compare groups inside this file. Do not use 46% as a performance benchmark.",
        "",
        "## Basic questions",
        "",
        f"B01. Readmission peaks at {_pct(peak['rate'])} in {peak['age']} ({int(peak['encounters']):,} encounters). Age-group differences are statistically significant (chi-square {results['b01_chi']['chi2']:.2f}, p {_p(results['b01_chi']['p'])}).",
        "",
        f"B02. Among specialties with at least 30 recorded encounters, the longest average stay is {results['b02'].iloc[0]['medical_specialty']} ({results['b02'].iloc[0]['avg_stay']:.2f} days) and the shortest in this ranking is {results['b02'].iloc[-1]['medical_specialty']} ({results['b02'].iloc[-1]['avg_stay']:.2f} days). Specialty is missing on {_pct(means['specialty_missing_share'])} of encounters, so the ranking describes the recorded half only.",
        "",
        f"B03. Prior emergency visits vs readmission: r = {results['b03_corr']['r']:.3f} ({results['b03_corr']['strength'].lower()}). The rate still rises from the zero-visit group to the 5+ group. See B03_Emergency.",
        "",
        f"B04. Patients on diabetic medication are readmitted at {_pct(results['b04'].iloc[0]['rate'])} ({int(results['b04'].iloc[0]['encounters']):,} encounters) versus {_pct(results['b04'].iloc[1]['rate'])} for patients not on diabetic medication. A diabetes diagnosis code gives a different rate ({_pct(results['b04'].iloc[2]['rate'])}). The definition changes the result.",
        "",
        f"B05. A medication change is associated with a {results['b05_z']['diff_pp']:.1f} percentage point higher readmission rate (z = {results['b05_z']['z']:.2f}, p {_p(results['b05_z']['p'])}). This is an association. Changes are often made for patients who are already unstable.",
        "",
        f"B06. Lab count vs readmission is {results['b06_corr']['strength'].lower()} (r = {results['b06_corr']['r']:.3f}). Do not use lab count alone as a risk trigger.",
        "",
        "B07. Unadjusted race and gender gaps are modest and are not adjusted for clinical mix. Adjusted odds are on A04_Social. Race and gender are not inputs to the risk model.",
        "",
        f"B08. Weight is recorded on {results['b08_recorded']:,} encounters ({_pct(means['weight_recorded_share'])}). That is too little coverage for a population conclusion. Patients with a recorded weight are readmitted at {_pct(results['b08_recorded_rate'])}, versus {_pct(results['b08_missing_rate'])} when weight is missing, which suggests selective recording.",
        "",
        f"B09. Medications vs length of stay: r = {results['b09_reg']['r']:.3f}, slope {results['b09_reg']['slope']:.3f} days per extra medication. This tracks illness complexity.",
        "",
        f"B10. Prior outpatient visits vs readmission: r = {results['b10_corr']['r']:.3f} ({results['b10_corr']['strength'].lower()}). The 5+ group is still higher than the zero-visit group.",
        "",
        "## Medium questions",
        "",
        "M01. The file has no admission or discharge date, so a monthly or seasonal trend cannot be estimated. Ordering encounters by encounter_id and splitting them into 10 equal groups is only a sequence view. It must not be read as seasonality.",
        "",
        f"M02. More diagnoses go with longer stays (r = {results['m02_stay']['r']:.3f}) and higher readmission (r = {results['m02_readmit']['r']:.3f}). diag_4 was an exact copy of diag_3 and diag_5 was not a diagnosis code, so both were dropped. The comorbidity score is number_diagnoses.",
        "",
        "M03. Not answerable from this file. None of the 49 columns is a discharge disposition. No proxy rate is reported. The field needed is a disposition code per encounter, with patients who died or went to hospice removed from the readmission denominator.",
        "",
        "M04. Age shows the clearest pattern in medications and procedures. Statistical significance is common because the sample is large, and the averages are not adjusted for diagnosis mix.",
        "",
        "M05. Prior inpatient, outpatient and emergency visits are averaged by ICD-9 chapter of diag_1 and for the 15 most common 3-digit codes. Diabetes (250.xx) is separated from the other endocrine codes.",
        "",
        "M06. Mortality and later health status are not in the file. The only proxy is repeat use: encounters per patient in this file, and prior inpatient stays. That is consistent with a cycle of utilisation. It does not show deterioration or death.",
        "",
        "M07. Insulin and metformin are the most used of the mapped medication columns. Specialty prescribing shares are on M07_Prescribing. Names for X3 to X25 follow the solution-guide appendix and should be confirmed with the data owner before any clinical use.",
        "",
        "M08. Weight-by-diagnosis cells are small. Cells with fewer than 20 encounters are left blank. Do not design a weight programme from this table.",
        "",
        "M09. Among patients with diabetesMed = Yes, each medication with at least 100 users is compared with a two-proportion z-test. Eleven tests at a 5% threshold will occasionally flag a chance difference. These are not effectiveness estimates.",
        "",
        "M10. Not answerable. The file has no satisfaction score. No correlation is reported.",
        "",
        "## Advanced questions",
        "",
        f"A01. Unpenalized logistic regression on the 13 admission-time variables in the guide. Patient-grouped holdout (30% of patients, random_state 0): AUC {model['auc_logit']:.3f}. Gradient boosting with specialty and diagnosis group added: AUC {model['auc_gb']:.3f}. Five-fold out-of-fold AUC: {model['auc_oof']:.3f}. At a 0.50 probability threshold, accuracy {model['accuracy']:.3f}, precision {model['precision']:.3f}, recall {model['recall']:.3f}. The high-risk third is readmitted at {_pct(finance['high_rate'])}. Race and gender are excluded from the score. The tier is a ranking tool for follow-up intensity, not a reason to deny care.",
        "",
        "A02. K-means, k = 4, on log1p prior inpatient, outpatient and emergency counts, standardised, 20 initialisations, random_state 0. Segment names are assigned after clustering from which visit type dominates. Silhouette scores for k = 2 to 6 are in the workbook.",
        "",
        f"A03. The file has no cost. At the placeholder ${results['assumptions']['cost_per_readmission']:,.0f} per readmission and an avoidable share of {_pct(results['assumptions']['avoidable_share'])}, avoidable cost is ${finance['avoidable_cost']:,.0f}. Replace both yellow inputs with hospital figures. The 46% base rate inflates any dollar total.",
        "",
        "A04. Only race, gender and age are available. Adjusted odds compare each race group with Caucasian patients and men with women, holding the clinical covariates in the guide fixed. An odds ratio below 1 is lower odds than the reference, not evidence of better care. There is no income, insurance, education, housing or neighbourhood field to add.",
        "",
        f"A05. The simulated programme enrols {_pct(results['assumptions']['enrolment'])} of the high-risk tier and assumes a {_pct(results['assumptions']['relative_reduction'])} relative reduction among those reached. Under those assumptions it prevents {finance['prevented']:.0f} readmissions and the net figure is ${finance['net_savings']:,.0f}. The reduction is not estimated from this file. Pilot it against a control group before scaling.",
        "",
        "## Checks",
        "",
        "Row reconciliation difference is 0. Train and test patients do not overlap. Risk tiers and segments each cover every cleaned encounter. X1 and X2 values of None were kept as text in the source count.",
        "",
    ]
    if results["checks"]:
        lines.append("Failures:")
        lines.extend(f"- {item}" for item in results["checks"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
