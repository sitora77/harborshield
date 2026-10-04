# Changelog

## 0.3.0 · 2026-10-04

- Added MPA Singapore 2024 delay and TradeTrust 2023 transaction source registers,
  with historical facts kept separate from constructed order and service inputs.
- Added replenishment opportunity cost, exact event-based working-capital ledger,
  simple negative-balance funding interest and 27 deterministic sensitivity cases.
- Added online browser calculator; checked agreement with Python default outputs,
  all sensitivity settings, cash/demand/rate boundaries and invalid inputs.
- Added structured JSON invoice/packing/insurance consistency rules and eight
  deliberately seeded fixtures (not a real-document accuracy benchmark).
- Added standalone Ed25519 demo: content tampering and replacement-key trust
  checks, temporary in-memory keys and no exported private keys.
- Added local case/document tabs, reproducible case report and Chinese learning
  guide. No bank/TradeTrust integration, credit model or enterprise deployment.

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
