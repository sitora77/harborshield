# HarborShield methodology

## 1. Decision problem

For a cargo shipment or container batch, compare routes that differ in freight
price, planned duration, transshipments, reliability, weather exposure, port
activity exposure, and emissions. The system should answer three questions:

1. Which route best matches a decision-maker's cost, risk, time, and carbon priorities?
2. Does that recommendation remain competitive under disruption scenarios?
3. How should a container batch be allocated when concentration and transit constraints apply?

## 2. Risk probability

An interpretable logistic model converts a linear risk score into a probability:

```text
p(claim) = 1 / (1 + exp(-z))
```

`z` combines cargo sensitivity, packaging quality, duration, transshipments,
weather exposure, congestion exposure, scenario disruption, and reliability.
Every sign and coefficient is visible in `claim_probability`. The coefficients
are illustrative assumptions, not estimates from insurance claims.

## 3. Monte Carlo uncertainty

For each route and scenario, the program repeats the shipment experiment:

1. Draw whether a cargo claim occurs using the estimated probability.
2. If it occurs, draw loss severity from a triangular distribution.
3. Calculate insurance payout after the deductible and coverage ratio.
4. Draw additional delay around a scenario-dependent mean.
5. Calculate freight, premium, retained loss, delay, and carbon cost.

The dashboard reports expected values, percentiles, and CVaR95 total cost. CVaR95
is the mean of the worst 5% simulated outcomes and is more informative than P90
when a rare cargo claim occurs in fewer than 10% of simulations. A fixed random
seed makes results reproducible.

## 4. Insurance treatment

```text
deductible = cargo value × deductible ratio
payout = coverage ratio × max(gross loss - deductible, 0)
retained loss = gross loss - payout
```

The illustrative premium combines probability, assumed average severity,
coverage, and a loading factor. It must not be treated as an insurance quote.

## 5. Multi-criteria route ranking

Cost, claim probability, total time, and carbon are min-max normalised across
candidate routes. User weights are normalised to sum to one. The decision score
is their weighted sum; lower is preferred.

This is a transparent weighted-sum MCDA method. It is easy to audit but is
sensitive to weights and the candidate set, which is why the application adds
a risk-weight sensitivity chart.

## 6. Stress testing and robustness

Every route is re-simulated under four scenarios. The robustness table reports:

- average rank;
- number of scenario wins;
- maximum claim probability;
- worst CVaR95 cost;
- average cost regret relative to the lowest-cost route in each scenario.

This prevents a single baseline recommendation from being presented as
universally optimal.

## 7. Container portfolio optimisation

The OR-Tools CP-SAT model chooses integer container allocations `x_r`:

```text
minimise Σ x_r × [expected cost_r + λ(CVaR95 cost_r - expected cost_r)]
subject to:
  Σ x_r = total containers
  x_r ≤ maximum route share × total containers
  weighted average transit time ≤ selected limit
  x_r is a non-negative integer
```

`λ` represents tail-risk aversion. The concentration constraint provides a
simple resilience mechanism by preventing the entire batch from depending on
one route.

## 8. Public port-activity data

The bundled MPA series is loaded from data.gov.sg. The activity-pressure index
equals the latest monthly vessel arrivals divided by the preceding 12-month
median. It is descriptive context only and is not automatically inserted into
the loss model.

## 9. Validation status

Implemented validation includes unit tests, deterministic random seeds,
monotonic adverse-scenario checks, feasibility checks for the integer model,
and an automated Streamlit render test.

Not yet completed:

- calibration against marine insurance claims;
- validation against port waiting times or AIS-derived berth events;
- carrier-quoted freight cost validation;
- voyage-level emissions calculation;
- out-of-sample predictive evaluation.

These limits are part of the project's research contribution: it demonstrates
an honest, reproducible decision framework and a concrete data-validation roadmap.
