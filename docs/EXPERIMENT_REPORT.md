# Baseline experiment report

Run date: 26 September 2026

## Configuration

- Cargo value: US$250,000
- Cargo: electronics
- Packaging quality: 3/5
- Insurance coverage: 90%
- Deductible: 1%
- Delay cost: US$500/day
- Simulation: 2,500 iterations per route and scenario
- Decision weights: cost 40%, risk 30%, time 20%, carbon 10%

All route parameters are simulated. The experiment demonstrates model behaviour;
it does not estimate real carrier performance or insurance rates.

## Scenario results

| Scenario | Rank | Route | Claim probability | Expected cost | CVaR95 cost | Decision score |
|---|---:|---|---:|---:|---:|---:|
| Normal operations | 1 | Direct ocean service | 3.55% | US$6,882 | US$15,491 | 12.8 |
| Normal operations | 2 | Busan transshipment | 3.10% | US$6,878 | US$14,958 | 26.0 |
| Normal operations | 3 | Port Klang + road | 4.16% | US$7,819 | US$18,214 | 97.1 |
| Monsoon weather | 1 | Busan transshipment | 4.14% | US$9,571 | US$19,822 | 26.0 |
| Monsoon weather | 2 | Direct ocean service | 6.28% | US$10,808 | US$23,875 | 54.0 |
| Monsoon weather | 3 | Port Klang + road | 6.37% | US$11,535 | US$24,107 | 97.0 |
| Port congestion | 1 | Busan transshipment | 4.14% | US$11,151 | US$21,919 | 26.0 |
| Port congestion | 2 | Direct ocean service | 6.30% | US$12,393 | US$25,891 | 51.7 |
| Port congestion | 3 | Port Klang + road | 6.37% | US$13,336 | US$27,226 | 98.2 |
| Strait disruption | 1 | Direct ocean service | 6.30% | US$13,508 | US$26,793 | 24.4 |
| Strait disruption | 2 | Busan transshipment | 4.61% | US$13,492 | US$24,855 | 26.0 |
| Strait disruption | 3 | Port Klang + road | 6.72% | US$15,351 | US$29,294 | 97.6 |

## Interpretation

The direct service wins in normal operations because its shorter time and lower
emissions outweigh its slightly higher estimated claim probability. Under
monsoon and congestion assumptions, the Busan alternative becomes preferable
because its lower exposure parameters matter more. The strait scenario returns
the direct service as the weighted winner, although Busan retains lower expected
and tail cost; this difference shows that a weighted recommendation is not the
same as choosing the lowest monetary cost.

Across all four scenarios, Direct and Busan each win twice. Busan has the lower
worst CVaR95 cost (US$24,855 versus US$26,793) and zero average monetary regret
in this simulated run, so it ranks first in the robustness summary.

## Risk-preference sensitivity

Under normal operations, the direct service is recommended when the risk weight
is 0%–30%. At 40% and above, Busan becomes the recommendation. This is useful
evidence that the model responds to user preferences rather than returning a
fixed route for every setting.

## Container portfolio experiment

For 20 containers, a 70% maximum route share, a 22-day maximum average transit,
and tail-risk aversion of 0.5, the integer optimiser returned:

- Direct ocean service: 6 containers
- Busan transshipment: 14 containers
- Port Klang + road: 0 containers
- Average transit including simulated delay: 16.46 days
- Expected batch cost: US$137,316
- Risk-adjusted objective value: US$217,565
- Total simulated emissions: 17,760 kg CO₂

The allocation illustrates how a concentration constraint can preserve route
diversification even when one alternative has a lower risk-adjusted unit cost.

## Limitations and next experiment

The most important next step is not a more complicated algorithm. It is
calibration: replace route assumptions with traceable schedules, quotes, AIS
waiting times, weather observations, and defensible emissions factors. Then run
out-of-sample validation and confidence-interval analysis.

