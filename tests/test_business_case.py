import copy
import json
from pathlib import Path
import unittest

from harborshield.business_case import (case_report, compare_options, evaluate_option,
                                      funding_ledger, load_case, validate_case)

ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTests(unittest.TestCase):
    def setUp(self):
        self.case = load_case(ROOT / "data/cases/singapore_2024.json")

    def test_cash_area_against_hand_calculation(self):
        result = funding_ledger([{"day": -7, "amount": -45000},
                                 {"day": 0, "amount": -108600},
                                 {"day": 28.5, "amount": 210000}], 25000, .08)
        self.assertAlmostEqual(result["funding_dollar_days"], 20000 * 7 + 128600 * 28.5)
        self.assertAlmostEqual(result["funding_cost"], (20000 * 7 + 128600 * 28.5) * .08 / 365)
        self.assertEqual(result["peak_funding_need"], 128600)
        self.assertEqual(result["closing_cash_before_interest"], 81400)

    def test_same_day_cashflows_net_before_interest(self):
        result = funding_ledger([{"day": 0, "amount": -100}, {"day": 0, "amount": 100},
                                 {"day": 10, "amount": 0}], 0, .1)
        self.assertEqual(result["funding_cost"], 0)
        self.assertEqual(result["peak_funding_need"], 0)

    def test_own_cash_and_zero_rate_remove_funding_cost(self):
        case = copy.deepcopy(self.case)
        case["order"]["initial_cash"] = 1000000
        self.assertTrue(all(row["funding_cost"] == 0 for row in compare_options(case)))
        case["order"].update(initial_cash=0, annual_funding_rate=0)
        self.assertTrue(all(row["funding_cost"] == 0 for row in compare_options(case)))

    def test_opportunity_is_not_double_counted_in_cash(self):
        row = evaluate_option(self.case["order"], self.case["options"][0], 2.5)
        self.assertEqual(row["stockout_days"], 2.5)
        self.assertEqual(row["stockout_opportunity_cost"], 500 * 12)
        self.assertEqual(row["sales_receipt"], 210000)
        self.assertAlmostEqual(row["economic_burden"], row["logistics_cost"] + row["funding_cost"] + 6000)
        self.assertAlmostEqual(row["net_economic_contribution"], 60000 - row["economic_burden"])
        self.assertEqual(sum(event["net_flow"] for event in row["events"]), 60000 - row["logistics_cost"])

    def test_decision_changes_with_delay(self):
        self.assertEqual(compare_options(self.case, 0)[0]["option_id"], "standard_sea")
        self.assertEqual(compare_options(self.case, 2.5)[0]["option_id"], "priority_sea")

    def test_unmet_volume_is_capped_and_zero_demand_supported(self):
        case = copy.deepcopy(self.case)
        case["order"].update(daily_demand=10000, stock_cover_days=0)
        self.assertEqual(compare_options(case)[0]["unmet_units"], 5000)
        case["order"]["daily_demand"] = 0
        self.assertTrue(all(row["stockout_opportunity_cost"] == 0 for row in compare_options(case)))

    def test_reject_nonfinite_negative_boolean_and_fractional_units(self):
        for key, value in (("annual_funding_rate", float("nan")), ("initial_cash", -1),
                           ("daily_demand", True), ("quantity", 1.5), ("supplier_deposit_fraction", 2)):
            with self.subTest(key=key):
                case = copy.deepcopy(self.case)
                case["order"][key] = value
                with self.assertRaises(ValueError):
                    validate_case(case)

    def test_reject_fx_and_duplicate_options(self):
        case = copy.deepcopy(self.case)
        case["order"]["currency"] = "SGD"
        with self.assertRaises(ValueError):
            validate_case(case)
        self.case["options"].append(self.case["options"][0])
        with self.assertRaises(ValueError):
            validate_case(self.case)

    def test_report_reproducible_and_inputs_not_mutated(self):
        before = copy.deepcopy(self.case)
        self.assertEqual(case_report(self.case), case_report(self.case))
        self.assertEqual(self.case, before)
        self.assertEqual(len(case_report(self.case)["sensitivity"]), 27)

    def test_remaining_principal_visible_after_collection(self):
        result = funding_ledger([{"day": 0, "amount": -100}, {"day": 10, "amount": 20}], 0, .1)
        self.assertEqual(result["residual_funding_need"], 80)
        self.assertAlmostEqual(result["funding_cost"], 100 * 10 * .1 / 365)

    def test_published_snapshot_matches_current_case_calculation(self):
        published = json.loads((ROOT / "reports/case_study.json").read_text(encoding="utf-8"))
        actual = case_report(self.case)
        for key in actual:
            self.assertEqual(published[key], actual[key])

    def test_seeded_document_evidence_is_labelled_and_correct(self):
        published = json.loads((ROOT / "reports/case_study.json").read_text(encoding="utf-8"))
        evidence = published["document_evidence"]
        self.assertEqual(len(evidence["consistency_fixtures"]), 8)
        self.assertTrue(all(row["matches_fixture_expectation"] for row in evidence["consistency_fixtures"]))
        original, tampered, replacement = evidence["signature_demonstration"]
        self.assertTrue(original["accepted_demo_signature"])
        self.assertFalse(tampered["signature_valid"])
        self.assertTrue(replacement["signature_valid"])
        self.assertFalse(replacement["issuer_key_matches_anchor"])
        self.assertTrue(all(not row["document_truth_verified"] for row in evidence["signature_demonstration"]))


if __name__ == "__main__":
    unittest.main()
