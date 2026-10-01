# Hospital readmission analysis

This project answers the hospital administration case study from the Kaggle file only:

[Hospital Administration Data](https://www.kaggle.com/datasets/shivavashishtha/hospital-administration-data/)

The archive contains `HA Data.csv` (66,587 rows, 49 columns). The pipeline downloads that file, cleans it the way the solution guide specifies, and writes a workbook plus a short results note. It does not use any other clinical database.

## Run

```bash
python -m pip install -r requirements.txt
python -m hospital_readmission
pytest
```

Outputs:

- `outputs/Hospital_Readmission_Analysis.xlsx`
- `outputs/RESULTS.md`

The CSV is saved at `data/Hospital_Administration_Database.csv` after the first download. If that file is already present, it is reused.

## Cleaning

Applied to this file only:

1. Read every field as text so the value `None` in `X1` and `X2` stays the text "test not performed". A default reader turns that word into a blank.
2. Drop the source `index` column.
3. Drop 17,676 rows that are identical on every column. The first copy is kept. 48,911 encounters remain, from 39,650 patients.
4. Drop `diag_4` because it is an exact copy of `diag_3`.
5. Drop `diag_5` because it holds decimals, not diagnosis codes.
6. Recode `?` in race to Unknown, in weight and specialty to Not recorded, and `Unknown/Invalid` gender to Unknown.
7. Map `X3` to `X25` with the medication names in the solution-guide appendix. Confirm those names with the data owner before clinical use.
8. Keep `readmitted` as provided: 1 means readmitted within 30 days.

## What the file cannot answer

There is no admission date, discharge date, discharge disposition, cost, satisfaction score, death indicator, or socioeconomic field. M01 is a sequence proxy only. M03, M06 and M10 are left unanswered rather than filled with invented columns. A03 and A05 use yellow assumption cells.

## Model

The risk score is an unpenalized logistic regression on the 13 admission-time variables named in the solution guide. The holdout is 30% of patients (`random_state` 0), so no patient is in both train and test. Tier labels use 5-fold out-of-fold scores. A gradient-boosting model is reported only as the benchmark in the guide. Race and gender are not score inputs.

## Checks

`python -m hospital_readmission` stops if the cleaned file is not 48,911 encounters, 22,609 readmissions and 39,650 patients, or if train and test patients overlap. `pytest` checks the same reconciliation, the published `[70-80)` counts, and that `None` in `X2` is not treated as a measured HbA1c.
