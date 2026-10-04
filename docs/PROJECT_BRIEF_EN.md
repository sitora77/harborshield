# HarborShield — maritime disruption, replenishment and working capital

A transparent, AI-assisted decision-support learning project connecting maritime
operations with supply-chain management and digital trade finance.

[English interactive case](https://sitorastudio.com/case-study-en.html) ·
[Chinese case](https://sitorastudio.com/case-study.html) ·
[Real-data forecast evidence](https://sitorastudio.com/real-data-en.html) ·
[Source code](https://github.com/sitora77/harborshield)

## Problem

A replenishment order can have an attractive planned margin yet run short of cash
before customers pay. A cheaper sea service may also arrive too late to prevent
stockouts. HarborShield asks which constructed transport option has the lowest
economic burden **among options meeting an assumed funding limit, availability
deadline and minimum net economic contribution**. It makes no recommendation if
no option meets all three criteria.

## Case and evidence

The historical setting is Singapore’s port congestion in May 2024. The official
[MPA statement](https://www.mpa.gov.sg/media-centre/details/in-response-to-media-queries-on--vessels--extended-waiting-times-for-berths-in-the-port-of-singapore)
reports that most container ships berthed on arrival; where schedule adjustment
was infeasible, average waiting was about 2–3 days. That conditional observation
motivates a 2.5-day case assumption. It does not calibrate a delay distribution.

The order is constructed: 5,000 units, US$150,000 purchase value, US$210,000
assumed sales, US$25,000 own cash, a 30% supplier deposit on day −7, and collection
14 days after availability. Freight, insurance premiums, financing rates, service
times and demand are assumptions, not company records or market quotations.

## Method

The deterministic case combines transit, port exposure and document-release time
to estimate stock availability. Unmet pre-arrival demand is capped by the order
quantity and valued at the unit contribution margin. This opportunity cost is
not entered as a second cash outflow. The eventual full order receipt remains a
separate, explicit simplifying assumption.

An event ledger nets same-day flows and integrates negative incremental balances
to compute simple ACT/365 funding interest. Peak external funding already deducts
own cash. Economic burden adds logistics, funding interest and stockout opportunity
cost; net economic contribution is not audited accounting profit.

At the default assumptions, the hypothetical priority option has economic burden
of US$5,972.65 and peak funding need of US$130,200. A US$129,000 funding limit and
day-15 deadline instead admit standard sea as the lowest-burden eligible option.
Tightening that deadline to day 12 leaves no eligible option. These are computed
conditional results, not achieved savings or evidence of available credit.

## Digital trade-document demonstration

The local app generates structured invoice, packing-list and insurance-request
JSON from the same constructed order. It checks identifiers, currency, SKU
quantities, arithmetic, declared values and strictly formatted cover dates. The
checked bundle can be DEMO-signed with Ed25519 using cryptography. Its context
includes case inputs, a SHA-256 input digest and the screening decision.

A changed amount fails verification. A replacement-key signature can be
mathematically valid but fail the separately supplied original-key anchor.
Signatures establish integrity relative to a key, not cargo existence, insurance
coverage or an issuer’s real identity. Invalid uploads block signing. Uploaded
bundles remain separate DEMO inputs; their assertions are not certified.

The [2023 TradeTrust transaction](https://www.tradetrust.io/happenings-and-resources/press-release-singapore-india-kick-off-interoperable-ebills-of-lading-for-trade-finance/)
and [TrustVC](https://github.com/TrustVC/trustvc) provide workflow and architecture
references only. HarborShield has no bank, TradeTrust, blockchain or legally
effective eBL/title-transfer integration. Its JSON envelope is project-local.

## Research layer and verification

A separate synthetic maritime-risk layer models shared cargo and sailing shocks,
compares four allocation policies, and evaluates frozen decisions on independent
synthetic samples. Its CVaR formulation follows
[Rockafellar and Uryasev](https://doi.org/10.21314/JOR.2000.038). Those model tests
are not validation against observed insurance claims or actual port operations.

The repository includes reproducible case outputs, 27 deterministic sensitivity
settings and four feasibility examples. Browser and Python calculations are
cross-checked. Automated tests cover cash-flow reconciliation, binding limits,
no-eligible decisions, date portability, same-order documents, signature trust
boundaries and dashboard interactions. Both display languages use one template
and one browser calculator; switching language preserves the selected inputs.

## Separate real-data evidence

The v0.5 module uses 1,096 daily, AIS-derived Singapore container-ship port-call
observations from [IMF PortWatch](https://portwatch.imf.org/datasets/83b1bbc7b3354c5fb1f40673bb8f852e/about).
It trains on 2022, selects one of five methods on 2023 MAE, then evaluates
366 rolling one-day-ahead targets in 2024. Raw source responses, retrieval
metadata and checksums are retained; missing dates and invalid counts block analysis.

The selected previous-28-day average achieves 2024 MAE 3.29 calls/day, compared
with 4.80 for yesterday's count, a 31.4% lower error on this fixed snapshot.
It also outperforms the fixed ridge candidate. This is a measured activity
forecast result, not classification accuracy, a congestion effect or financial
savings. Earlier observed test days may enter lags; future targets do not.
The snapshot was downloaded later and may contain historical revisions;
contemporaneous real-time data availability is not validated.

Connecting the activity forecast to a real replenishment/finance decision still
requires matched waiting-time, delivery, demand, quotation and payment records.
No automatic port-call-to-delay mapping is used. The real activity experiment
does not validate the separate constructed cargo-insurance or working-capital models.
[Full report and limitations](REAL_DATA_REPORT.md).

## Academic relevance and limits

- SCM: replenishment, inventory exposure and disruption response under constraints.
- FinTech: structured trade-data consistency, signatures and issuer-key boundaries.
- Finance/business: liquidity timing, funding needs and conditional contribution.
- Maritime, ISE and intelligent transportation: transport alternatives and risk allocation.

This is an educational prototype, not a company pilot, actuarial pricing system,
credit score, investment model or proof of enterprise impact. No confidential
company documents were available. Substantial AI assistance is disclosed; the
owner should claim only the experiments and methods they can personally explain,
reproduce and defend. No completed personal learning record is implied here.

Version 0.5 · 4 October 2026.
