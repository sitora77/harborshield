# Application positioning notes

## Core narrative

My undergraduate training in port, waterway, and coastal engineering taught me
how maritime infrastructure shapes cargo flows. During a freight-forwarding
internship, I assisted with marine cargo insurance operations and observed that
route, delay, cargo, and insurance decisions were often discussed separately.
I therefore built HarborShield with AI-assisted coding, a transparent prototype that integrates
these trade-offs through probabilistic simulation and multi-criteria decision
analysis.

Only use this paragraph after you can demonstrate and explain the project in
your own words.

## Programme-specific emphasis

### Maritime Technology and Management

Emphasise maritime digitalisation, port disruption, cargo risk, and the bridge
between engineering knowledge and operational decisions.

### Industrial and Systems Engineering

Emphasise problem formulation, probability, Monte Carlo simulation, transparent
assumptions, sensitivity analysis, and multi-objective optimisation.

### Supply Chain Management

Emphasise supply-chain resilience, transshipment risk, total landed cost,
service reliability, and scenario planning.

### Intelligent Transportation

Emphasise multimodal networks, route choice, disruption response, emissions,
and data-supported transport planning.

## AI assistance and ownership

The implementation and documentation were developed with substantial AI coding
assistance. This should not be described as entirely independently authored code.
Only claim personal work, experiments and learning that you can actually explain,
reproduce and discuss. Record your own parameter changes, questions, experiments
and conclusions in a learning log. Keep any AI-assistance disclosure required by
the relevant institution or application.

## CV bullet template

Do not invent performance improvements. Replace bracketed text only after the
experiment has been run and documented.

> Built HarborShield with AI-assisted coding, a Python-based maritime cargo risk and intermodal
> route decision-support prototype; combined Monte Carlo loss simulation,
> CVaR95 tail-risk measurement, insurance coverage modelling, and OR-Tools
> integer allocation across four disruption scenarios and three candidate routes;
> integrated an official monthly vessel-arrivals dataset from Singapore's MPA.

Version 0.2 adds joint batch CVaR, finite-action allocation, four policy baselines,
independent synthetic evaluation and paired uncertainty intervals. Describe these
as implemented prototype methods, not novel algorithms or demonstrated savings.
In the default report, three regimes return identical joint/cost-only policies;
the strait-regime CVaR difference is not established as significant.

## Evidence to prepare

- A public GitHub repository with clear commit history.
- A 2–3 minute screen recording of the dashboard.
- One architecture diagram.
- A short report describing assumptions, experiments, limitations, and next steps.
- A table showing how route rankings change across scenarios and decision weights.
- A source register separating official, simulated, and planned data.
- A short reflection on what you personally learned and changed during development.
