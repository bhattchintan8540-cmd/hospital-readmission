"""Question, approach and action for each case-study item. Findings stay in the calculated tables."""

NARRATIVES = {
    "B01": {
        "question": "What is the distribution of readmission rates across age groups?",
        "approach": "Group by the 10-year age band and calculate the share readmitted within 30 days. Test the table with a chi-square.",
        "action": "Give ages 60-90 a structured follow-up call within 48-72 hours and a medication review. Use a lighter pathway for bands with lower rates and few encounters.",
    },
    "B02": {
        "question": "Which medical specialties have the longest and shortest average stays?",
        "approach": "Average time_in_hospital by specialty. Rank only specialties with at least 30 encounters. Report missing specialty separately.",
        "action": "Plan beds and discharge staff around rehabilitation, psychiatry and cardiovascular surgery. Make specialty a required admission field.",
    },
    "B03": {
        "question": "How do prior-year emergency visits relate to readmission?",
        "approach": "Pearson correlation of number_emergency with readmitted, plus the rate in bands 0, 1, 2, 3, 4 and 5 or more.",
        "action": "Enrol patients with 2 or more prior emergency visits in care management at discharge.",
    },
    "B04": {
        "question": "What proportion of patients with diabetes were readmitted within 30 days?",
        "approach": "Primary definition is diabetesMed = Yes. Cross-check with ICD-9 250 in diag_1 to diag_3.",
        "action": "Extend the diabetes discharge bundle to every patient on diabetic medication, not only those with a 250 code.",
    },
    "B05": {
        "question": "Is readmission different when diabetic medication was changed?",
        "approach": "Compare the readmission rate for change = Ch with change = No using a two-proportion z-test.",
        "action": "Treat a medication change as a risk flag: pharmacist review and a follow-up call within 72 hours.",
    },
    "B06": {
        "question": "How do lab procedures during the stay relate to readmission?",
        "approach": "Pearson correlation, plus rates in bands of lab counts.",
        "action": "Do not trigger outreach from lab count alone. Use it only inside the multi-factor score in A01.",
    },
    "B07": {
        "question": "How do readmission rates vary by race and gender?",
        "approach": "Unadjusted rates by race, by gender, and for race by gender. Adjusted odds are on A04.",
        "action": "Review a quarterly dashboard by race and gender after clinical adjustment. Do not act on an unadjusted gap by itself.",
    },
    "B08": {
        "question": "How does weight relate to readmission?",
        "approach": "First measure how often weight is recorded. Then calculate rates only where a weight category exists, and flag cells with fewer than 30 encounters.",
        "action": "Do not set weight-management policy from this file. Make weight required at admission, confirm the unit, and repeat the analysis.",
    },
    "B09": {
        "question": "How does the number of medications relate to length of stay?",
        "approach": "Pearson correlation and a linear regression of time_in_hospital on num_medications, plus average stay by medication band.",
        "action": "Pharmacist-led review when a stay has 20 or more distinct medications.",
    },
    "B10": {
        "question": "How do prior outpatient visits relate to readmission?",
        "approach": "Pearson correlation of number_outpatient with readmitted, plus rates in the same visit bands used for emergency visits.",
        "action": "Give patients with 3 or more prior outpatient visits one named coordinator and one follow-up plan.",
    },
    "M01": {
        "question": "Are there months or seasons with higher readmission?",
        "approach": "The file has no admission or discharge date. Encounter_id order, split into 10 equal groups, is only a sequence proxy.",
        "action": "Add admission_date and discharge_date, then repeat by month and quarter. Until then, plan capacity from the A01 tier, not from a season.",
    },
    "M02": {
        "question": "How do comorbid conditions affect stay and readmission?",
        "approach": "Use number_diagnoses as the comorbidity score. diag_4 duplicated diag_3 and diag_5 was not a diagnosis code, so both were dropped.",
        "action": "Flag 8 or more diagnoses at admission for early discharge planning.",
    },
    "M03": {
        "question": "How does discharge disposition relate to readmission?",
        "approach": "Search the 49 source columns for a disposition or destination field.",
        "action": "Request discharge disposition, admission type and admission source. Map them to home, home with services, skilled nursing, rehab, other facility, left against advice, and expired or hospice. Exclude expired and hospice from the readmission denominator.",
    },
    "M04": {
        "question": "Do lab tests, procedures and medications differ by age, race and gender?",
        "approach": "Average the three intervention counts in each demographic group. One-way ANOVA p-values are from scipy. Gender ANOVA drops the unknown-gender rows.",
        "action": "Look at groups with fewer interventions only after adjusting for diagnosis and severity.",
    },
    "M05": {
        "question": "How do prior visits vary by primary diagnosis?",
        "approach": "Map diag_1 to ICD-9 chapters, with 250.xx kept as Diabetes, and average the three prior-year visit counts. Also list the 15 most common 3-digit codes.",
        "action": "Size preventive programmes for the diagnosis groups with the highest prior use. Circulatory conditions are the largest group.",
    },
    "M06": {
        "question": "What happens to patients beyond the readmission flag?",
        "approach": "Death, functional status and later outcomes are not in the file. The proxy is repeat use: encounters per patient, and prior inpatient stays.",
        "action": "Link a death register or discharge status, plus 90-day and 180-day events, before building a composite outcome.",
    },
    "M07": {
        "question": "How does prescribing vary by specialty, and how does it relate to readmission?",
        "approach": "A medication counts as used when the value is not No. Compare users and non-users, then show the share for the eight largest recorded specialties. Names follow the guide appendix.",
        "action": "Share specialty prescribing and readmission profiles with service leads. Do not treat the differences as proof that a drug causes readmission.",
    },
    "M08": {
        "question": "How do weight and primary diagnosis together relate to readmission?",
        "approach": "Among recorded weights, combine Under 75, 75 to 100, and Over 100 with the primary diagnosis group. Hide cells with fewer than 20 encounters.",
        "action": "Treat the table as a hypothesis. Repeat it only after weight capture improves.",
    },
    "M09": {
        "question": "Which diabetic medications are associated with lower readmission among diabetic patients?",
        "approach": "Restrict to diabetesMed = Yes. Two-proportion z-test for each medication with at least 100 users, plus insulin dosing status.",
        "action": "Do not change the formulary from these associations. Use them to choose agents for a matched or randomised review.",
    },
    "M10": {
        "question": "Do satisfaction scores correlate with readmission?",
        "approach": "Search every column for a survey or satisfaction field.",
        "action": "Link survey results to encounter_id, then use a point-biserial correlation or a logistic regression. Report the response rate, because people who answer surveys differ from those who do not.",
    },
    "A01": {
        "question": "Who is at high risk of readmission from the initial encounter?",
        "approach": "Unpenalized logistic regression on 13 admission-time variables. Hold out 30% of patients. Tier labels use 5-fold out-of-fold scores. Gradient boosting, with specialty and diagnosis added, is the benchmark only.",
        "action": "High tier: call within 48 hours and a visit within 7 days. Medium: call within 72 hours. Low: standard discharge. Do not use the score to deny care.",
    },
    "A02": {
        "question": "How do patients cluster by prior utilisation?",
        "approach": "K-means, k = 4, on standardised log1p counts of prior inpatient, outpatient and emergency visits. 20 initialisations, random_state 0. Names are assigned after clustering.",
        "action": "Emergency-reliant: same-week primary care and a case manager. Frequent inpatient: transitional care. Outpatient-engaged: one coordinator. Low prior use: standard discharge unless the A01 tier is High.",
    },
    "A03": {
        "question": "What is the financial impact of readmissions, including avoidable ones?",
        "approach": "The file has no cost or planned-versus-unplanned flag. Yellow cells are assumptions. The sensitivity grid multiplies readmissions by avoidable share and cost.",
        "action": "Replace the two yellow inputs with the hospital's average readmission cost and a chart-review estimate of the avoidable share.",
    },
    "A04": {
        "question": "What role do social determinants play in readmission?",
        "approach": "Only race, gender and age exist. Logistic odds for race and sex are adjusted for age, stay, procedures, medications, prior visits, diagnoses, diabetic medication, medication change, insulin and HbA1c testing. Reference is Caucasian women.",
        "action": "Add insurance, a ZIP deprivation index, language, housing and transport. Screen social needs before discharge and monitor adjusted rates quarterly.",
    },
    "A05": {
        "question": "What post-discharge programme do these results support, and what might it change?",
        "approach": "Enrol the high-risk tier, call within 48 hours, and add support for the emergency-reliant and frequent-inpatient segments. The reduction is an editable assumption, not an effect from this file.",
        "action": "Pilot for six months against a control group. Replace the yellow assumptions with the observed effect before scaling.",
    },
}
