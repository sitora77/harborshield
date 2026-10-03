# Joint-risk methodology · v0.2

## Decision problem and units

Compare three illustrative service alternatives, not navigable vessel paths:
Direct, Busan transshipment and Klang+road. Cargo value, freight, premium,
carbon and delay costs are **per container**. A 20-container default batch has
USD5 million of cargo value, not USD250,000 in total. Monetary units are USD.

The map joins illustrative port coordinates; lines can cross land and must not
be used as safe sailing routes. Carbon is assumed kg CO₂ per container, not
voyage-level measured emissions. The USD80/tonne shadow price is not a tax quote.

## Correct empirical CVaR

For S equal-weight losses, upper CVaR is

```text
CVaR_α(L) = min_η [η + Σ_s max(L_s−η,0) / ((1−α)S)], α=0.95
```

Implementation sorts losses descending and averages the largest (1−α)S sample
mass, with a fractional weight at the boundary. This handles ties correctly.
Averaging every value above an interpolated P95 is not equivalent. For example,
99 zeros and one USD100 loss have CVaR95=USD20, not USD1.
Percentiles remain descriptive linear-interpolation quantiles.

Basis: [Rockafellar & Uryasev (2000)](https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf)
and [general loss distributions (2002)](https://sites.math.washington.edu/~rtr/papers/rtr187-CVaR2.pdf).
Tests independently compare sorting CVaR to the variational objective.

## Insurance consistency

For severity X~Triangular(a,m,b), a=0.03, b=0.88, m depends on cargo type.
Coverage q, deductible fraction d, cargo value V and claim probability p give
premium=1.25×p×V×q×E[(X−d)+]. The exact stop-loss mean is

```text
d ≤ a:        (a+m+b)/3 - d
a < d ≤ m:    (a+m+b)/3 - d + (d-a)^3 / [3(b-a)(m-a)]
m < d < b:    (b-d)^3 / [3(b-a)(b-m)]
d ≥ b:        0
```

The loading and deductible-first contract convention are assumptions, not
insurer rates. Real exclusions, limits and franchises are not represented.

## Shared-shock construction

Each world samples a common standard-normal Z_s. For route r and potential
container k, with independent standard-normal ε_srk and ν_sr:

```text
H_srk = sqrt(ρ) Z_s + sqrt(1−ρ) ε_srk
claim_srk = 1[H_srk > Φ⁻¹(1−p_r)]
G_sr = sqrt(ρ) Z_s + sqrt(1−ρ) ν_sr
D_sr = max(0, μ_r + σ_r G_sr)
```

These variables preserve the original marginal claim probability and delay
distribution. Positive common shocks increase both claims and delay; conditional
severities remain independent triangular draws. ρ is an assumed **latent**
dependence parameter, not the realised claim/cost correlation or a fitted value.

All containers assigned to a route share one sailing delay. At ρ=0, cross-route
common shocks and claim dependence vanish, but same-route delay dependence
remains. At ρ=1, claim and delay latent shocks are fully shared, not severities.
This is not an estimate of historical port/weather correlation.

For route r, the first k potential containers' cumulative costs are stored.
Allocation x has L_s(x)=Σ_r Σ_{k≤x_r} cost_srk. Container order is fixed before
selection and cannot be rearranged after observing outcomes. Container identities
are exchangeable in the assumed population; finite sample optima vary by seed.
Identical worlds are used for every candidate (common random numbers).

## Finite-action sample-average optimisation

```text
min_x mean_s L_s(x) + λ [CVaR95_s L_s(x) − mean_s L_s(x)]
subject to:
  x_1+x_2+x_3 = N; x_r are non-negative integers
  x_r ≤ floor(N × maximum route share)
  Σ_r x_r × (planned duration_r + E[D_r]) / N ≤ transit limit
```

λ∈[0,1] is a convex combination of mean and CVaR. For D=max(0, μ+σZ),
E[D]=μΦ(μ/σ)+σφ(μ/σ), not exactly μ. The analytical mean is used in constraints.
The route-share cap is never rounded up to force feasibility.

Every feasible allocation is evaluated in memory-bounded chunks. Three routes
and N≤100 give at most 5,151 candidates before caps. This returns the global
optimum of the **sampled** finite objective, not a real-world optimum. No new
optimisation algorithm is claimed. Mean-transit feasibility is not a deadline
or service-level guarantee. The Pareto chart is a **training** frontier.

The original CP-SAT optimiser is retained as a labelled additive-tail baseline;
its scaled transit constraint rounds conservatively. The research comparison
evaluates an additive proxy on the same training worlds. That is not the exact
CP-SAT dashboard run, which uses separate single-route simulations.

## Evaluation protocol

Four policies share training worlds and constraints: joint mean–CVaR, cost-only
(λ=0), closest feasible balanced allocation (squared distance to equal thirds,
ties broken by training mean), and additive standalone-tail proxy.

Policies are frozen before 10,000 separate synthetic worlds, seed 20261004.
Training seeds: 11,22,33,44,55. Dependence sweep: 0,0.35,0.7,0.95. Sample sizes:
200,500,1000,2500 (not nested). The report fixes a 30-day mean constraint across
all four regimes; the dashboard defaults to 22 days and can show infeasibility.

Mean intervals use a normal Monte Carlo approximation. Joint-minus-cost
differences use a paired percentile bootstrap with 200 resamples. Test worlds
are shared across policies, so their results are paired. Intervals cover
simulation noise conditional on selected policies and the model, not calibration
uncertainty, training-selection uncertainty or distribution shift. An interval
spanning zero does not establish improvement. Two hundred bootstrap draws are
an exploratory default; rare-tail inference warrants larger sensitivity checks.

Training-seed stability and held-out results are reported separately. No route
assumptions or hyperparameters were tuned on held-out performance. Same-distribution
**independent synthetic evaluation is not empirical or predictive validation**.
See the [generated report](EXPERIMENT_REPORT.md).

## Scope boundaries

Single-route MCDA uses claim probability as its risk criterion, distinct from
joint CVaR. Cross-scenario rank summaries are descriptive, not formal robust
optimisation over unknown regime probabilities. The genuine MPA arrivals series
is context only and does not calibrate congestion, claims or joint cost.

Historical claims, actual quotes, AIS waiting times, weather, road networks and
measured emissions remain unintegrated. Gaussian dependence, homogeneous cargo,
one sailing per route and static premiums are simplifications. There is no
demonstrated real-world saving, causal congestion estimate or insurer endorsement.
