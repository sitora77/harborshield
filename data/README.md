# Data provenance

## `portwatch/`

1,096 daily observations from [IMF PortWatch Daily_Ports_Data](https://portwatch.imf.org/datasets/83b1bbc7b3354c5fb1f40673bb8f852e/about),
Singapore port1201 only, 2022-01-01 through 2024-12-31. AIS-derived container-ship
port-call counts, not waiting times, cargo claims or TEU. Raw paginated API
responses and snapshot SHA-256 checksums are retained; no missing dates or
counts are invented. See [source-data terms](portwatch/DATA_TERMS.md),
`portwatch/provenance.json` and the [real-data report](../docs/REAL_DATA_REPORT.md).
The noncommercial research subset keeps source attribution; MIT applies to code,
not third-party data. A later-retrieved historical snapshot may contain revisions.

## `sample_routes.csv`

Illustrative route alternatives created for this portfolio prototype. Costs,
durations, exposure indexes, reliability, and emissions are simulated and must
not be represented as carrier quotations or observed operational records.

## `mpa_vessel_arrivals_monthly.csv`

- Publisher: Maritime and Port Authority of Singapore (MPA), via data.gov.sg
- Dataset: Vessel Arrivals (>75 GT) Total, Monthly
- Dataset ID: `d_d48c5a038904f6da3c603cd854b6c191`
- Source: https://data.gov.sg/datasets/d_d48c5a038904f6da3c603cd854b6c191/view
- API: https://data.gov.sg/api/action/datastore_search?resource_id=d_d48c5a038904f6da3c603cd854b6c191
- Snapshot in repository: September 2023 through August 2026
- Retrieved: 26 September 2026

The field called `gross_tonnage_thousand` retains the source values and unit
description. The dashboard uses vessel arrivals only as an **activity-pressure
proxy**. It does not claim that vessel-arrival volume is a direct measurement
of queueing time or port congestion.

Run `python scripts/update_mpa_data.py` to refresh the snapshot from the
official API. Review upstream schema changes before committing an update.
