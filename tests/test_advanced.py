import unittest
from pathlib import Path

from harborshield.analysis import robust_route_summary, scenario_stress_test
from harborshield.models import SCENARIOS, Shipment, load_routes, simulate_route
from harborshield.optimization import optimize_container_portfolio
from harborshield.public_data import activity_summary, load_port_activity


ROOT = Path(__file__).resolve().parents[1]


class HarborShieldAdvancedTests(unittest.TestCase):
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

    def test_public_activity_summary(self):
        observations = load_port_activity(ROOT / "data" / "mpa_vessel_arrivals_monthly.csv")
        summary = activity_summary(observations)
        self.assertEqual(summary["latest_month"], "2026-08")
        self.assertGreater(summary["activity_pressure_index"], 0)

    def test_stress_test_covers_all_route_scenario_pairs(self):
        rows = scenario_stress_test(self.shipment, self.routes, iterations=200)
        self.assertEqual(len(rows), len(self.routes) * len(SCENARIOS))
        summary = robust_route_summary(rows)
        self.assertEqual(len(summary), len(self.routes))

    def test_portfolio_optimizer_allocates_every_container(self):
        results = [
            simulate_route(
                self.shipment,
                route,
                SCENARIOS["Normal operations"],
                iterations=300,
                seed=index,
            )
            for index, route in enumerate(self.routes)
        ]
        solution = optimize_container_portfolio(
            self.routes,
            results,
            containers=20,
            maximum_route_share=0.7,
            maximum_average_transit_days=25,
        )
        self.assertIsNotNone(solution)
        self.assertEqual(sum(solution.allocations.values()), 20)
        self.assertLessEqual(max(solution.allocations.values()), 14)


if __name__ == "__main__":
    unittest.main()

