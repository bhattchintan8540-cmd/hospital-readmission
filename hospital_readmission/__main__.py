"""Run the Kaggle-file analysis and write the workbook and report."""

from __future__ import annotations

import sys
from pathlib import Path

from hospital_readmission.analyze import analyze
from hospital_readmission.dashboard import write_dashboard
from hospital_readmission.prepare import load
from hospital_readmission.report import write_report
from hospital_readmission.workbook import write_workbook

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "source_rows": 66587,
    "duplicate_rows_removed": 17676,
    "analysis_rows": 48911,
    "unique_patients": 39650,
    "readmitted_n": 22609,
}


def main() -> int:
    df, meta = load()
    for key, expected in EXPECTED.items():
        actual = meta[key]
        if actual != expected:
            raise SystemExit(f"{key} is {actual}, the Kaggle file and solution guide both require {expected}")
    if meta["x1_none"] == 0 or meta["x2_none"] == 0:
        raise SystemExit("X1/X2 text value None was lost. Reload with keep_default_na=False.")
    results = analyze(df, meta)
    if results["checks"]:
        raise SystemExit("Validation failed:\n" + "\n".join(results["checks"]))
    out = ROOT / "outputs"
    write_workbook(out / "Hospital_Readmission_Analysis.xlsx", results)
    write_report(out / "RESULTS.md", results)
    write_dashboard(results, ROOT / "dashboard")
    print(
        f"encounters={meta['analysis_rows']} readmitted={meta['readmitted_n']} "
        f"auc={results['model']['auc_logit']:.3f} gb={results['model']['auc_gb']:.3f}"
    )
    print(f"wrote {out / 'Hospital_Readmission_Analysis.xlsx'}")
    print(f"wrote {out / 'RESULTS.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
