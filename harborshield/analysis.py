"""Scenario stress testing and sensitivity analysis for HarborShield."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Sequence

from .models import Route, SCENARIOS, Shipment, rank_routes, simulate_route


def scenario_stress_test(
    shipment: Shipment,
    routes: Sequence[Route],
    iterations: int = 2_500,
    cost_weight: float = 0.40,
    risk_weight: float = 0.30,
    time_weight: float = 0.20,
    carbon_weight: float = 0.10,
    seed: int = 100,
) -> List[Dict[str, float]]:
    """Evaluate every route under every predefined disruption scenario."""
    rows: List[Dict[str, float]] = []
    for scenario_index, (scenario_name, scenario) in enumerate(SCENARIOS.items()):
        results = [
            simulate_route(
                shipment,
                route,
                scenario,
                iterations=iterations,
                seed=seed + scenario_index * 100 + route_index,
            )
            for route_index, route in enumerate(routes)
        ]
        ranked = rank_routes(
            results,
            cost_weight=cost_weight,
            risk_weight=risk_weight,
            time_weight=time_weight,
            carbon_weight=carbon_weight,
        )
        minimum_cost = min(row["expected_total_cost"] for row in ranked)
        for rank, row in enumerate(ranked, start=1):
            enriched = dict(row)
            enriched["scenario"] = scenario_name
            enriched["rank"] = rank
            enriched["cost_regret"] = row["expected_total_cost"] - minimum_cost
            rows.append(enriched)
    return rows


def robust_route_summary(stress_rows: Sequence[Dict[str, float]]) -> List[Dict[str, float]]:
    """Aggregate scenario results into a conservative robustness comparison."""
    grouped: Dict[str, List[Dict[str, float]]] = defaultdict(list)
    for row in stress_rows:
        grouped[str(row["route_id"])].append(row)

    summary: List[Dict[str, float]] = []
    for route_id, rows in grouped.items():
        count = float(len(rows))
        summary.append(
            {
                "route_id": route_id,
                "route_name": rows[0]["route_name"],
                "average_rank": sum(float(row["rank"]) for row in rows) / count,
                "wins": sum(1 for row in rows if int(row["rank"]) == 1),
                "average_decision_score": sum(
                    float(row["decision_score"]) for row in rows
                )
                / count,
                "worst_case_cost": max(float(row["cvar95_total_cost"]) for row in rows),
                "maximum_claim_probability": max(
                    float(row["claim_probability"]) for row in rows
                ),
                "average_cost_regret": sum(
                    float(row["cost_regret"]) for row in rows
                )
                / count,
            }
        )
    return sorted(
        summary,
        key=lambda row: (
            row["average_rank"],
            row["average_decision_score"],
            row["worst_case_cost"],
        ),
    )


def risk_weight_sensitivity(
    shipment: Shipment,
    routes: Sequence[Route],
    scenario_name: str,
    iterations: int = 2_000,
    seed: int = 700,
) -> List[Dict[str, float]]:
    """Show how the recommended route changes as risk preference changes."""
    scenario = SCENARIOS[scenario_name]
    results = [
        simulate_route(
            shipment,
            route,
            scenario,
            iterations=iterations,
            seed=seed + route_index,
        )
        for route_index, route in enumerate(routes)
    ]
    rows: List[Dict[str, float]] = []
    # The non-risk share retains the baseline 4:2:1 ratio for cost, time, carbon.
    for risk_percent in range(0, 101, 10):
        remaining = 100 - risk_percent
        ranked = rank_routes(
            results,
            cost_weight=remaining * 4 / 7,
            risk_weight=risk_percent,
            time_weight=remaining * 2 / 7,
            carbon_weight=remaining * 1 / 7,
        )
        for rank, result in enumerate(ranked, start=1):
            rows.append(
                {
                    "risk_weight_percent": risk_percent,
                    "route_name": result["route_name"],
                    "rank": rank,
                    "decision_score": result["decision_score"],
                    "recommended": rank == 1,
                }
            )
    return rows
