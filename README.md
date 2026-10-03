# HarborShield

**A risk-aware decision-support prototype for maritime cargo insurance and intermodal logistics.**

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-1f6feb)](https://www.python.org/)
[![Licence: MIT](https://img.shields.io/badge/Licence-MIT-2ea44f)](LICENSE)

**v0.2:** joint batch CVaR, common disruption shocks, independent synthetic
evaluation, four policy comparisons, confidence intervals and reproducible reports.
[Read the experiment evidence](docs/EXPERIMENT_REPORT.md).

![Joint-risk research lab with held-out policy comparison](assets/research-lab.png)

The screenshot shows synthetic default inputs. The public portfolio hosts a
[static evidence page](https://sitorastudio.com/experiment.html); the interactive
Streamlit application runs locally unless separately deployed on a Python host.

HarborShield compares candidate cargo routes by combining shipment characteristics,
marine risk, insurance coverage, delay uncertainty, logistics cost, and carbon
emissions. It was designed as a transparent educational project at the intersection
of maritime technology, industrial systems engineering, supply-chain management,
and intelligent transportation.

## System overview

```mermaid
flowchart LR
    A[Shipment profile] --> D[Risk model]
    B[Simulated route alternatives] --> D
    C[Disruption scenario] --> D
    D --> E[Monte Carlo simulation]
    E --> F[Expected cost and CVaR95]
    F --> G[Multi-criteria ranking]
    E --> H[Joint batch loss + finite-action SAA]
    H --> L[Independent synthetic evaluation]
    I[MPA public vessel-arrival data] --> J[Port activity context]
    G --> K[Interactive decision dashboard]
    H --> K
    L --> K
    J --> K
```

## Why this project exists

Freight forwarders and cargo owners make decisions under uncertainty: a cheaper
route may involve more transshipments, a longer voyage, higher congestion exposure,
or a larger expected loss. HarborShield turns these trade-offs into an auditable
scenario analysis instead of presenting a black-box recommendation.

## Current research prototype

- Four disruption scenarios: normal operations, monsoon weather, port congestion,
  and strait disruption.
- Interpretable cargo-claim probability model.
- Reproducible Monte Carlo simulation of cargo loss and delays, including CVaR95 tail cost.
- Illustrative risk-based insurance premium and payout model.
- Multi-criteria route ranking across cost, risk, time, and carbon.
- Interactive dashboard, route map, cost breakdown, and CSV export.
- Cross-scenario stress testing, cost regret, and robust-route comparison.
- Risk-weight sensitivity analysis.
- Joint batch losses with correlated claims and shared sailing delays.
- Exact three-route sample-average allocation and cost–CVaR Pareto frontier.
- Independent 10,000-world synthetic evaluation against cost-only, balanced and additive-tail policies.
- Paired bootstrap intervals, five training seeds, dependence and sample-size diagnostics.
- OR-Tools integer allocation retained as a labelled additive-tail baseline.
- Insurance premium consistent with severity mean and deductible.
- Official monthly vessel-arrival data from Singapore's MPA/data.gov.sg.
- Automated tests for monotonic risk behaviour, reproducibility, and ranking.

## Run locally

Python 3.9 or newer is recommended.

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

## Run the model tests

Install the requirements first. Tests cover the model, joint samples, constraints,
CVaR identities and dashboard interactions.

```bash
python -m unittest discover -s tests -v
```

## Reproduce the research evidence

```bash
python -m pip install -r requirements-research.txt
python scripts/run_experiments.py
```

This creates unrounded JSON, comparison CSV, Markdown and static HTML evidence
in `reports/`. The pinned file records tested top-level libraries, not a complete
transitive lock. Test worlds are never used for policy selection. Baselines may
coincide; superiority or real-world savings are not assumed. Cargo value and
costs are per container, not per batch.

Local model and dashboard tests pass. A [CI template](ci/tests.yml.example)
is supplied, but GitHub Actions is **not yet enabled**: the current publishing
credential does not grant workflow modification. See [activation notes](ci/README.md).

## Project structure

```text
harborshield/
├── app.py                      # Streamlit interface
├── data/sample_routes.csv      # Clearly labelled simulated route inputs
├── data/mpa_vessel_arrivals_monthly.csv  # Official public-data snapshot
├── harborshield/models.py      # Risk, insurance, simulation, and ranking logic
├── harborshield/analysis.py    # Stress tests and sensitivity analysis
├── harborshield/optimization.py # OR-Tools container allocation
├── harborshield/joint_risk.py  # Shared shocks, exact SAA and held-out evaluation
├── harborshield/public_data.py # Public-data provenance calculations
├── scripts/update_mpa_data.py  # Refresh official MPA data
├── scripts/run_experiments.py # Reproduce the research evidence
├── reports/                   # JSON, CSV, Markdown and HTML artefacts
├── tests/test_models.py        # Automated model tests
└── docs/
    ├── LEARNING_GUIDE_ZH.md    # Beginner-friendly learning path
    ├── APPLICATION_NOTES.md    # Application and interview positioning
    ├── METHODOLOGY.md          # Equations, assumptions, and validation
    ├── EXPERIMENT_REPORT.md    # v0.2 synthetic evaluation evidence
    └── LITERATURE_AND_OPEN_SOURCE.md # Papers, repositories, and datasets
```

## Model boundaries and research integrity

The route values and coefficients in this MVP are simulated assumptions for
education and portfolio demonstration. They are **not** carrier quotations,
historical claims data, actuarial rates, or operational advice. A research-grade
extension should calibrate the model using licensed claims, weather, port-call,
congestion, and emissions data, then report uncertainty and validation results.

## Research and engineering notes

- [Methodology and equations](docs/METHODOLOGY.md)
- [Joint-risk methodology and evaluation](docs/JOINT_RISK_METHODOLOGY.md)
- [Literature, open-source, and data traceability](docs/LITERATURE_AND_OPEN_SOURCE.md)
- [Joint-risk experiment report](docs/EXPERIMENT_REPORT.md)
- [Beginner learning guide in Chinese](docs/LEARNING_GUIDE_ZH.md)
- [v0.2 project explanation in Chinese](docs/PROJECT_GUIDE_ZH.md)
- [Application positioning notes](docs/APPLICATION_NOTES.md)

## Development transparency

This prototype was built with substantial AI-assisted coding and documentation.
It is a learning/research portfolio, not evidence of independently authored code
or calibrated operational expertise. Applicant claims should reflect work that
the owner can explain, reproduce and defend personally.

## Planned extensions

1. Replace remaining simulated route values with traceable public datasets.
2. Assess parameter uncertainty and distribution shift beyond simulation noise.
3. Add AIS-derived port waiting times and berth-level validation.
4. Add marine-weather and land-side geospatial network analysis.
5. Validate assumptions through interviews with freight-forwarding practitioners.
