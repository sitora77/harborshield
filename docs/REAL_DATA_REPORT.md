# Real-data evidence: Singapore container-ship port calls

Version 0.5 · historical one-day-ahead experiment, not a company pilot

Source: [IMF PortWatch Daily_Ports_Data](https://portwatch.imf.org/datasets/83b1bbc7b3354c5fb1f40673bb8f852e/about). Sources: UN Global Platform; IMF PortWatch (portwatch.imf.org).

Snapshot: 1,096 UTC dates, 2022-01-01 through 2024-12-31, Singapore port1201 only. Retrieved 2026-10-04T14:34:46+00:00.

Raw response bytes, pagination query URLs, source counts and SHA-256 checksums are retained in `data/portwatch/`. No dates/counts were interpolated or removed. Missing dates, duplicates, nulls and invalid counts block analysis rather than creating artificial zeros.

## Fixed chronological protocol

Choose by 2023 validation MAE. Refit ridge on 2022–2023 only; freeze coefficients. Each 2024 forecast uses observed earlier days, not the current or future target. This is rolling one-day-ahead evaluation, not a year-ahead forecast. Historical records downloaded later may be revised; this is not an as-of-2024 vintage backtest.

Training: 365 days (2022). Validation: 365 days (2023). Final test: 366 days (2024, including leap day). Ridge uses lagged counts at 1, 2, 7, 14 and 28 days, weekday indicators, training-only standardisation, an unpenalised intercept and fixed penalty 10. Negative predictions are clipped to zero. Other methods have no fitted coefficients. Ties use the documented method order.

## Results — all daily targets

| Method | 2023 selection MAE | 2024 test MAE | 2024 RMSE | 2024 WAPE |
|---|---:|---:|---:|---:|
| Yesterday's observed count | 4.8000 | 4.7951 | 5.9481 | 12.86% |
| Same weekday last week | 4.5397 | 4.5984 | 5.8462 | 12.33% |
| Previous 28-day mean **(selected before test)** | 3.4568 | 3.2906 | 4.1748 | 8.82% |
| Same weekday, previous four weeks | 3.6048 | 3.6530 | 4.6314 | 9.79% |
| Ridge autoregression (fixed penalty 10) | 3.9346 | 3.4616 | 4.3969 | 9.28% |

MAE/RMSE units: container-ship port calls per UTC day. WAPE = sum of absolute daily errors / sum of daily observed calls; it is not mean daily percentage error or classification accuracy.

The method selected on 2023 is **Previous 28-day mean**. Its 2024 MAE is 3.2906, versus 4.7951 for yesterday's count: a 31.38% error reduction on this fixed dataset. Ridge does not beat the selected simple average on the final test. No operational or monetary benefit is inferred.

The website chart shows weekly averages for legibility, retaining partial first/last weeks. Report metrics and downloadable forecasts are daily. Month-by-month diagnostics are in the JSON and dashboard; these are descriptive, not additional model selection.

## Scope and limitations

- Port calls are AIS-derived indicators, not observed port waiting times, cargo delays or losses.
- No observed invoices, carrier quotations, claims, premiums or funding costs are available.
- No causal congestion effect, calibrated insurance price or realised operational savings is established.
- One port, one held-out year and a later-retrieved data vintage; external generalisation is untested.
- No automatic mapping from predicted calls to the constructed order's port-delay assumption.
- AI-assisted implementation; personal learning and independent replication remain to be documented.

AIS-derived port calls measure entries into the publisher's port boundary, not TEU, unique vessels or customs cargo value. These estimates can be affected by AIS coverage and revisions. MPA monthly totals have a different publisher, scope and method; they are not used as day-level ground-truth labels here.

## Reproduce offline

```bash
python scripts/run_real_data.py
python -m unittest discover -s tests -v
```

Refresh only when intentionally updating the snapshot: `python scripts/fetch_portwatch.py`. Optional `--transport curl` uses the same queries where urllib responses are truncated. An upstream change changes the snapshot hash and may change results; commit source and rebuilt reports together. Offline reproduction needs no credentials or network.

## References and data rights

- [Arslanalp, Koepke and Verschuur (2021), Tracking Trade from Space, IMF Working Paper 2021/225](https://www.imf.org/en/Publications/WP/Issues/2021/08/20/Tracking-Trade-from-Space-An-Application-to-Pacific-Island-Countries-464345). Source methodology reference, not a forecast paper being replicated.
- [World Bank port-call monitoring example](https://worldbank.github.io/alternative-data-for-crisis/notebooks/disruptions-business-trade/port-calls-trends-monitor.html). Reference for public port activity analysis and paginated extraction; no code copied.
- [IMF copyright/data terms](https://www.imf.org/en/about/copyright-and-terms). The code's MIT licence does not relicense source data. Preserve attribution and transformations; consult source terms for other or commercial uses. No IMF endorsement is implied.

AI-assisted implementation is disclosed. The owner's own learning/replication log is intentionally not filled in by the assistant.
