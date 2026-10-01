"""Static dashboard pages for the hospital readmission case study."""

from __future__ import annotations

from html import escape
from pathlib import Path


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _bar_rows(labels, displays, magnitudes, max_value: float | None = None) -> str:
    peak = max_value if max_value else (max(magnitudes) or 1)
    rows = []
    for label, display, magnitude in zip(labels, displays, magnitudes):
        width = 0 if peak == 0 else max(2, round(100 * float(magnitude) / peak))
        rows.append(
            "<div class='bar-row'>"
            f"<span class='bar-label'>{escape(str(label))}</span>"
            "<span class='bar-track'><span class='bar-fill' "
            f"style='width:{width}%'></span></span>"
            f"<span class='bar-value'>{escape(str(display))}</span>"
            "</div>"
        )
    return "\n".join(rows)


def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    :root {{
      --ink: #1c2b33;
      --muted: #5c6d76;
      --line: #d7e0e4;
      --card: #ffffff;
      --bg: #f4f7f8;
      --teal: #0f6e6b;
      --teal-dark: #0b3d45;
      --amber: #a15c07;
      --amber-bg: #fff6e8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; background: var(--bg); color: var(--ink);
      font: 15px/1.45 "Segoe UI", Helvetica, Arial, sans-serif;
    }}
    header {{
      background: var(--teal-dark); color: white; padding: 28px 40px 22px;
    }}
    header p {{ margin: 6px 0 0; color: #d5e4e6; max-width: 820px; }}
    h1 {{ margin: 0; font-size: 28px; font-weight: 650; }}
    main {{ padding: 24px 40px 40px; max-width: 1180px; }}
    h2 {{ margin: 28px 0 12px; font-size: 18px; }}
    .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }}
    .card {{
      background: var(--card); border: 1px solid var(--line); border-radius: 10px;
      padding: 16px 18px;
    }}
    .kpi .label {{ color: var(--muted); font-size: 13px; }}
    .kpi .value {{ font-size: 28px; font-weight: 680; margin-top: 4px; }}
    .kpi .note {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}
    .grid {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 14px; }}
    .bar-row {{ display: grid; grid-template-columns: 250px 1fr 64px; gap: 8px; align-items: center; margin: 7px 0; }}
    .bar-label {{ font-size: 12px; line-height: 1.2; }}
    .note {{ color: var(--muted); font-size: 12px; }}
    .bar-track {{ background: #e7eef0; border-radius: 999px; height: 12px; }}
    .bar-fill {{ display: block; height: 12px; border-radius: 999px; background: var(--teal); }}
    .bar-value {{ text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; }}
    .callout {{ background: var(--amber-bg); border: 1px solid #f0d7a8; color: #6d4308; border-radius: 10px; padding: 14px 16px; }}
    ul {{ margin: 8px 0 0; padding-left: 18px; }}
    li {{ margin: 4px 0; }}
    footer {{ color: var(--muted); font-size: 12px; margin-top: 18px; }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(title)}</h1>
    <p>Hospital administration case study. Source file: Kaggle Hospital Administration Data, cleaned to 48,911 encounters.</p>
  </header>
  <main>
    {body}
  </main>
</body>
</html>
"""


def write_dashboard(results: dict, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    meta = results["meta"]
    means = results["means"]
    b01 = results["b01"]
    b03 = results["b03"]
    b02 = results["b02"].head(8)
    tiers = {row["risk_tier"]: row for row in results["model"]["tiers"]}
    segments = results["segments"]["rows"]

    overview = _page(
        "Readmission overview",
        f"""
        <section class="kpis">
          <article class="card kpi"><div class="label">Encounters analysed</div><div class="value">{meta['analysis_rows']:,}</div><div class="note">{meta['unique_patients']:,} patients</div></article>
          <article class="card kpi"><div class="label">30-day readmission</div><div class="value">{_pct(meta['readmission_rate'])}</div><div class="note">{meta['readmitted_n']:,} encounters</div></article>
          <article class="card kpi"><div class="label">Average stay</div><div class="value">{means['stay']:.2f} days</div><div class="note">{means['medications']:.1f} medications on average</div></article>
          <article class="card kpi"><div class="label">On diabetic medication</div><div class="value">{_pct(means['diabetes_med_share'])}</div><div class="note">Weight recorded for only {_pct(means['weight_recorded_share'])}</div></article>
        </section>
        <p class="callout">The 46.2% rate is far above a typical hospital benchmark. Use it to compare groups inside this file, not to judge the hospital against other hospitals.</p>
        <div class="grid">
          <section class="card">
            <h2>Readmission by age</h2>
            {_bar_rows(list(b01['age']), [f"{r * 100:.1f}%" for r in b01['rate']], list(b01['rate'] * 100), max_value=60)}
          </section>
          <section class="card">
            <h2>Prior emergency visits</h2>
            {_bar_rows(list(b03['ed_band']), [f"{r * 100:.1f}%" for r in b03['rate']], list(b03['rate'] * 100), max_value=100)}
            <p class="note">Correlation is weak (r = {results['b03_corr']['r']:.3f}), but the gradient is steep.</p>
          </section>
        </div>
        <footer>Specialty is missing on {_pct(means['specialty_missing_share'])} of encounters. The file has no dates, discharge destination, cost, or satisfaction score.</footer>
        """,
    )
    risk = _page(
        "Risk tiers and where to act",
        f"""
        <section class="kpis">
          <article class="card kpi"><div class="label">High-risk tier</div><div class="value">{_pct(tiers['High']['rate'])}</div><div class="note">{tiers['High']['encounters']:,} encounters</div></article>
          <article class="card kpi"><div class="label">Medium-risk tier</div><div class="value">{_pct(tiers['Medium']['rate'])}</div><div class="note">{tiers['Medium']['encounters']:,} encounters</div></article>
          <article class="card kpi"><div class="label">Low-risk tier</div><div class="value">{_pct(tiers['Low']['rate'])}</div><div class="note">{tiers['Low']['encounters']:,} encounters</div></article>
          <article class="card kpi"><div class="label">Logistic AUC</div><div class="value">{results['model']['auc_logit']:.3f}</div><div class="note">Gradient boosting {results['model']['auc_gb']:.3f}</div></article>
        </section>
        <div class="grid">
          <section class="card">
            <h2>Longest stays by recorded specialty</h2>
            {_bar_rows(list(b02['medical_specialty']), [f"{v:.1f}d" for v in b02['avg_stay']], list(b02['avg_stay']), max_value=10)}
          </section>
          <section class="card">
            <h2>Utilisation segments</h2>
            {_bar_rows([row['segment'] for row in segments], [f"{row['rate'] * 100:.1f}%" for row in segments], [row['rate'] * 100 for row in segments], max_value=80)}
          </section>
        </div>
        <section class="card">
          <h2>Actions supported by this file</h2>
          <ul>
            <li>Call the high-risk tier within 48 hours and arrange a visit within 7 days. Do not use the score to deny care.</li>
            <li>Flag two or more prior emergency visits, a diabetic medication change, and eight or more diagnoses.</li>
            <li>Pharmacist review when 20 or more medications were prescribed, or when diabetic therapy changed.</li>
            <li>Make specialty and weight required fields. Add admission dates, discharge disposition, cost, and satisfaction before those questions can be answered.</li>
          </ul>
        </section>
        <footer>Tiers are out-of-fold terciles from the 13-variable logistic model. Race and gender are not inputs.</footer>
        """,
    )
    (folder / "overview.html").write_text(overview, encoding="utf-8")
    (folder / "risk.html").write_text(risk, encoding="utf-8")
