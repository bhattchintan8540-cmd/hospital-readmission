# Reducing readmissions: results from the Kaggle hospital file

Source: [Hospital Administration Data](https://www.kaggle.com/datasets/shivavashishtha/hospital-administration-data/) (`HA Data.csv`). No other database is used.

## Cohort

- Source rows: 66,587
- Exact duplicate rows removed: 17,676
- Encounters analysed: 48,911
- Unique patients: 39,650
- Readmissions within 30 days: 22,609 (46.2%)
- Average stay: 4.40 days. Average medications: 16.03
- Diabetic medication: 77.0%. Weight recorded: 3.2%. Specialty missing: 49.0%

The 46% rate is much higher than a typical hospital-wide 30-day rate. Compare groups inside this file. Do not use 46% as a performance benchmark.

## Basic questions

B01. Readmission peaks at 48.2% in [70-80) (12,478 encounters). Age-group differences are statistically significant (chi-square 113.39, p <0.0001).

B02. Among specialties with at least 30 recorded encounters, the longest average stay is PhysicalMedicineandRehabilitation (9.04 days) and the shortest in this ranking is Pediatrics-Endocrinology (2.61 days). Specialty is missing on 49.0% of encounters, so the ranking describes the recorded half only.

B03. Prior emergency visits vs readmission: r = 0.109 (weak). The rate still rises from the zero-visit group to the 5+ group. See B03_Emergency.

B04. Patients on diabetic medication are readmitted at 47.9% (37,640 encounters) versus 40.5% for patients not on diabetic medication. A diabetes diagnosis code gives a different rate (45.2%). The definition changes the result.

B05. A medication change is associated with a 4.6 percentage point higher readmission rate (z = 10.11, p <0.0001). This is an association. Changes are often made for patients who are already unstable.

B06. Lab count vs readmission is very weak (r = 0.037). Do not use lab count alone as a risk trigger.

B07. Unadjusted race and gender gaps are modest and are not adjusted for clinical mix. Adjusted odds are on A04_Social. Race and gender are not inputs to the risk model.

B08. Weight is recorded on 1,557 encounters (3.2%). That is too little coverage for a population conclusion. Patients with a recorded weight are readmitted at 57.5%, versus 45.9% when weight is missing, which suggests selective recording.

B09. Medications vs length of stay: r = 0.465, slope 0.171 days per extra medication. This tracks illness complexity.

B10. Prior outpatient visits vs readmission: r = 0.083 (very weak). The 5+ group is still higher than the zero-visit group.

## Medium questions

M01. The file has no admission or discharge date, so a monthly or seasonal trend cannot be estimated. Ordering encounters by encounter_id and splitting them into 10 equal groups is only a sequence view. It must not be read as seasonality.

M02. More diagnoses go with longer stays (r = 0.219) and higher readmission (r = 0.113). diag_4 was an exact copy of diag_3 and diag_5 was not a diagnosis code, so both were dropped. The comorbidity score is number_diagnoses.

M03. Not answerable from this file. None of the 49 columns is a discharge disposition. No proxy rate is reported. The field needed is a disposition code per encounter, with patients who died or went to hospice removed from the readmission denominator.

M04. Age shows the clearest pattern in medications and procedures. Statistical significance is common because the sample is large, and the averages are not adjusted for diagnosis mix.

M05. Prior inpatient, outpatient and emergency visits are averaged by ICD-9 chapter of diag_1 and for the 15 most common 3-digit codes. Diabetes (250.xx) is separated from the other endocrine codes.

M06. Mortality and later health status are not in the file. The only proxy is repeat use: encounters per patient in this file, and prior inpatient stays. That is consistent with a cycle of utilisation. It does not show deterioration or death.

M07. Insulin and metformin are the most used of the mapped medication columns. Specialty prescribing shares are on M07_Prescribing. Names for X3 to X25 follow the solution-guide appendix and should be confirmed with the data owner before any clinical use.

M08. Weight-by-diagnosis cells are small. Cells with fewer than 20 encounters are left blank. Do not design a weight programme from this table.

M09. Among patients with diabetesMed = Yes, each medication with at least 100 users is compared with a two-proportion z-test. Eleven tests at a 5% threshold will occasionally flag a chance difference. These are not effectiveness estimates.

M10. Not answerable. The file has no satisfaction score. No correlation is reported.

## Advanced questions

A01. Unpenalized logistic regression on the 13 admission-time variables in the guide. Patient-grouped holdout (30% of patients, random_state 0): AUC 0.652. Gradient boosting with specialty and diagnosis group added: AUC 0.667. Five-fold out-of-fold AUC: 0.654. At a 0.50 probability threshold, accuracy 0.618, precision 0.635, recall 0.398. The high-risk third is readmitted at 62.3%. Race and gender are excluded from the score. The tier is a ranking tool for follow-up intensity, not a reason to deny care.

A02. K-means, k = 4, on log1p prior inpatient, outpatient and emergency counts, standardised, 20 initialisations, random_state 0. Segment names are assigned after clustering from which visit type dominates. Silhouette scores for k = 2 to 6 are in the workbook.

A03. The file has no cost. At the placeholder $15,000 per readmission and an avoidable share of 27.0%, avoidable cost is $91,566,450. Replace both yellow inputs with hospital figures. The 46% base rate inflates any dollar total.

A04. Only race, gender and age are available. Adjusted odds compare each race group with Caucasian patients and men with women, holding the clinical covariates in the guide fixed. An odds ratio below 1 is lower odds than the reference, not evidence of better care. There is no income, insurance, education, housing or neighbourhood field to add.

A05. The simulated programme enrols 70.0% of the high-risk tier and assumes a 15.0% relative reduction among those reached. Under those assumptions it prevents 1066 readmissions and the net figure is $14,279,055. The reduction is not estimated from this file. Pilot it against a control group before scaling.

## Recommended actions

B01. Give ages 60-90 a structured follow-up call within 48-72 hours and a medication review. Use a lighter pathway for bands with lower rates and few encounters.
B02. Plan beds and discharge staff around rehabilitation, psychiatry and cardiovascular surgery. Make specialty a required admission field.
B03. Enrol patients with 2 or more prior emergency visits in care management at discharge.
B04. Extend the diabetes discharge bundle to every patient on diabetic medication, not only those with a 250 code.
B05. Treat a medication change as a risk flag: pharmacist review and a follow-up call within 72 hours.
B06. Do not trigger outreach from lab count alone. Use it only inside the multi-factor score in A01.
B07. Review a quarterly dashboard by race and gender after clinical adjustment. Do not act on an unadjusted gap by itself.
B08. Do not set weight-management policy from this file. Make weight required at admission, confirm the unit, and repeat the analysis.
B09. Pharmacist-led review when a stay has 20 or more distinct medications.
B10. Give patients with 3 or more prior outpatient visits one named coordinator and one follow-up plan.
M01. Add admission_date and discharge_date, then repeat by month and quarter. Until then, plan capacity from the A01 tier, not from a season.
M02. Flag 8 or more diagnoses at admission for early discharge planning.
M03. Request discharge disposition, admission type and admission source. Map them to home, home with services, skilled nursing, rehab, other facility, left against advice, and expired or hospice. Exclude expired and hospice from the readmission denominator.
M04. Look at groups with fewer interventions only after adjusting for diagnosis and severity.
M05. Size preventive programmes for the diagnosis groups with the highest prior use. Circulatory conditions are the largest group.
M06. Link a death register or discharge status, plus 90-day and 180-day events, before building a composite outcome.
M07. Share specialty prescribing and readmission profiles with service leads. Do not treat the differences as proof that a drug causes readmission.
M08. Treat the table as a hypothesis. Repeat it only after weight capture improves.
M09. Do not change the formulary from these associations. Use them to choose agents for a matched or randomised review.
M10. Link survey results to encounter_id, then use a point-biserial correlation or a logistic regression. Report the response rate, because people who answer surveys differ from those who do not.
A01. High tier: call within 48 hours and a visit within 7 days. Medium: call within 72 hours. Low: standard discharge. Do not use the score to deny care.
A02. Emergency-reliant: same-week primary care and a case manager. Frequent inpatient: transitional care. Outpatient-engaged: one coordinator. Low prior use: standard discharge unless the A01 tier is High.
A03. Replace the two yellow inputs with the hospital's average readmission cost and a chart-review estimate of the avoidable share.
A04. Add insurance, a ZIP deprivation index, language, housing and transport. Screen social needs before discharge and monitor adjusted rates quarterly.
A05. Pilot for six months against a control group. Replace the yellow assumptions with the observed effect before scaling.

## Checks

Row reconciliation difference is 0. Train and test patients do not overlap. Risk tiers and segments each cover every cleaned encounter. X1 and X2 values of None were kept as text in the source count.
