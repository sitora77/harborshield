import math
import random
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

from harborshield.models import (
    SCENARIOS, Shipment, _conditional_tail_mean, expected_excess_severity,
    load_routes, rank_routes, severity_parameters, simulate_route,
)
from harborshield.joint_risk import (
    allocation_frontier, allocation_losses, empirical_cvar, feasible_allocations,
    generate_joint_samples, run_joint_experiment, select_allocation,
)
from harborshield.optimization import optimize_container_portfolio


class JointRiskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.routes = load_routes(Path(__file__).resolve().parents[1] / "data/sample_routes.csv")
        cls.shipment = Shipment(250000, cargo_type="Electronics")
        cls.scenario = SCENARIOS["Normal operations"]

    def draws(self, **kwargs):
        return generate_joint_samples(self.shipment, self.routes, self.scenario, **kwargs)

    def test_fractional_tail_mass(self):
        self.assertAlmostEqual(_conditional_tail_mean([0, 10, 20], 0.5), 50 / 3)
        self.assertAlmostEqual(float(empirical_cvar([0, 10, 20], 0.5)), 50 / 3)

    def test_cvar_handles_quantile_ties(self):
        self.assertAlmostEqual(float(empirical_cvar([0] * 99 + [100], 0.95)), 20)
        self.assertAlmostEqual(_conditional_tail_mean([0] * 99 + [100], 0.95), 20)

    def test_cvar_matches_rockafellar_uryasev_objective(self):
        values = np.array([1, 2, 2, 9, 18, 31])
        objective = min(eta + np.maximum(values - eta, 0).mean() / 0.25 for eta in values)
        self.assertAlmostEqual(float(empirical_cvar(values, 0.75)), objective)

    def test_vectorised_cvar(self):
        values = np.array([[1, 4], [5, 2], [3, 8]])
        np.testing.assert_allclose(empirical_cvar(values, 0.5), [13 / 3, 20 / 3])

    def test_premium_uses_triangular_mean_not_mode(self):
        low, mode, high = severity_parameters(self.shipment)
        expected = (low + mode + high) / 3 - self.shipment.deductible_ratio
        self.assertAlmostEqual(expected_excess_severity(self.shipment), expected)
        self.assertNotAlmostEqual(expected, mode - self.shipment.deductible_ratio)

    def test_deductible_stop_loss_integral(self):
        rng = random.Random(77)
        low, mode, high = severity_parameters(self.shipment)
        severities = [rng.triangular(low, high, mode) for _ in range(100000)]
        for deductible in (0.02, 0.15, 0.5, 0.95):
            analytical = expected_excess_severity(replace(self.shipment, deductible_ratio=deductible))
            simulated = sum(max(s - deductible, 0) for s in severities) / len(severities)
            self.assertAlmostEqual(analytical, simulated, delta=0.002)

    def test_joint_reproducibility_and_seed_separation(self):
        a, b = self.draws(iterations=200), self.draws(iterations=200)
        np.testing.assert_array_equal(a.cumulative_costs, b.cumulative_costs)
        self.assertFalse(np.array_equal(a.cumulative_costs, self.draws(iterations=200, seed=12).cumulative_costs))
        self.assertTrue((np.diff(a.cumulative_costs, axis=2) >= 0).all())

    def test_share_cap_never_rounds_up(self):
        samples = self.draws(containers=1, iterations=100)
        self.assertEqual(feasible_allocations(samples, 0.7, 30), [])
        results = [simulate_route(self.shipment, r, self.scenario, iterations=100) for r in self.routes]
        self.assertIsNone(optimize_container_portfolio(self.routes, results, 1, 0.7, 30))

    def test_all_feasible_allocations_obey_constraints(self):
        samples = self.draws(containers=20, iterations=100)
        for counts in feasible_allocations(samples, 0.7, 22):
            self.assertEqual(sum(counts), 20)
            self.assertLessEqual(max(counts), 14)
            self.assertLessEqual(np.dot(counts, samples.mean_transit) / 20, 22 + 1e-9)

    def test_selected_sample_objective_is_global_minimum(self):
        samples = self.draws(containers=6, iterations=200)
        frontier = allocation_frontier(samples, 0.7, 30)
        chosen = select_allocation(frontier, 0.5)
        objective = lambda row: (row["mean_cost"] + row["cvar95_cost"]) / 2
        self.assertEqual(objective(chosen), min(map(objective, frontier)))
        self.assertAlmostEqual(chosen["cvar95_cost"], float(empirical_cvar(allocation_losses(samples, chosen["counts"]))))

    def test_pareto_flags_match_pairwise_definition(self):
        rows = allocation_frontier(self.draws(containers=6, iterations=100), 1.0, 30)
        for row in rows:
            dominated = any(x["mean_cost"] <= row["mean_cost"] and x["cvar95_cost"] <= row["cvar95_cost"]
                            and (x["mean_cost"] < row["mean_cost"] or x["cvar95_cost"] < row["cvar95_cost"])
                            for x in rows)
            self.assertEqual(row["pareto_efficient"], not dominated)

    def test_identical_training_and_evaluation_seed_rejected(self):
        with self.assertRaises(ValueError):
            run_joint_experiment(self.shipment, self.routes, self.scenario, train_seed=11, test_seed=11)

    def test_evaluation_seed_cannot_change_training_decision(self):
        arguments = dict(containers=6, training_samples=100, evaluation_samples=200,
                         maximum_average_transit_days=30, stability_seeds=())
        a = run_joint_experiment(self.shipment, self.routes, self.scenario, test_seed=91, **arguments)
        b = run_joint_experiment(self.shipment, self.routes, self.scenario, test_seed=92, **arguments)
        self.assertEqual(a["comparison"][0]["counts"], b["comparison"][0]["counts"])
        self.assertNotEqual(a["comparison"][0]["mean_cost"], b["comparison"][0]["mean_cost"])

    def test_shared_shock_increases_cross_route_dependence(self):
        independent = self.draws(iterations=20000, containers=2, shared_shock_strength=0)
        shared = self.draws(iterations=20000, containers=2, shared_shock_strength=0.9)
        correlation = lambda draws: np.corrcoef(draws.cumulative_costs[:, 0, 1], draws.cumulative_costs[:, 1, 1])[0, 1]
        self.assertGreater(correlation(shared), correlation(independent) + 0.10)

    def test_input_validation(self):
        for value in (math.nan, math.inf, -1):
            with self.assertRaises(ValueError):
                Shipment(value)
        with self.assertRaises(ValueError):
            Shipment(100, delay_cost_per_day=-1)
        with self.assertRaises(ValueError):
            replace(self.routes[0], reliability=1.1)
        with self.assertRaises(ValueError):
            empirical_cvar([], 0.95)
        with self.assertRaises(ValueError):
            self.draws(shared_shock_strength=1.1)
        results = [simulate_route(self.shipment, r, self.scenario, iterations=100) for r in self.routes]
        with self.assertRaises(ValueError):
            optimize_container_portfolio(self.routes, list(reversed(results)), 20)
        with self.assertRaises(ValueError):
            rank_routes(results, 0, 0, 0, 0)


if __name__ == "__main__":
    unittest.main()
