# Literature, open-source, and data traceability

This document records what informed HarborShield and, equally importantly,
what was **not** copied or claimed. Initial sources were reviewed on 26 September
2026; the v0.2 additions were checked on 4 October 2026 with the free arXiv API,
author-hosted papers, GitHub and official documentation. No Firecrawl was used
for the v0.2 additions.

## v0.2 sources mapped to implementation

| Primary source | Implemented use | Boundary |
|---|---|---|
| Rockafellar & Uryasev (2000), *Optimization of Conditional Value-at-Risk*, [DOI](https://doi.org/10.21314/JOR.2000.038), [author-hosted preprint](https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf) | Variational CVaR and scenario-based loss optimisation. | Finite whole-container enumeration, not the financial application or a copied solver. |
| Rockafellar & Uryasev (2002), *Conditional Value-at-Risk for General Loss Distributions*, [preprint](https://sites.math.washington.edu/~rtr/papers/rtr187-CVaR2.pdf) | Fractional tail mass and tied-loss handling; independent CVaR identity tests. | Does not equate all values above an interpolated P95 with the worst 5% mass. |
| El Karoui, Lim & Vahn, *Performance-based regularization in mean-CVaR portfolio optimization*, [arXiv:1111.2091v2](https://arxiv.org/abs/1111.2091v2) | Motivates reporting estimation risk, seed instability and separate evaluation. | PBR regularisation and asymptotic results are not implemented or claimed. |
| [PyPortfolio/PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt), MIT; [official CVaR documentation](https://pyportfolioopt.readthedocs.io/en/latest/GeneralEfficientFrontier.html#efficient-cvar) | Scenario-based CVaR implementation comparison. | Not a dependency; no code copied. Shipping costs and integer containers differ from fractional financial returns. |
| [ccolon/disrupt-sc](https://github.com/ccolon/disrupt-sc), GPL-3.0 | System-level supply-chain disruption and transport-dependency reference. | Conceptual only; no GPL code copied into this MIT repository; no agent-based economy implemented. |

The Gaussian shared shocks, premium correction and finite-action enumeration
are explicit prototype modelling/engineering choices, not fitted parameters
from these papers. The maritime resilience review was rechecked via arXiv
metadata; it motivates regime coverage, not claim pricing.

## Research literature

| Source | What it contributes to the project | How HarborShield uses it |
|---|---|---|
| Redekar, Askin & Ju, *Maritime Port Supply Chain Resilience: A Systematic Review* ([arXiv:2510.09844v1](https://arxiv.org/abs/2510.09844v1)) | Frames maritime-port resilience across operational and technology dimensions and a broad disruption set. | Motivates cross-scenario stress testing and the separation of normal operations, weather, congestion, and chokepoint disruption. |
| Li et al., *Temporal-IRL: Modeling Port Congestion and Berth Scheduling with Inverse Reinforcement Learning* ([arXiv:2506.19843v1](https://arxiv.org/abs/2506.19843v1)) | Shows why vessel behaviour, waiting time, terminal state, and AIS-derived berth schedules matter for congestion modelling. | Supports the roadmap toward AIS/berth-level validation; the present MPA arrivals series is explicitly labelled only as an activity proxy. |
| Chen et al., *Learning Large Neighborhood Search for Maritime Inventory Routing Optimization* ([arXiv:2502.15244v2](https://arxiv.org/abs/2502.15244v2)) | Treats maritime inventory routing as a difficult combinatorial optimisation problem and evaluates advanced search methods. | Motivates an optimisation layer. HarborShield currently uses a smaller, interpretable integer allocation model suitable for the available data and application timeline. |
| Chiang, Lin & Long, *Efficient Propagation of Uncertainties in Manufacturing Supply Chains* ([arXiv:1808.07121v2](https://arxiv.org/abs/1808.07121v2)) | Studies stochastic supply-chain simulation and efficient uncertainty propagation with Monte Carlo methods. | Supports reporting distributions and tail outcomes instead of only deterministic averages. HarborShield uses ordinary Monte Carlo and CVaR95 because its educational network is small. |
| Deriba & Yang, *Performance-Based Risk Assessment for Large-Scale Transportation Networks Using the Transitional Markov Chain Monte Carlo Method* ([arXiv:2411.03580v1](https://arxiv.org/abs/2411.03580v1)) | Highlights low-probability/high-consequence states and system-performance-based transportation risk. | Motivates tail-cost reporting, worst-case comparison, and scenario robustness. HarborShield does not implement TMCMC. |
| Marijan, Mohammed & Zaman, *Estimation and Optimization of Ship Fuel Consumption in Maritime: Review, Challenges and Future Directions* ([arXiv:2602.21959v1](https://arxiv.org/abs/2602.21959v1)) | Reviews physics-based, machine-learning, and hybrid fuel estimation and the value of AIS, sensor, and meteorological data fusion. | Motivates the carbon/fuel roadmap and the decision to keep current emissions inputs explicitly simulated until suitable voyage data are integrated. |

These papers motivate the **problem formulation and method family**. The risk
coefficients in `harborshield/models.py` were not estimated or copied from these
papers; they are transparent teaching assumptions awaiting calibration.

## Open-source comparison

| Repository | Licence observed | Relevance | Use in HarborShield |
|---|---|---|---|
| [google/or-tools](https://github.com/google/or-tools) | Apache-2.0 | Integer programming, routing, scheduling | Direct dependency for container portfolio allocation. |
| [gboeing/osmnx](https://github.com/gboeing/osmnx) | MIT | OpenStreetMap street-network acquisition and analysis | Planned land-side network extension; no code copied. |
| [eclipse-sumo/sumo](https://github.com/eclipse-sumo/sumo) | EPL-2.0 | Microscopic and intermodal traffic simulation | Evaluated as a future truck/port-gate simulation engine; not bundled. |
| [a-b-street/abstreet](https://github.com/a-b-street/abstreet) | Apache-2.0 | Interactive transport scenario exploration | Interface and scenario-analysis reference; no code copied. |
| [windmar-nav/windmar-demo](https://github.com/windmar-nav/windmar-demo) | Apache-2.0 | Weather-aware maritime routing and vessel performance | Conceptual reference for a future weather-routing layer; no code copied. |
| [samirsaci/supply-chain-optimization](https://github.com/samirsaci/supply-chain-optimization) | No licence detected | Python supply-chain optimisation examples | Ideas reviewed only. No code reused because absence of a licence does not grant reuse rights. |
| [hzjken/multimodal-transportation-optimization](https://github.com/hzjken/multimodal-transportation-optimization) | No licence detected | Mathematical programming for multimodal freight | Ideas reviewed only. No code reused. |

HarborShield's Python implementation was written specifically for this project.
Licence metadata above was checked through the GitHub API; repositories can
change, so re-check before future reuse.

## Public and planned data sources

| Source | Status | Intended role |
|---|---|---|
| [MPA vessel arrivals via data.gov.sg](https://data.gov.sg/datasets/d_d48c5a038904f6da3c603cd854b6c191/view) | Integrated snapshot | Singapore port-activity context and reproducible public-data pipeline. |
| [UNCTAD Maritime Transport via World Bank Data360](https://data360.worldbank.org/en/dataset/UNCTAD_MT) | Documented, not yet integrated | Connectivity, fleet, trade, and maritime transport indicators. |
| [UNCTAD Review of Maritime Transport 2025](https://unctad.org/publication/review-maritime-transport-2025) | Context source | Sector disruptions, port performance, decarbonisation, and policy context. |
| [NGA World Port Index](https://msi.nga.mil/Publications/WPI) | Planned | Traceable global port coordinates and port characteristics. |
| [Open-Meteo Marine Weather API](https://open-meteo.com/en/docs/marine-weather-api) | Planned | Wave and marine-weather scenario inputs with source acknowledgement. |

## Research-integrity rules

1. Simulated route inputs must remain labelled simulated.
2. Public datasets must include publisher, URL, retrieval date, fields, and transformations.
3. Vessel-arrival counts must not be called congestion or waiting time without validation.
4. Model coefficients must not be called trained, calibrated, or actuarial until suitable data and validation exist.
5. Application documents may describe implemented features and measured experiments only.
