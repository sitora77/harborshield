"""Joint batch loss, finite-action SAA, and held-out synthetic experiments.

No historical calibration is implied. Shared shocks are a sensitivity parameter,
not an estimated correlation. Exhaustive enumeration is exact for the sampled
objective over this project's small, three-route allocation space.
"""

from dataclasses import asdict, dataclass
from itertools import groupby
import math
from statistics import NormalDist
from typing import Sequence

import numpy as np

from .models import (
    Route, Scenario, Shipment, claim_probability, delay_parameters,
    expected_delay_days, insurance_premium, severity_parameters,
)


@dataclass(frozen=True)
class JointSamples:
    route_ids: tuple
    cumulative_costs: np.ndarray  # [scenario, route, allocated containers + 1]
    mean_transit: np.ndarray
    seed: int
    shared_shock_strength: float

    @property
    def containers(self):
        return self.cumulative_costs.shape[2] - 1


def empirical_cvar(losses, alpha=0.95, axis=0):
    """Exact equal-weight empirical upper CVaR, with fractional boundary mass."""
    values = np.asarray(losses, dtype=float)
    if values.ndim == 0 or not 0 <= alpha < 1 or not np.isfinite(values).all():
        raise ValueError("CVaR requires finite samples and alpha in [0, 1)")
    values = np.moveaxis(values, axis, 0)
    if len(values) == 0:
        raise ValueError("CVaR requires nonempty samples")
    mass = len(values) * (1 - alpha)
    whole = int(math.floor(mass))
    fraction = mass - whole
    ordered = np.sort(values, axis=0)[::-1]
    total = ordered[:whole].sum(axis=0)
    if whole < len(values):
        total = total + fraction * ordered[whole]
    return total / mass


def generate_joint_samples(shipment: Shipment, routes: Sequence[Route], scenario: Scenario,
                           containers=20, iterations=1000, seed=11,
                           shared_shock_strength=0.35, carbon_price_per_tonne=80.0):
    """Gaussian latent shocks preserve each route's original marginal model.

    Positive common shocks increase both claim incidence and delay. Claim
    severities are independent. Containers on the same route share a sailing
    delay even at rho=0; rho controls CROSS-route/claim latent dependence.
    """
    if not isinstance(containers, int) or not 1 <= containers <= 100:
        raise ValueError("containers must be an integer in [1, 100]")
    if not isinstance(iterations, int) or iterations < 100:
        raise ValueError("iterations must be an integer >= 100")
    if not 0 <= shared_shock_strength <= 1:
        raise ValueError("shared_shock_strength must be in [0, 1]")
    if not math.isfinite(carbon_price_per_tonne) or carbon_price_per_tonne < 0:
        raise ValueError("carbon price must be finite and non-negative")
    if not routes or len({r.route_id for r in routes}) != len(routes):
        raise ValueError("routes must have unique IDs and be nonempty")
    rng = np.random.default_rng(seed)
    shared = rng.standard_normal((iterations, 1))
    common_scale = math.sqrt(shared_shock_strength)
    local_scale = math.sqrt(1 - shared_shock_strength)
    cumulative = np.zeros((iterations, len(routes), containers + 1))
    low, mode, high = severity_parameters(shipment)
    for index, route in enumerate(routes):
        probability = claim_probability(shipment, route, scenario)
        claim_latent = common_scale * shared + local_scale * rng.standard_normal((iterations, containers))
        claims = claim_latent > NormalDist().inv_cdf(1 - probability)
        severity = rng.triangular(low, mode, high, (iterations, containers))
        gross = claims * severity * shipment.cargo_value
        payout = shipment.coverage_ratio * np.maximum(gross - shipment.cargo_value * shipment.deductible_ratio, 0)
        location, scale = delay_parameters(route, scenario)
        delay_latent = common_scale * shared[:, 0] + local_scale * rng.standard_normal(iterations)
        delay = np.maximum(location + scale * delay_latent, 0)
        fixed = (route.freight_cost + insurance_premium(shipment, route, scenario)
                 + route.carbon_kg / 1000 * carbon_price_per_tonne)
        costs = fixed + gross - payout + delay[:, None] * shipment.delay_cost_per_day
        cumulative[:, index, 1:] = np.cumsum(costs, axis=1)
    transit = np.array([r.duration_days + expected_delay_days(r, scenario) for r in routes])
    return JointSamples(tuple(r.route_id for r in routes), cumulative, transit,
                        int(seed), float(shared_shock_strength))


def allocation_losses(samples: JointSamples, counts):
    counts = tuple(counts)
    if len(counts) != len(samples.route_ids) or any(not isinstance(n, (int, np.integer)) or n < 0 for n in counts):
        raise ValueError("counts must be one non-negative integer per route")
    if sum(counts) != samples.containers:
        raise ValueError("counts must sum to the batch size")
    return sum(samples.cumulative_costs[:, r, n] for r, n in enumerate(counts))


def feasible_allocations(samples: JointSamples, maximum_route_share=0.7,
                         maximum_average_transit_days=22.0):
    if len(samples.route_ids) != 3:
        raise ValueError("finite-action optimiser currently supports exactly three routes")
    if not 0 < maximum_route_share <= 1:
        raise ValueError("maximum_route_share must be in (0, 1]")
    if not math.isfinite(maximum_average_transit_days) or maximum_average_transit_days <= 0:
        raise ValueError("transit limit must be finite and positive")
    n = samples.containers
    cap = math.floor(n * maximum_route_share + 1e-9)
    choices = []
    for a in range(cap + 1):
        for b in range(cap + 1):
            c = n - a - b
            if not 0 <= c <= cap:
                continue
            counts = (a, b, c)
            if np.dot(counts, samples.mean_transit) / n <= maximum_average_transit_days + 1e-10:
                choices.append(counts)
    return choices


def allocation_frontier(samples: JointSamples, maximum_route_share=0.7,
                        maximum_average_transit_days=22.0):
    """Evaluate every feasible integer allocation; chunks bound peak memory."""
    choices = feasible_allocations(samples, maximum_route_share, maximum_average_transit_days)
    rows = []
    for start in range(0, len(choices), 128):
        chunk = choices[start:start + 128]
        costs = np.column_stack([allocation_losses(samples, counts) for counts in chunk])
        means, tails = costs.mean(axis=0), empirical_cvar(costs)
        for counts, mean, tail in zip(chunk, means, tails):
            rows.append({"counts": list(counts), "mean_cost": float(mean),
                         "cvar95_cost": float(tail),
                         "average_transit_days": float(np.dot(counts, samples.mean_transit) / samples.containers)})
    # Two-objective dominance in O(K log K), retaining identical ties.
    best_tail = math.inf
    for _, group in groupby(sorted(rows, key=lambda row: row["mean_cost"]), key=lambda row: row["mean_cost"]):
        group = list(group)
        group_tail = min(row["cvar95_cost"] for row in group)
        for row in group:
            row["pareto_efficient"] = row["cvar95_cost"] == group_tail and group_tail < best_tail
        best_tail = min(best_tail, group_tail)
    return rows


def select_allocation(frontier, risk_aversion=0.5):
    """Minimise mean + lambda * (CVaR - mean), lambda in [0, 1]."""
    if not 0 <= risk_aversion <= 1:
        raise ValueError("risk_aversion must be in [0, 1]")
    if not frontier:
        return None
    return min(frontier, key=lambda row: (
        row["mean_cost"] + risk_aversion * (row["cvar95_cost"] - row["mean_cost"]),
        row["mean_cost"], tuple(row["counts"])))


def loss_summary(losses):
    values = np.asarray(losses)
    mean = float(values.mean())
    error = float(1.96 * values.std(ddof=1) / math.sqrt(len(values)))
    return {"mean_cost": mean, "mean_ci95_low": mean - error, "mean_ci95_high": mean + error,
            "p95_cost": float(np.quantile(values, 0.95)), "cvar95_cost": float(empirical_cvar(values)),
            "evaluation_samples": len(values)}


def paired_bootstrap(candidate_losses, baseline_losses, repetitions=200, seed=909):
    """Paired percentile bootstrap for candidate-minus-baseline differences.

    Bounds describe Monte Carlo uncertainty conditional on the selected policies
    and synthetic model, not real-world parameter uncertainty.
    """
    candidate, baseline = np.asarray(candidate_losses), np.asarray(baseline_losses)
    if candidate.shape != baseline.shape or candidate.ndim != 1 or len(candidate) < 2:
        raise ValueError("paired losses must be equally sized nonempty vectors")
    rng = np.random.default_rng(seed)
    differences = []
    for _ in range(repetitions):
        index = rng.integers(0, len(candidate), len(candidate))
        differences.append((float((candidate[index] - baseline[index]).mean()),
                            float(empirical_cvar(candidate[index]) - empirical_cvar(baseline[index]))))
    bounds = np.quantile(differences, [0.025, 0.975], axis=0)
    return {"definition": "joint minus cost-only; negative means lower cost",
            "bootstrap_repetitions": repetitions,
            "mean_difference": float((candidate - baseline).mean()),
            "mean_difference_ci95": bounds[:, 0].tolist(),
            "cvar95_difference": float(empirical_cvar(candidate) - empirical_cvar(baseline)),
            "cvar95_difference_ci95": bounds[:, 1].tolist()}


def run_joint_experiment(shipment, routes, scenario, containers=20,
                         training_samples=1000, evaluation_samples=10000,
                         train_seed=11, test_seed=20261004, shared_shock_strength=0.35,
                         maximum_route_share=0.7, maximum_average_transit_days=22.0,
                         risk_aversion=0.5, stability_seeds=(22, 33, 44, 55)):
    """Select on training only; evaluate frozen policies on independent samples."""
    if test_seed in (train_seed, *stability_seeds):
        raise ValueError("evaluation seed must differ from all training seeds")
    training = generate_joint_samples(shipment, routes, scenario, containers,
                                      training_samples, train_seed, shared_shock_strength)
    frontier = allocation_frontier(training, maximum_route_share, maximum_average_transit_days)
    if not frontier:
        return {"status": "infeasible", "frontier": []}
    joint = select_allocation(frontier, risk_aversion)
    cost = select_allocation(frontier, 0)
    balanced = min(frontier, key=lambda row: (sum((n - containers / 3) ** 2 for n in row["counts"]), row["mean_cost"]))
    # Additive marginal-tail baseline measured on the same training worlds.
    standalone = [loss_summary(training.cumulative_costs[:, r, 1]) for r in range(3)]
    additive = min(frontier, key=lambda row: sum(
        n * (m["mean_cost"] + risk_aversion * (m["cvar95_cost"] - m["mean_cost"]))
        for n, m in zip(row["counts"], standalone)))
    testing = generate_joint_samples(shipment, routes, scenario, containers,
                                     evaluation_samples, test_seed, shared_shock_strength)
    policies = {"Joint CVaR": joint, "Cost only": cost, "Balanced feasible": balanced, "Additive tail proxy": additive}
    comparison = []
    for name, row in policies.items():
        losses = allocation_losses(testing, row["counts"])
        comparison.append({"policy": name, "counts": row["counts"], **loss_summary(losses),
                           "average_transit_days": row["average_transit_days"],
                           "carbon_kg": sum(n * r.carbon_kg for n, r in zip(row["counts"], routes))})
    stability = [{"train_seed": train_seed, "counts": joint["counts"]}]
    for seed in stability_seeds:
        draws = generate_joint_samples(shipment, routes, scenario, containers,
                                       training_samples, seed, shared_shock_strength)
        alternative = select_allocation(allocation_frontier(draws, maximum_route_share, maximum_average_transit_days), risk_aversion)
        stability.append({"train_seed": seed, "counts": alternative["counts"]})
    uncertainty = paired_bootstrap(allocation_losses(testing, joint["counts"]), allocation_losses(testing, cost["counts"]))
    return {"status": "sample-optimal", "model_version": "0.2.0",
            "shipment": asdict(shipment), "route_inputs": [asdict(r) for r in routes],
            "scenario_inputs": asdict(scenario), "numpy_version": np.__version__,
            "scenario": scenario.name,
            "route_ids": list(training.route_ids), "containers": containers,
            "training_samples": training_samples, "evaluation_samples": evaluation_samples,
            "train_seed": train_seed, "test_seed": test_seed,
            "shared_shock_strength": shared_shock_strength, "risk_aversion": risk_aversion,
            "maximum_route_share": maximum_route_share,
            "maximum_average_transit_days": maximum_average_transit_days,
            "feasible_allocations": len(frontier), "frontier": frontier,
            "comparison": comparison, "paired_uncertainty": uncertainty,
            "training_seed_stability": stability,
            "scope": "Independent synthetic evaluation under the same assumed distribution; not empirical validation."}
