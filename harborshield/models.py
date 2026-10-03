"""Transparent risk, insurance, and route-comparison models for HarborShield.

The formulas are educational decision-support models. They are deliberately
simple enough to audit and explain, and are not calibrated actuarial pricing
models.
"""

from __future__ import annotations

import csv
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping


CARGO_RISK: Mapping[str, float] = {
    "General cargo": 0.00,
    "Machinery": 0.18,
    "Electronics": 0.42,
    "Perishable goods": 0.55,
    "Dangerous goods": 0.32,
}


@dataclass(frozen=True)
class Shipment:
    cargo_value: float
    cargo_type: str = "General cargo"
    packaging_quality: int = 3
    coverage_ratio: float = 0.90
    deductible_ratio: float = 0.01
    delay_cost_per_day: float = 500.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.cargo_value) or self.cargo_value <= 0:
            raise ValueError("cargo_value must be positive")
        if self.cargo_type not in CARGO_RISK:
            raise ValueError("unsupported cargo_type")
        if not isinstance(self.packaging_quality, int) or not 1 <= self.packaging_quality <= 5:
            raise ValueError("packaging_quality must be between 1 and 5")
        if not 0 <= self.coverage_ratio <= 1:
            raise ValueError("coverage_ratio must be between 0 and 1")
        if not 0 <= self.deductible_ratio <= 1:
            raise ValueError("deductible_ratio must be between 0 and 1")
        if not math.isfinite(self.delay_cost_per_day) or self.delay_cost_per_day < 0:
            raise ValueError("delay_cost_per_day must be finite and non-negative")


@dataclass(frozen=True)
class Route:
    route_id: str
    name: str
    via: str
    freight_cost: float
    duration_days: float
    transshipments: int
    distance_km: float
    carbon_kg: float
    weather_exposure: float
    congestion_index: float
    reliability: float
    path: str

    def __post_init__(self) -> None:
        if not self.route_id or not self.name:
            raise ValueError("route_id and name are required")
        for field in ("freight_cost", "duration_days", "distance_km", "carbon_kg"):
            value = getattr(self, field)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{field} must be finite and non-negative")
        if self.duration_days == 0:
            raise ValueError("duration_days must be positive")
        for field in ("weather_exposure", "congestion_index", "reliability"):
            if not 0 <= getattr(self, field) <= 1:
                raise ValueError(f"{field} must be in [0, 1]")
        if not isinstance(self.transshipments, int) or self.transshipments < 0:
            raise ValueError("transshipments must be a non-negative integer")


@dataclass(frozen=True)
class Scenario:
    name: str
    weather_multiplier: float = 1.0
    congestion_multiplier: float = 1.0
    delay_multiplier: float = 1.0
    disruption_multiplier: float = 1.0

    def __post_init__(self) -> None:
        for field in ("weather_multiplier", "congestion_multiplier", "delay_multiplier", "disruption_multiplier"):
            value = getattr(self, field)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{field} must be finite and positive")


SCENARIOS: Dict[str, Scenario] = {
    "Normal operations": Scenario("Normal operations"),
    "Monsoon weather": Scenario(
        "Monsoon weather",
        weather_multiplier=1.85,
        congestion_multiplier=1.10,
        delay_multiplier=1.20,
        disruption_multiplier=1.15,
    ),
    "Port congestion": Scenario(
        "Port congestion",
        weather_multiplier=1.05,
        congestion_multiplier=1.90,
        delay_multiplier=1.35,
        disruption_multiplier=1.20,
    ),
    "Strait disruption": Scenario(
        "Strait disruption",
        weather_multiplier=1.20,
        congestion_multiplier=1.40,
        delay_multiplier=1.60,
        disruption_multiplier=2.00,
    ),
}


@dataclass(frozen=True)
class SimulationResult:
    route_id: str
    route_name: str
    claim_probability: float
    insurance_premium: float
    expected_gross_loss: float
    expected_insurance_payout: float
    expected_retained_loss: float
    expected_delay_days: float
    expected_delay_cost: float
    carbon_cost: float
    freight_cost: float
    expected_total_cost: float
    p90_total_cost: float
    p95_total_cost: float
    cvar95_total_cost: float
    reliability: float
    duration_days: float
    carbon_kg: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


def _logistic(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def claim_probability(
    shipment: Shipment, route: Route, scenario: Scenario
) -> float:
    """Estimate a transparent, illustrative cargo-claim probability."""
    packaging_penalty = (5 - shipment.packaging_quality) * 0.16
    score = (
        -5.15
        + CARGO_RISK[shipment.cargo_type]
        + packaging_penalty
        + 0.032 * route.duration_days
        + 0.30 * route.transshipments
        + 1.05 * route.weather_exposure * scenario.weather_multiplier
        + 0.80 * route.congestion_index * scenario.congestion_multiplier
        + 0.38 * math.log(max(scenario.disruption_multiplier, 0.01))
        - 0.45 * route.reliability
    )
    return min(max(_logistic(score), 0.001), 0.65)


def _percentile(values: List[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = (len(ordered) - 1) * percentile
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _conditional_tail_mean(values: List[float], percentile: float) -> float:
    """Empirical upper CVaR with fractional boundary mass, including ties.

    Equivalent to min_eta eta + mean(max(loss - eta, 0)) / (1 - alpha).
    Simply averaging values >= an interpolated quantile is not equivalent.
    """
    if not values or not 0 <= percentile < 1:
        raise ValueError("CVaR requires nonempty samples and percentile in [0, 1)")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("loss samples must be finite")
    ordered = sorted(values, reverse=True)
    mass = len(ordered) * (1 - percentile)
    whole = min(int(math.floor(mass)), len(ordered))
    fraction = mass - whole
    total = sum(ordered[:whole])
    if whole < len(ordered):
        total += fraction * ordered[whole]
    return total / mass


def severity_parameters(shipment: Shipment):
    """Triangular loss fraction: (minimum, mode, maximum), not mean."""
    return 0.03, 0.26 + 0.10 * CARGO_RISK[shipment.cargo_type], 0.88


def expected_excess_severity(shipment: Shipment) -> float:
    """Exact E[(severity - deductible_ratio)+] for the triangular model."""
    low, mode, high = severity_parameters(shipment)
    deductible = shipment.deductible_ratio
    mean = (low + mode + high) / 3
    if deductible <= low:
        return mean - deductible
    if deductible >= high:
        return 0.0
    if deductible <= mode:
        return mean - deductible + (deductible - low) ** 3 / (3 * (high - low) * (mode - low))
    return (high - deductible) ** 3 / (3 * (high - low) * (high - mode))


def insurance_premium(shipment: Shipment, route: Route, scenario: Scenario) -> float:
    """Illustrative expected insured payout plus 25% loading; not a quote."""
    return (claim_probability(shipment, route, scenario) * shipment.cargo_value
            * shipment.coverage_ratio * expected_excess_severity(shipment) * 1.25)


def delay_parameters(route: Route, scenario: Scenario):
    location = (route.duration_days * max(scenario.delay_multiplier - 1, 0)
                + 2.2 * route.congestion_index * scenario.congestion_multiplier)
    return location, max(0.7, location * 0.40)


def expected_delay_days(route: Route, scenario: Scenario) -> float:
    """Analytic mean of max(0, Normal(location, scale)); used in constraints."""
    location, scale = delay_parameters(route, scenario)
    z = location / scale
    return location * (1 + math.erf(z / math.sqrt(2))) / 2 + scale * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)


def simulate_route(
    shipment: Shipment,
    route: Route,
    scenario: Scenario,
    iterations: int = 5_000,
    seed: int = 42,
    carbon_price_per_tonne: float = 80.0,
) -> SimulationResult:
    """Run a reproducible Monte Carlo simulation for one route."""
    if not isinstance(iterations, int) or iterations < 100:
        raise ValueError("iterations must be at least 100")
    if not math.isfinite(carbon_price_per_tonne) or carbon_price_per_tonne < 0:
        raise ValueError("carbon price must be finite and non-negative")

    rng = random.Random(seed)
    probability = claim_probability(shipment, route, scenario)
    deductible = shipment.cargo_value * shipment.deductible_ratio

    # Pure-risk premium plus a 25% operating/capital loading. This is a
    # teaching approximation, not an insurer quote.
    low_severity, mode_severity, high_severity = severity_parameters(shipment)
    premium = insurance_premium(shipment, route, scenario)
    carbon_cost = route.carbon_kg / 1_000.0 * carbon_price_per_tonne

    gross_losses: List[float] = []
    payouts: List[float] = []
    retained_losses: List[float] = []
    delays: List[float] = []
    delay_costs: List[float] = []
    total_costs: List[float] = []

    mean_delay, delay_scale = delay_parameters(route, scenario)

    for _ in range(iterations):
        if rng.random() < probability:
            severity = rng.triangular(low_severity, high_severity, mode_severity)
            gross_loss = shipment.cargo_value * severity
        else:
            gross_loss = 0.0

        payout = shipment.coverage_ratio * max(gross_loss - deductible, 0.0)
        retained_loss = gross_loss - payout
        delay = max(0.0, rng.gauss(mean_delay, delay_scale))
        delay_cost = delay * shipment.delay_cost_per_day
        total_cost = (
            route.freight_cost
            + premium
            + retained_loss
            + delay_cost
            + carbon_cost
        )

        gross_losses.append(gross_loss)
        payouts.append(payout)
        retained_losses.append(retained_loss)
        delays.append(delay)
        delay_costs.append(delay_cost)
        total_costs.append(total_cost)

    divisor = float(iterations)
    return SimulationResult(
        route_id=route.route_id,
        route_name=route.name,
        claim_probability=probability,
        insurance_premium=premium,
        expected_gross_loss=sum(gross_losses) / divisor,
        expected_insurance_payout=sum(payouts) / divisor,
        expected_retained_loss=sum(retained_losses) / divisor,
        expected_delay_days=sum(delays) / divisor,
        expected_delay_cost=sum(delay_costs) / divisor,
        carbon_cost=carbon_cost,
        freight_cost=route.freight_cost,
        expected_total_cost=sum(total_costs) / divisor,
        p90_total_cost=_percentile(total_costs, 0.90),
        p95_total_cost=_percentile(total_costs, 0.95),
        cvar95_total_cost=_conditional_tail_mean(total_costs, 0.95),
        reliability=route.reliability,
        duration_days=route.duration_days,
        carbon_kg=route.carbon_kg,
    )


def _normalise(values: Iterable[float]) -> List[float]:
    items = list(values)
    lower, upper = min(items), max(items)
    if math.isclose(lower, upper):
        return [0.0 for _ in items]
    return [(value - lower) / (upper - lower) for value in items]


def rank_routes(
    results: List[SimulationResult],
    cost_weight: float = 0.40,
    risk_weight: float = 0.30,
    time_weight: float = 0.20,
    carbon_weight: float = 0.10,
) -> List[Dict[str, float]]:
    """Rank routes with an auditable weighted multi-criteria score."""
    if not results:
        return []
    weights = [cost_weight, risk_weight, time_weight, carbon_weight]
    if any(not math.isfinite(weight) or weight < 0 for weight in weights) or math.isclose(sum(weights), 0):
        raise ValueError("weights must be non-negative and sum to more than zero")
    total_weight = sum(weights)
    cost_weight, risk_weight, time_weight, carbon_weight = [
        weight / total_weight for weight in weights
    ]

    costs = _normalise(result.expected_total_cost for result in results)
    risks = _normalise(result.claim_probability for result in results)
    times = _normalise(
        result.duration_days + result.expected_delay_days for result in results
    )
    carbon = _normalise(result.carbon_kg for result in results)

    ranked: List[Dict[str, float]] = []
    for index, result in enumerate(results):
        score = 100.0 * (
            cost_weight * costs[index]
            + risk_weight * risks[index]
            + time_weight * times[index]
            + carbon_weight * carbon[index]
        )
        row = result.to_dict()
        row["decision_score"] = score
        ranked.append(row)
    return sorted(ranked, key=lambda row: row["decision_score"])


def load_routes(path: Path) -> List[Route]:
    """Load candidate routes from a CSV file."""
    routes: List[Route] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            routes.append(
                Route(
                    route_id=row["route_id"],
                    name=row["name"],
                    via=row["via"],
                    freight_cost=float(row["freight_cost"]),
                    duration_days=float(row["duration_days"]),
                    transshipments=int(row["transshipments"]),
                    distance_km=float(row["distance_km"]),
                    carbon_kg=float(row["carbon_kg"]),
                    weather_exposure=float(row["weather_exposure"]),
                    congestion_index=float(row["congestion_index"]),
                    reliability=float(row["reliability"]),
                    path=row["path"],
                )
            )
    return routes
