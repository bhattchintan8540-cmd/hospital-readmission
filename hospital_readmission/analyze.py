"""Answers for questions B01-B10, M01-M10 and A01-A05.

Methods follow the solution guide: rates, chi-square, two-proportion z-tests,
Pearson correlation, linear regression, ANOVA, unpenalized logistic regression,
a gradient-boosting benchmark, and K-means on log prior-visit counts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from hospital_readmission.prepare import AGE_ORDER, MEDICATIONS
from hospital_readmission.stats import anova, chi_square, linreg, pearson, two_proportion

LOGIT_FEATURES = [
    "age_mid",
    "time_in_hospital",
    "num_lab_procedures",
    "num_procedures",
    "num_medications",
    "number_outpatient",
    "number_emergency",
    "number_inpatient",
    "number_diagnoses",
    "diabetes_med_flag",
    "change_flag",
    "insulin_used",
    "hba1c_measured",
]

FEATURE_LABELS = {
    "age_mid": "Age (years, midpoint of band)",
    "time_in_hospital": "Length of stay (days)",
    "num_lab_procedures": "Lab procedures",
    "num_procedures": "Other procedures",
    "num_medications": "Medications",
    "number_outpatient": "Outpatient visits, prior year",
    "number_emergency": "Emergency visits, prior year",
    "number_inpatient": "Inpatient stays, prior year",
    "number_diagnoses": "Diagnoses entered",
    "diabetes_med_flag": "On diabetic medication (1 = yes, 0 = no)",
    "change_flag": "Diabetic medication changed (1/0)",
    "insulin_used": "Insulin used (1/0)",
    "hba1c_measured": "HbA1c measured (1/0)",
}

# Common medications the guide tests once each has at least 100 users.
FOCUS_MEDS = [
    "metformin",
    "repaglinide",
    "nateglinide",
    "glimepiride",
    "glipizide",
    "glyburide",
    "pioglitazone",
    "rosiglitazone",
    "acarbose",
    "insulin",
    "glyburide-metformin",
]


def _cap_visits(series: pd.Series) -> pd.Series:
    return series.clip(upper=5).astype(int).map(lambda v: "5+" if v == 5 else str(v))


def _lab_band(value: int) -> str:
    if value <= 20:
        return "1-20"
    if value <= 40:
        return "21-40"
    if value <= 60:
        return "41-60"
    if value <= 80:
        return "61-80"
    return "81+"


def _med_band(value: int) -> str:
    if value <= 10:
        return "1-10"
    if value <= 20:
        return "11-20"
    if value <= 30:
        return "21-30"
    return "31+"


def _dx_band(value: int) -> str:
    if value <= 3:
        return "1-3"
    if value <= 5:
        return "4-5"
    if value <= 7:
        return "6-7"
    if value <= 9:
        return "8-9"
    return "10 or more"


def _weight_group(weight: str) -> str:
    if weight == "[75-100)":
        return "75 to 100"
    if weight in {"[0-25)", "[25-50)", "[50-75)"}:
        return "Under 75"
    if weight == "Not recorded":
        return "Not recorded"
    return "Over 100"


def _encounter_band(n: int) -> str:
    return "4+" if n >= 4 else str(n)


def _fit_logit(frame: pd.DataFrame, y: pd.Series):
    design = sm.add_constant(frame.astype(float), has_constant="add")
    model = sm.Logit(y.astype(float), design)
    return model.fit(disp=False, maxiter=200)


def _safe_auc(y_true, y_score) -> float:
    y_true = np.asarray(y_true)
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(roc_auc_score(y_true, y_score))


def _patient_split(df: pd.DataFrame):
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=0)
    train_idx, test_idx = next(splitter.split(df, df["readmitted"], df["patient_id"]))
    return df.iloc[train_idx], df.iloc[test_idx]


def build_models(df: pd.DataFrame) -> dict:
    train, test = _patient_split(df)
    overlap = set(train["patient_id"]).intersection(set(test["patient_id"]))
    if overlap:
        raise RuntimeError(f"patient leakage in split: {len(overlap)} patients")

    train_model = _fit_logit(train[LOGIT_FEATURES], train["readmitted"])
    test_design = sm.add_constant(test[LOGIT_FEATURES].astype(float), has_constant="add")
    test_prob = np.asarray(train_model.predict(test_design))
    test_hat = (test_prob >= 0.5).astype(int)

    full = _fit_logit(df[LOGIT_FEATURES], df["readmitted"])
    params = full.params
    conf = full.conf_int()

    oof = pd.Series(index=df.index, dtype=float)
    folder = GroupKFold(n_splits=5)
    for tr, te in folder.split(df, df["readmitted"], df["patient_id"]):
        fold_model = _fit_logit(df.iloc[tr][LOGIT_FEATURES], df.iloc[tr]["readmitted"])
        design = sm.add_constant(df.iloc[te][LOGIT_FEATURES].astype(float), has_constant="add")
        oof.iloc[te] = np.asarray(fold_model.predict(design))
    if oof.isna().any():
        raise RuntimeError("out-of-fold scores were not produced for every encounter")

    tiers = pd.qcut(oof, 3, labels=["Low", "Medium", "High"])
    # qcut labels the lowest third Low. The guide's High tier is the top third.
    thresholds = oof.quantile([1 / 3, 2 / 3])

    gb_auc = _gradient_boosting_auc(train, test)

    coefficients = []
    for name in LOGIT_FEATURES:
        coefficients.append(
            {
                "variable": FEATURE_LABELS[name],
                "key": name,
                "coefficient": float(params[name]),
                "odds_ratio": float(np.exp(params[name])),
                "ci_low": float(np.exp(conf.loc[name, 0])),
                "ci_high": float(np.exp(conf.loc[name, 1])),
                "p": float(full.pvalues[name]),
            }
        )

    tier_rows = []
    scored = df.copy()
    scored["oof_score"] = oof.to_numpy()
    scored["risk_tier"] = tiers.astype(str).to_numpy()
    for tier in ["High", "Medium", "Low"]:
        part = scored.loc[scored["risk_tier"] == tier]
        k = int(part["readmitted"].sum())
        n = int(len(part))
        tier_rows.append(
            {
                "risk_tier": tier,
                "encounters": n,
                "readmitted": k,
                "rate": k / n,
                "share_of_readmissions": k / scored["readmitted"].sum(),
                "lift": (k / n) / scored["readmitted"].mean(),
            }
        )

    return {
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_patients": int(train["patient_id"].nunique()),
        "test_patients": int(test["patient_id"].nunique()),
        "auc_logit": _safe_auc(test["readmitted"], test_prob),
        "auc_oof": _safe_auc(df["readmitted"], oof),
        "auc_gb": gb_auc,
        "accuracy": float(accuracy_score(test["readmitted"], test_hat)),
        "precision": float(precision_score(test["readmitted"], test_hat, zero_division=0)),
        "recall": float(recall_score(test["readmitted"], test_hat, zero_division=0)),
        "intercept": float(params["const"]),
        "coefficients": coefficients,
        "threshold_medium": float(thresholds.iloc[0]),
        "threshold_high": float(thresholds.iloc[1]),
        "tiers": tier_rows,
        "prevalence": float(df["readmitted"].mean()),
        "pseudo_r2": float(full.prsquared),
        "scored": scored,
    }


def _gradient_boosting_auc(train: pd.DataFrame, test: pd.DataFrame) -> float:
    def matrix(frame: pd.DataFrame, columns: list[str] | None = None):
        base = frame[LOGIT_FEATURES].reset_index(drop=True).astype(float)
        extra = pd.get_dummies(
            pd.DataFrame(
                {
                    "specialty": frame["medical_specialty"].reset_index(drop=True),
                    "diag_group": frame["diag_1_group"].reset_index(drop=True),
                }
            ),
            drop_first=False,
        )
        out = pd.concat([base, extra], axis=1)
        if columns is None:
            return out, list(out.columns)
        return out.reindex(columns=columns, fill_value=0), columns

    # Collapse rare specialties using the training distribution only.
    counts = train["medical_specialty"].value_counts()
    train = train.copy()
    test = test.copy()
    train["medical_specialty"] = train["medical_specialty"].where(train["medical_specialty"].map(counts) >= 30, "Other specialty")
    test["medical_specialty"] = test["medical_specialty"].where(test["medical_specialty"].map(counts) >= 30, "Other specialty")
    x_train, columns = matrix(train)
    x_test, _ = matrix(test, columns)
    model = GradientBoostingClassifier(
        n_estimators=80,
        max_depth=3,
        learning_rate=0.1,
        subsample=0.8,
        random_state=0,
    )
    model.fit(x_train, train["readmitted"])
    prob = model.predict_proba(x_test)[:, 1]
    return _safe_auc(test["readmitted"], prob)


def _name_segments(profile: pd.DataFrame) -> dict[int, str]:
    remaining = set(profile.index.astype(int))
    names = {}
    emergency = int(profile["number_emergency"].idxmax())
    names[emergency] = "Emergency-reliant"
    remaining.remove(emergency)
    inpatient = int(profile.loc[list(remaining), "number_inpatient"].idxmax())
    names[inpatient] = "Frequent inpatient"
    remaining.remove(inpatient)
    outpatient = int(profile.loc[list(remaining), "number_outpatient"].idxmax())
    names[outpatient] = "Outpatient-engaged"
    remaining.remove(outpatient)
    names[remaining.pop()] = "Low prior utilisation"
    return names


def build_segments(df: pd.DataFrame) -> dict:
    features = np.log1p(df[["number_inpatient", "number_outpatient", "number_emergency"]].astype(float))
    scaled = StandardScaler().fit_transform(features)
    model = KMeans(n_clusters=4, n_init=20, random_state=0)
    labels = model.fit_predict(scaled)
    sample_n = min(8000, len(df))
    rng = np.random.default_rng(0)
    sample_idx = rng.choice(len(df), size=sample_n, replace=False)
    silhouettes = {}
    for k in range(2, 7):
        km = KMeans(n_clusters=k, n_init=10, random_state=0)
        pred = km.fit_predict(scaled[sample_idx])
        silhouettes[k] = float(silhouette_score(scaled[sample_idx], pred))
    assigned = df.copy()
    assigned["cluster"] = labels
    profile = assigned.groupby("cluster")[["number_inpatient", "number_outpatient", "number_emergency"]].mean()
    names = _name_segments(profile)
    assigned["segment"] = assigned["cluster"].map(names)
    rows = []
    for name in ["Emergency-reliant", "Frequent inpatient", "Outpatient-engaged", "Low prior utilisation"]:
        part = assigned.loc[assigned["segment"] == name]
        rows.append(
            {
                "segment": name,
                "encounters": int(len(part)),
                "share": len(part) / len(assigned),
                "avg_inpatient": float(part["number_inpatient"].mean()),
                "avg_outpatient": float(part["number_outpatient"].mean()),
                "avg_emergency": float(part["number_emergency"].mean()),
                "avg_stay": float(part["time_in_hospital"].mean()),
                "readmitted": int(part["readmitted"].sum()),
                "rate": float(part["readmitted"].mean()),
            }
        )
    return {"rows": rows, "silhouette": silhouettes, "labels": assigned["segment"].to_numpy()}


def _group_rate(df: pd.DataFrame, column: str, order: list | None = None) -> pd.DataFrame:
    data = df.copy()
    if order is not None:
        data[column] = pd.Categorical(data[column], categories=order, ordered=True)
    grouped = data.groupby(column, observed=False)
    out = grouped.agg(encounters=("readmitted", "size"), readmitted=("readmitted", "sum")).reset_index()
    out["rate"] = out["readmitted"] / out["encounters"]
    return out


def analyze(df: pd.DataFrame, meta: dict) -> dict:
    df = df.copy()
    df["lab_band"] = df["num_lab_procedures"].map(_lab_band)
    df["med_band"] = df["num_medications"].map(_med_band)
    df["dx_band"] = df["number_diagnoses"].map(_dx_band)
    df["ed_band"] = _cap_visits(df["number_emergency"])
    df["op_band"] = _cap_visits(df["number_outpatient"])
    df["ip_band"] = df["number_inpatient"].clip(upper=3).astype(int).map(lambda v: "3+" if v == 3 else str(v))
    df["weight_group"] = df["weight"].map(_weight_group)
    counts = df.groupby("patient_id")["encounter_id"].transform("size")
    df["encounters_per_patient_band"] = counts.map(_encounter_band)

    b01 = _group_rate(df, "age", AGE_ORDER)
    b01_chi = chi_square(list(zip(b01["readmitted"], b01["encounters"] - b01["readmitted"])))

    spec = (
        df.groupby("medical_specialty")
        .agg(encounters=("time_in_hospital", "size"), avg_stay=("time_in_hospital", "mean"))
        .reset_index()
    )
    spec_ranked = spec.loc[(spec["medical_specialty"] != "Not recorded") & (spec["encounters"] >= 30)].sort_values(
        ["avg_stay", "medical_specialty"], ascending=[False, True]
    )
    spec_ranked.insert(0, "rank", np.arange(1, len(spec_ranked) + 1))

    b03 = _group_rate(df, "ed_band", ["0", "1", "2", "3", "4", "5+"])
    b03_corr = pearson(df["number_emergency"], df["readmitted"])
    b10 = _group_rate(df, "op_band", ["0", "1", "2", "3", "4", "5+"])
    b10_corr = pearson(df["number_outpatient"], df["readmitted"])

    dm_yes = df.loc[df["diabetesMed"] == "Yes"]
    dm_no = df.loc[df["diabetesMed"] == "No"]
    dx_yes = df.loc[df["diabetes_dx"] == 1]
    dx_no = df.loc[df["diabetes_dx"] == 0]
    b04 = pd.DataFrame(
        [
            _cohort_row("On diabetic medication (diabetesMed = Yes)", dm_yes),
            _cohort_row("Not on diabetic medication (diabetesMed = No)", dm_no),
            _cohort_row("Diabetes diagnosis code 250 in diag_1-3 (Yes)", dx_yes),
            _cohort_row("No diabetes diagnosis code (No)", dx_no),
            _cohort_row("All encounters (benchmark)", df),
        ]
    )

    ch = df.loc[df["change"] == "Ch"]
    no = df.loc[df["change"] == "No"]
    b05 = pd.DataFrame(
        [
            _cohort_row("Medication changed (Ch)", ch),
            _cohort_row("No change (No)", no),
            _cohort_row("All encounters (benchmark)", df),
        ]
    )
    b05_z = two_proportion(int(ch["readmitted"].sum()), len(ch), int(no["readmitted"].sum()), len(no))

    b06 = _group_rate(df, "lab_band", ["1-20", "21-40", "41-60", "61-80", "81+"])
    b06_corr = pearson(df["num_lab_procedures"], df["readmitted"])

    race_order = ["Caucasian", "AfricanAmerican", "Hispanic", "Asian", "Other", "Unknown"]
    b07_race = _group_rate(df, "race", [r for r in race_order if r in set(df["race"])])
    b07_gender = _group_rate(df, "gender", [g for g in ["Female", "Male", "Unknown"] if g in set(df["gender"])])
    b07_chi = chi_square(list(zip(b07_race["readmitted"], b07_race["encounters"] - b07_race["readmitted"])))
    cross = []
    for race in b07_race["race"]:
        row = {"race": race}
        for gender in ["Female", "Male"]:
            part = df.loc[(df["race"] == race) & (df["gender"] == gender)]
            row[f"{gender}_n"] = int(len(part))
            row[f"{gender}_rate"] = float(part["readmitted"].mean()) if len(part) else float("nan")
        cross.append(row)

    weight_known = df.loc[df["weight_recorded"] == 1]
    weight_order = ["[0-25)", "[25-50)", "[50-75)", "[75-100)", "[100-125)", "[125-150)", "[150-175)", "[175-200)", ">200"]
    b08 = _group_rate(weight_known, "weight", [w for w in weight_order if w in set(weight_known["weight"])])
    b08["flag"] = np.where(b08["encounters"] < 30, "n<30 - interpret with caution", "")

    b09 = (
        df.groupby(df["med_band"])
        .agg(encounters=("time_in_hospital", "size"), avg_stay=("time_in_hospital", "mean"))
        .reindex(["1-10", "11-20", "21-30", "31+"])
        .reset_index()
    )
    b09_reg = linreg(df["num_medications"], df["time_in_hospital"])

    m01 = _group_rate(df, "seq_decile", list(range(1, 11)))
    m01_chi = chi_square(list(zip(m01["readmitted"], m01["encounters"] - m01["readmitted"])))

    m02 = (
        df.groupby(df["dx_band"])
        .agg(
            encounters=("readmitted", "size"),
            avg_stay=("time_in_hospital", "mean"),
            readmitted=("readmitted", "sum"),
        )
        .reindex(["1-3", "4-5", "6-7", "8-9", "10 or more"])
        .reset_index()
    )
    m02["rate"] = m02["readmitted"] / m02["encounters"]
    m02_stay = pearson(df["number_diagnoses"], df["time_in_hospital"])
    m02_readmit = pearson(df["number_diagnoses"], df["readmitted"])

    if meta.get("has_discharge"):
        order = [
            "Home",
            "Home with health service",
            "Skilled nursing / ICF",
            "Rehab",
            "Other facility",
            "Left against advice",
            "Unknown",
        ]
        present = [g for g in order if g in set(df["discharge_group"])]
        m03 = _group_rate(df, "discharge_group", present)
        m03_chi = chi_square(list(zip(m03["readmitted"], m03["encounters"] - m03["readmitted"])))
        m03_note = (
            "Expired and hospice discharges are excluded from the cohort because those patients "
            "are not at risk of readmission. This field is present on the UCI file and was missing "
            "from the Kaggle extract described in the solution guide."
        )
    else:
        m03 = pd.DataFrame()
        m03_chi = None
        m03_note = "Not answerable from this file: no discharge disposition column."

    m04_age = _intervention_table(df, "age", AGE_ORDER)
    m04_race = _intervention_table(df, "race", list(b07_race["race"]))
    gender_known = df.loc[df["gender"] != "Unknown"]
    m04_gender = _intervention_table(gender_known, "gender", ["Female", "Male"])
    m04_anova = {
        "age": _anova_block(df, "age"),
        "race": _anova_block(df, "race"),
        "gender": _anova_block(gender_known, "gender"),
    }

    m05 = (
        df.groupby("diag_1_group")
        .agg(
            encounters=("readmitted", "size"),
            avg_inpatient=("number_inpatient", "mean"),
            avg_outpatient=("number_outpatient", "mean"),
            avg_emergency=("number_emergency", "mean"),
            readmitted=("readmitted", "sum"),
        )
        .reset_index()
        .sort_values("encounters", ascending=False)
    )
    m05["rate"] = m05["readmitted"] / m05["encounters"]
    top_codes = (
        df.groupby("diag_1_code3")
        .agg(
            encounters=("readmitted", "size"),
            avg_inpatient=("number_inpatient", "mean"),
            avg_outpatient=("number_outpatient", "mean"),
            avg_emergency=("number_emergency", "mean"),
            readmitted=("readmitted", "sum"),
        )
        .reset_index()
        .sort_values("encounters", ascending=False)
        .head(15)
    )
    top_codes["rate"] = top_codes["readmitted"] / top_codes["encounters"]

    m06_enc = (
        df.groupby("encounters_per_patient_band")
        .agg(encounters=("readmitted", "size"), avg_stay=("time_in_hospital", "mean"), readmitted=("readmitted", "sum"))
        .reindex(["1", "2", "3", "4+"])
        .dropna(how="all")
        .reset_index()
    )
    m06_enc["rate"] = m06_enc["readmitted"] / m06_enc["encounters"]
    m06_ip = _group_rate(df, "ip_band", ["0", "1", "2", "3+"])
    m06_ip = m06_ip.merge(
        df.groupby("ip_band")["time_in_hospital"].mean().rename("avg_stay"),
        left_on="ip_band",
        right_index=True,
        how="left",
    )

    med_rows = []
    for code, column, label in MEDICATIONS:
        used = df[f"{column}_used"] == 1
        n_used = int(used.sum())
        if n_used < 100:
            continue
        rate_used = float(df.loc[used, "readmitted"].mean())
        rate_not = float(df.loc[~used, "readmitted"].mean())
        med_rows.append(
            {
                "column": code,
                "medication": label,
                "users": n_used,
                "share": n_used / len(df),
                "rate_users": rate_used,
                "rate_nonusers": rate_not,
                "diff_pp": (rate_used - rate_not) * 100,
            }
        )
    m07_meds = pd.DataFrame(med_rows).sort_values("users", ascending=False)

    top_specs = (
        df.loc[df["medical_specialty"] != "Not recorded", "medical_specialty"].value_counts().head(8).index.tolist()
    )
    share_rows = []
    for specialty in top_specs:
        part = df.loc[df["medical_specialty"] == specialty]
        row = {"specialty": specialty, "encounters": int(len(part)), "readmission_rate": float(part["readmitted"].mean())}
        for column in ["insulin", "metformin", "glipizide", "glyburide", "glimepiride", "pioglitazone", "rosiglitazone"]:
            row[column] = float(part[f"{column}_used"].mean())
        share_rows.append(row)
    m07_spec = pd.DataFrame(share_rows)

    recorded = df.loc[df["weight_recorded"] == 1].copy()
    m08_rows = []
    for group, part in recorded.groupby("diag_1_group"):
        row = {"diag_1_group": group}
        for band in ["Under 75", "75 to 100", "Over 100"]:
            cell = part.loc[part["weight_group"] == band]
            row[f"n_{band}"] = int(len(cell))
            row[f"rate_{band}"] = float(cell["readmitted"].mean()) if len(cell) >= 20 else float("nan")
        m08_rows.append(row)
    m08 = pd.DataFrame(m08_rows).sort_values("n_Under 75", ascending=False)

    m09_rows = []
    diabetic = df.loc[df["diabetesMed"] == "Yes"]
    for code, column, label in MEDICATIONS:
        used = diabetic[f"{column}_used"] == 1
        n_used = int(used.sum())
        n_not = int((~used).sum())
        if n_used < 100 or n_not == 0:
            continue
        k_used = int(diabetic.loc[used, "readmitted"].sum())
        k_not = int(diabetic.loc[~used, "readmitted"].sum())
        test = two_proportion(k_used, n_used, k_not, n_not)
        m09_rows.append(
            {
                "column": code,
                "medication": label,
                "users": n_used,
                "rate_users": test["p1"],
                "nonusers": n_not,
                "rate_nonusers": test["p2"],
                "diff_pp": test["diff_pp"],
                "z": test["z"],
                "p": test["p"],
                "result": "Significant" if test["significant"] else "Not significant",
            }
        )
    m09 = pd.DataFrame(m09_rows)
    insulin_rows = _group_rate(diabetic, "insulin_status", ["No", "Steady", "Up", "Down"])

    models = build_models(df)
    segments = build_segments(df)
    scored = models["scored"].copy()
    scored["segment"] = segments["labels"]
    df = scored

    a04 = _adjusted_odds(df)

    assumptions = {
        "cost_per_readmission": 15000,
        "avoidable_share": 0.27,
        "enrolment": 0.70,
        "relative_reduction": 0.15,
        "programme_cost": 150,
    }
    high = next(row for row in models["tiers"] if row["risk_tier"] == "High")
    finance = _finance(meta, assumptions, high)

    checks = _checks(df, meta, models, segments)
    return {
        "meta": meta,
        "df": df,
        "b01": b01,
        "b01_chi": b01_chi,
        "b02": spec_ranked.reset_index(drop=True),
        "b02_missing": spec.loc[spec["medical_specialty"] == "Not recorded"].iloc[0].to_dict(),
        "b02_overall_stay": float(df["time_in_hospital"].mean()),
        "b03": b03,
        "b03_corr": b03_corr,
        "b04": b04,
        "b05": b05,
        "b05_z": b05_z,
        "b06": b06,
        "b06_corr": b06_corr,
        "b07_race": b07_race,
        "b07_gender": b07_gender,
        "b07_chi": b07_chi,
        "b07_cross": pd.DataFrame(cross),
        "b08": b08,
        "b08_recorded": int(df["weight_recorded"].sum()),
        "b08_recorded_rate": float(weight_known["readmitted"].mean()) if len(weight_known) else float("nan"),
        "b08_missing_rate": float(df.loc[df["weight_recorded"] == 0, "readmitted"].mean()),
        "b09": b09,
        "b09_reg": b09_reg,
        "b10": b10,
        "b10_corr": b10_corr,
        "m01": m01,
        "m01_chi": m01_chi,
        "m02": m02,
        "m02_stay": m02_stay,
        "m02_readmit": m02_readmit,
        "m03": m03,
        "m03_chi": m03_chi,
        "m03_note": m03_note,
        "m04_age": m04_age,
        "m04_race": m04_race,
        "m04_gender": m04_gender,
        "m04_anova": m04_anova,
        "m05": m05,
        "m05_codes": top_codes,
        "m06_enc": m06_enc,
        "m06_ip": m06_ip,
        "m07_meds": m07_meds,
        "m07_spec": m07_spec,
        "m08": m08,
        "m09": m09,
        "m09_insulin": insulin_rows,
        "model": {k: v for k, v in models.items() if k != "scored"},
        "segments": {k: v for k, v in segments.items() if k != "labels"},
        "a04": a04,
        "assumptions": assumptions,
        "finance": finance,
        "checks": checks,
        "means": {
            "stay": float(df["time_in_hospital"].mean()),
            "medications": float(df["num_medications"].mean()),
            "labs": float(df["num_lab_procedures"].mean()),
            "procedures": float(df["num_procedures"].mean()),
            "diabetes_med_share": float((df["diabetesMed"] == "Yes").mean()),
            "specialty_missing_share": float((df["medical_specialty"] == "Not recorded").mean()),
            "weight_recorded_share": float(df["weight_recorded"].mean()),
        },
    }


def _cohort_row(label: str, part: pd.DataFrame) -> dict:
    n = int(len(part))
    k = int(part["readmitted"].sum())
    return {"cohort": label, "encounters": n, "readmitted": k, "rate": k / n if n else float("nan")}


def _intervention_table(df: pd.DataFrame, column: str, order: list) -> pd.DataFrame:
    data = df.copy()
    data[column] = pd.Categorical(data[column], categories=order, ordered=True)
    out = (
        data.groupby(column, observed=False)
        .agg(
            encounters=("readmitted", "size"),
            avg_labs=("num_lab_procedures", "mean"),
            avg_medications=("num_medications", "mean"),
            avg_procedures=("num_procedures", "mean"),
        )
        .reset_index()
    )
    return out


def _anova_block(df: pd.DataFrame, column: str) -> dict:
    out = {}
    for measure in ["num_lab_procedures", "num_medications", "num_procedures"]:
        groups = [part[measure].to_numpy() for _, part in df.groupby(column) if len(part)]
        out[measure] = anova(groups)
    return out


def _adjusted_odds(df: pd.DataFrame) -> pd.DataFrame:
    covariates = [
        "age_mid",
        "time_in_hospital",
        "num_procedures",
        "num_medications",
        "number_outpatient",
        "number_emergency",
        "number_inpatient",
        "number_diagnoses",
        "diabetes_med_flag",
        "change_flag",
        "insulin_used",
        "hba1c_measured",
    ]
    race = pd.get_dummies(df["race"], prefix="race", drop_first=False)
    # Caucasian is the reference.
    race = race.drop(columns=[c for c in race.columns if c.endswith("Caucasian")])
    male = (df["gender"] == "Male").astype(int).rename("male")
    design = pd.concat([df[covariates], race, male], axis=1).astype(float)
    model = _fit_logit(design, df["readmitted"])
    rows = []
    labels = {col: col.replace("race_", "") + " vs Caucasian" for col in race.columns}
    labels["male"] = "Male vs female"
    conf = model.conf_int()
    for key, label in labels.items():
        rows.append(
            {
                "comparison": label,
                "odds_ratio": float(np.exp(model.params[key])),
                "ci_low": float(np.exp(conf.loc[key, 0])),
                "ci_high": float(np.exp(conf.loc[key, 1])),
                "p": float(model.pvalues[key]),
            }
        )
    return pd.DataFrame(rows)


def _finance(meta: dict, assumptions: dict, high: dict) -> dict:
    readmits = int(meta["readmitted_n"])
    encounters = int(meta["analysis_rows"])
    cost = assumptions["cost_per_readmission"]
    share = assumptions["avoidable_share"]
    total_cost = readmits * cost
    avoidable_n = readmits * share
    enrolled = high["encounters"] * assumptions["enrolment"]
    enrolled_readmits = high["readmitted"] * assumptions["enrolment"]
    prevented = enrolled_readmits * assumptions["relative_reduction"]
    gross = prevented * cost
    programme = enrolled * assumptions["programme_cost"]
    net = gross - programme
    return {
        "encounters": encounters,
        "readmissions": readmits,
        "rate": readmits / encounters,
        "total_cost": total_cost,
        "avoidable_n": avoidable_n,
        "unavoidable_n": readmits - avoidable_n,
        "avoidable_cost": avoidable_n * cost,
        "unavoidable_cost": (readmits - avoidable_n) * cost,
        "cost_per_encounter": total_cost / encounters,
        "high_encounters": high["encounters"],
        "high_readmissions": high["readmitted"],
        "high_rate": high["rate"],
        "enrolled": enrolled,
        "enrolled_readmissions": enrolled_readmits,
        "prevented": prevented,
        "rate_after": (readmits - prevented) / encounters,
        "reduction_pp": (readmits / encounters - (readmits - prevented) / encounters) * 100,
        "gross_savings": gross,
        "programme_cost": programme,
        "net_savings": net,
        "roi": net / programme if programme else float("nan"),
    }


def _checks(df: pd.DataFrame, meta: dict, models: dict, segments: dict) -> list[str]:
    errors = []
    if not set(df["readmitted"].unique()).issubset({0, 1}):
        errors.append("readmitted is not binary")
    if int(df["readmitted"].sum()) != int(meta["readmitted_n"]):
        errors.append("readmission count does not match the cohort summary")
    tier_n = sum(row["encounters"] for row in models["tiers"])
    if tier_n != len(df):
        errors.append(f"risk tiers cover {tier_n} rows, cohort has {len(df)}")
    seg_n = sum(row["encounters"] for row in segments["rows"])
    if seg_n != len(df):
        errors.append(f"segments cover {seg_n} rows, cohort has {len(df)}")
    if not (0.5 < models["auc_logit"] < 1):
        errors.append(f"logistic AUC out of range: {models['auc_logit']}")
    if models["train_patients"] + models["test_patients"] != df["patient_id"].nunique():
        errors.append("train and test patients do not partition the cohort")
    if meta["source_kind"] == "uci":
        expected = meta["source_rows"] - meta["duplicate_rows_removed"] - meta["expired_hospice_excluded"]
        if expected != meta["analysis_rows"]:
            errors.append("row reconciliation failed for the UCI source")
    if meta["source_kind"] == "kaggle":
        expected = meta["source_rows"] - meta["duplicate_rows_removed"]
        if expected != meta["analysis_rows"]:
            errors.append("row reconciliation failed for the Kaggle source")
    return errors
