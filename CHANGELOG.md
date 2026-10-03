# Changelog

## 0.2.0 · 2026-10-04

- Corrected triangular-severity pricing: expected payout, including deductible,
  replaces the previous mode-as-mean approximation.
- Corrected empirical CVaR for ties and fractional boundary sample mass.
- Added shared latent-shock batch simulation, exact finite-action sample-average
  allocation, training Pareto frontier and four-policy held-out comparison.
- Added paired bootstrap intervals, seed stability, dependence sensitivity,
  training-size diagnostics and reproducible JSON/CSV/Markdown/HTML evidence.
- Labelled the existing CP-SAT additive-tail baseline; fixed route-share cap,
  route/result alignment and conservative transit rounding.
- Added input checks, all-zero-weight UI guidance and cached dashboard analysis.
- Added model/dashboard tests, research-source mapping, pinned top-level
  research requirements, inactive CI template and Chinese project explanation.
- Explicitly documented per-container units, AI assistance and the distinction
  between same-model synthetic evaluation and real-world validation.

## 0.1 · 2026-09-26

Initial public educational prototype with single-route simulation, MCDA,
stress scenarios, CP-SAT allocation and official MPA arrivals context.
Its historical report is archived as `docs/EXPERIMENT_REPORT_V0_1.md`; the old
premium approximation and cost numbers are superseded by v0.2.
