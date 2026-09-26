import unittest
from pathlib import Path

from harborshield.models import (
    SCENARIOS,
    Shipment,
    claim_probability,
    load_routes,
    rank_routes,
    simulate_route,
)


ROOT = Path(__file__).resolve().parents[1]


class HarborShieldModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.routes = load_routes(ROOT / "data" / "sample_routes.csv")
        cls.shipment = Shipment(
            cargo_value=250_000,
            cargo_type="Electronics",
            packaging_quality=3,
            coverage_ratio=0.9,
            deductible_ratio=0.01,
        )

    def test_route_data_loads(self):
        self.assertEqual(len(self.routes), 3)
        self.assertTrue(all(route.freight_cost > 0 for route in self.routes))

    def test_adverse_scenario_increases_claim_probability(self):
        route = self.routes[0]
        normal = claim_probability(self.shipment, route, SCENARIOS["Normal operations"])
        disruption = claim_probability(self.shipment, route, SCENARIOS["Strait disruption"])
        self.assertGreater(disruption, normal)

    def test_simulation_is_reproducible(self):
        first = simulate_route(
            self.shipment, self.routes[0], SCENARIOS["Normal operations"], iterations=500, seed=7
        )
        second = simulate_route(
            self.shipment, self.routes[0], SCENARIOS["Normal operations"], iterations=500, seed=7
        )
        self.assertEqual(first.expected_total_cost, second.expected_total_cost)

    def test_ranking_returns_lowest_score_first(self):
        results = [
            simulate_route(
                self.shipment, route, SCENARIOS["Normal operations"], iterations=500, seed=index
            )
            for index, route in enumerate(self.routes)
        ]
        ranked = rank_routes(results)
        self.assertEqual(len(ranked), 3)
        self.assertLessEqual(ranked[0]["decision_score"], ranked[-1]["decision_score"])


if __name__ == "__main__":
    unittest.main()

