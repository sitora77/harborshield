# Data provenance

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

