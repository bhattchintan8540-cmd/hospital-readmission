"""Statistical helpers named in the solution guide."""

from __future__ import annotations

import math

import numpy as np
from scipy import stats


def strength(r: float) -> str:
    a = abs(r)
    if a < 0.10:
        return "Very weak"
    if a < 0.30:
        return "Weak"
    if a < 0.50:
        return "Moderate"
    return "Strong"


def pearson(x, y) -> dict:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    r, p = stats.pearsonr(x, y)
    n = int(x.size)
    if n > 2 and abs(r) < 1:
        t = r * math.sqrt((n - 2) / (1 - r * r))
    else:
        t = float("nan")
    return {
        "r": float(r),
        "r2": float(r * r),
        "t": float(t),
        "p": float(p),
        "n": n,
        "strength": strength(float(r)),
    }


def linreg(x, y) -> dict:
    slope, intercept, r, p, se = stats.linregress(np.asarray(x, dtype=float), np.asarray(y, dtype=float))
    base = pearson(x, y)
    base.update({"slope": float(slope), "intercept": float(intercept), "stderr": float(se), "p": float(p)})
    return base


def chi_square(rows: list[tuple[int, int]]) -> dict:
    """rows are (events, non-events) or a 2-column count table."""
    table = np.asarray(rows, dtype=float)
    if table.ndim != 2:
        raise ValueError("chi-square table must be 2-d")
    chi2, p, dof, _ = stats.chi2_contingency(table, correction=False)
    return {
        "chi2": float(chi2),
        "dof": int(dof),
        "p": float(p),
        "significant": bool(p < 0.05),
    }


def two_proportion(x1: int, n1: int, x2: int, n2: int) -> dict:
    """Two-sided z-test. z uses the pooled standard error; the CI uses the unpooled error."""
    if min(n1, n2) <= 0:
        raise ValueError("group sizes must be positive")
    p1 = x1 / n1
    p2 = x2 / n2
    diff = p1 - p2
    pooled = (x1 + x2) / (n1 + n2)
    se_pool = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = diff / se_pool if se_pool else float("nan")
    p = float(2 * (1 - stats.norm.cdf(abs(z)))) if se_pool else float("nan")
    se_unpooled = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return {
        "p1": p1,
        "p2": p2,
        "diff": diff,
        "diff_pp": diff * 100,
        "pooled": pooled,
        "se": se_pool,
        "z": z,
        "p": p,
        "ci_low_pp": (diff - 1.96 * se_unpooled) * 100,
        "ci_high_pp": (diff + 1.96 * se_unpooled) * 100,
        "significant": bool(p < 0.05),
    }


def anova(groups: list[np.ndarray]) -> float:
    cleaned = [np.asarray(g, dtype=float) for g in groups if len(g) > 0]
    if len(cleaned) < 2:
        return float("nan")
    _f, p = stats.f_oneway(*cleaned)
    return float(p)


def rate_table(df, by: str, target: str = "readmitted") -> list[dict]:
    rows = []
    for key, part in df.groupby(by, sort=False, observed=False):
        n = int(len(part))
        k = int(part[target].sum())
        rows.append({by: key, "encounters": n, "readmitted": k, "rate": (k / n) if n else float("nan")})
    return rows
