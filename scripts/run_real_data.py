#!/usr/bin/env python3
"""Reproduce the real-data experiment offline from a verified source snapshot."""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harborshield.portwatch import load_snapshot, run_backtest
from harborshield.portwatch_page import build_page


def build_markdown(report):
    selected = report["selected_method"]
    result = report["test"][selected]
    lines = ["# Real-data evidence: Singapore container-ship port calls", "",
             "Version 0.5 · historical one-day-ahead experiment, not a company pilot", "",
             f"Source: [IMF PortWatch Daily_Ports_Data]({report['source']['dataset']}). {report['source']['attribution']}", "",
             f"Snapshot: 1,096 UTC dates, 2022-01-01 through 2024-12-31, Singapore port1201 only. Retrieved {report['source']['retrieved_at_utc']}.", "",
             "Raw response bytes, pagination query URLs, source counts and SHA-256 checksums are retained in `data/portwatch/`. No dates/counts were interpolated or removed. Missing dates, duplicates, nulls and invalid counts block analysis rather than creating artificial zeros.", "",
             "## Fixed chronological protocol", "", report["protocol"], "",
             "Training: 365 days (2022). Validation: 365 days (2023). Final test: 366 days (2024, including leap day). Ridge uses lagged counts at 1, 2, 7, 14 and 28 days, weekday indicators, training-only standardisation, an unpenalised intercept and fixed penalty 10. Negative predictions are clipped to zero. Other methods have no fitted coefficients. Ties use the documented method order.", "",
             "## Results — all daily targets", "",
             "| Method | 2023 selection MAE | 2024 test MAE | 2024 RMSE | 2024 WAPE |", "|---|---:|---:|---:|---:|"]
    for method, name in report["method_names"].items():
        row = report["test"][method]
        mark = " **(selected before test)**" if method == selected else ""
        lines.append(f"| {name}{mark} | {report['validation'][method]['mae']:.4f} | {row['mae']:.4f} | {row['rmse']:.4f} | {row['wape']:.2%} |")
    lines.extend(["", "MAE/RMSE units: container-ship port calls per UTC day. WAPE = sum of absolute daily errors / sum of daily observed calls; it is not mean daily percentage error or classification accuracy.", "",
                  f"The method selected on 2023 is **{report['method_names'][selected]}**. Its 2024 MAE is {result['mae']:.4f}, versus {report['test']['yesterday']['mae']:.4f} for yesterday's count: a {report['mae_improvement_vs_yesterday']:.2%} error reduction on this fixed dataset. Ridge does not beat the selected simple average on the final test. No operational or monetary benefit is inferred.", "",
                  "The website chart shows weekly averages for legibility, retaining partial first/last weeks. Report metrics and downloadable forecasts are daily. Month-by-month diagnostics are in the JSON and dashboard; these are descriptive, not additional model selection.", "",
                  "## Scope and limitations", "", *["- " + value for value in report["limitations"]], "",
                  "AIS-derived port calls measure entries into the publisher's port boundary, not TEU, unique vessels or customs cargo value. These estimates can be affected by AIS coverage and revisions. MPA monthly totals have a different publisher, scope and method; they are not used as day-level ground-truth labels here.", "",
                  "## Reproduce offline", "", "```bash", "python scripts/run_real_data.py", "python -m unittest discover -s tests -v", "```", "",
                  "Refresh only when intentionally updating the snapshot: `python scripts/fetch_portwatch.py`. Optional `--transport curl` uses the same queries where urllib responses are truncated. An upstream change changes the snapshot hash and may change results; commit source and rebuilt reports together. Offline reproduction needs no credentials or network.", "",
                  "## References and data rights", "",
                  "- [Arslanalp, Koepke and Verschuur (2021), Tracking Trade from Space, IMF Working Paper 2021/225](https://www.imf.org/en/Publications/WP/Issues/2021/08/20/Tracking-Trade-from-Space-An-Application-to-Pacific-Island-Countries-464345). Source methodology reference, not a forecast paper being replicated.",
                  "- [World Bank port-call monitoring example](https://worldbank.github.io/alternative-data-for-crisis/notebooks/disruptions-business-trade/port-calls-trends-monitor.html). Reference for public port activity analysis and paginated extraction; no code copied.",
                  "- [IMF copyright/data terms](https://www.imf.org/en/about/copyright-and-terms). The code's MIT licence does not relicense source data. Preserve attribution and transformations; consult source terms for other or commercial uses. No IMF endorsement is implied.", "",
                  "AI-assisted implementation is disclosed. The owner's own learning/replication log is intentionally not filled in by the assistant.", ""])
    return "\n".join(lines)


def main():
    rows, metadata = load_snapshot(ROOT / "data/portwatch")
    report = run_backtest(rows, metadata)
    target = ROOT / "reports"
    target.mkdir(exist_ok=True)
    (target / "real-data-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    (ROOT / "docs/REAL_DATA_REPORT.md").write_text(build_markdown(report), encoding="utf-8")
    for language, name in (("zh", "real-data.html"), ("en", "real-data-en.html")):
        (target / name).write_text(build_page(report, language), encoding="utf-8")
    shutil.copyfile(ROOT / "web/real-data.css", target / "real-data.css")
    selected = report["selected_method"]
    print(json.dumps({"rows": len(rows), "selected_on_2023": selected, "test_2024": report["test"],
                      "mae_improvement_vs_yesterday": report["mae_improvement_vs_yesterday"]}, indent=2))


if __name__ == "__main__":
    main()
