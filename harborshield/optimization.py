"""Integer portfolio optimisation for allocating containers across routes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Sequence

from ortools.sat.python import cp_model

from .models import Route, SimulationResult


@dataclass(frozen=True)
class PortfolioSolution:
    status: str
    allocations: Dict[str, int]
    expected_total_cost: float
    risk_adjusted_total_cost: float
    average_transit_days: float
    total_carbon_kg: float


def optimize_container_portfolio(
    routes: Sequence[Route],
    results: Sequence[SimulationResult],
    containers: int,
    maximum_route_share: float = 0.70,
    maximum_average_transit_days: float = 22.0,
    risk_aversion: float = 0.50,
) -> Optional[PortfolioSolution]:
    """Allocate a container batch using an auditable integer programme.

    The objective minimises expected total cost plus a configurable tail-risk
    premium based on the gap between CVaR95 and expected cost. Constraints enforce
    a shipment total, a route-concentration limit, and an average transit limit.
    """
    if containers < 1:
        raise ValueError("containers must be positive")
    if len(routes) != len(results):
        raise ValueError("routes and results must have the same length")
    if not 0 < maximum_route_share <= 1:
        raise ValueError("maximum_route_share must be in (0, 1]")
    if risk_aversion < 0:
        raise ValueError("risk_aversion must be non-negative")

    model = cp_model.CpModel()
    variables = [
        model.new_int_var(0, containers, f"containers_{route.route_id}")
        for route in routes
    ]
    model.add(sum(variables) == containers)

    route_cap = max(1, math.floor(containers * maximum_route_share))
    for variable in variables:
        model.add(variable <= route_cap)

    duration_scale = 100
    model.add(
        sum(
            int(round((result.duration_days + result.expected_delay_days) * duration_scale))
            * variable
            for result, variable in zip(results, variables)
        )
        <= int(round(maximum_average_transit_days * duration_scale * containers))
    )

    cost_scale = 100
    risk_adjusted_unit_costs = [
        result.expected_total_cost
        + risk_aversion * max(result.cvar95_total_cost - result.expected_total_cost, 0.0)
        for result in results
    ]
    model.minimize(
        sum(
            int(round(unit_cost * cost_scale)) * variable
            for unit_cost, variable in zip(risk_adjusted_unit_costs, variables)
        )
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    solver.parameters.num_search_workers = 1
    status_code = solver.solve(model)
    if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    status = "optimal" if status_code == cp_model.OPTIMAL else "feasible"
    allocations = {
        route.route_id: solver.value(variable)
        for route, variable in zip(routes, variables)
    }
    expected_total_cost = sum(
        allocations[route.route_id] * result.expected_total_cost
        for route, result in zip(routes, results)
    )
    risk_adjusted_total_cost = sum(
        allocations[route.route_id] * unit_cost
        for route, unit_cost in zip(routes, risk_adjusted_unit_costs)
    )
    average_transit_days = sum(
        allocations[route.route_id]
        * (result.duration_days + result.expected_delay_days)
        for route, result in zip(routes, results)
    ) / containers
    total_carbon_kg = sum(
        allocations[route.route_id] * result.carbon_kg
        for route, result in zip(routes, results)
    )
    return PortfolioSolution(
        status=status,
        allocations=allocations,
        expected_total_cost=expected_total_cost,
        risk_adjusted_total_cost=risk_adjusted_total_cost,
        average_transit_days=average_transit_days,
        total_carbon_kg=total_carbon_kg,
    )
