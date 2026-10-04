"""Data integrity, chronological selection and explicit look-ahead checks."""
import copy
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from harborshield.portwatch import (METHODS, feature_row, fit_ridge, load_snapshot,
                                    metrics, predict_one, run_backtest, strict_date, validate_records)
from harborshield.portwatch_page import COPY, activity_svg, build_page

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    start = date(2022, 1, 1)
    return [{"date": (start + timedelta(days=i)).isoformat(), "portid": "port1201", "portname": "Singapore",
             "portcalls_container": 25 + i % 7 + (i % 11 == 0) * 5, "portcalls": 200} for i in range(1096)]


class PortWatchTests(unittest.TestCase):
    def setUp(self):
        self.rows = fixture()
        self.days = [strict_date(row["date"]) for row in self.rows]
        self.values = np.array([row["portcalls_container"] for row in self.rows], dtype=float)
        self.metadata = {"retrieved_at_utc": "2026-10-04T00:00:00+00:00", "snapshot_sha256": "fixture"}

    def test_real_snapshot_is_complete_and_traceable(self):
        rows, metadata = load_snapshot(ROOT / "data/portwatch")
        self.assertEqual(len(rows), 1096)
        self.assertEqual(sum(page["rows"] for page in metadata["raw_pages"]), 1096)
        self.assertEqual(rows[0]["date"], "2022-01-01")
        self.assertEqual(rows[-1]["date"], "2024-12-31")
        self.assertEqual(len(metadata["snapshot_sha256"]), 64)

    def test_missing_date_blocks_analysis(self):
        del self.rows[50]
        with self.assertRaisesRegex(ValueError, "Missing dates"):
            validate_records(self.rows)

    def test_duplicate_date_blocks_analysis(self):
        self.rows[50] = copy.deepcopy(self.rows[49])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_records(self.rows)

    def test_missing_negative_boolean_or_float_counts_are_not_coerced(self):
        for bad in (None, -1, True, 3.0, "3", float("nan")):
            self.rows[0]["portcalls_container"] = bad
            with self.assertRaises(ValueError):
                validate_records(self.rows)

    def test_total_count_reconciliation(self):
        self.rows[0]["portcalls"] = 1
        with self.assertRaisesRegex(ValueError, "exceed"):
            validate_records(self.rows)

    def test_wrong_port_and_out_of_window_rejected(self):
        self.rows[0]["portid"] = "port1182"
        with self.assertRaisesRegex(ValueError, "Wrong port"):
            validate_records(self.rows)
        self.rows[0]["portid"] = "port1201"
        self.rows[0]["date"] = "2021-12-31"
        with self.assertRaisesRegex(ValueError, "outside"):
            validate_records(self.rows)

    def test_unsorted_rows_are_sorted_without_changing_values(self):
        self.assertEqual(validate_records(list(reversed(self.rows))), self.rows)

    def test_zero_counts_are_preserved_not_treated_as_missing(self):
        self.rows[0]["portcalls_container"] = 0
        self.assertEqual(validate_records(self.rows)[0]["portcalls_container"], 0)

    def test_strict_dates_reject_ambiguous_dates_and_week_dates(self):
        for value in ("2024-W01-1", "20240101", "2024-2-01", "2024-02-30", None):
            with self.assertRaises(ValueError):
                strict_date(value)

    def test_metrics_use_all_daily_errors_not_percentage_average(self):
        result = metrics([10, 20], [12, 16])
        self.assertEqual(result["mae"], 3)
        self.assertEqual(result["bias"], -1)
        self.assertAlmostEqual(result["rmse"], np.sqrt(10))
        self.assertEqual(result["wape"], 0.2)
        self.assertIsNone(metrics([0, 0], [1, 2])["wape"])

    def test_invalid_metric_inputs_rejected(self):
        for actual, predicted in (([], []), ([1], [1, 2]), ([1], [float("nan")]), ([-1], [0]), ([1], [-1])):
            with self.assertRaises(ValueError):
                metrics(actual, predicted)

    def test_lag_features_exclude_today_and_future(self):
        row = feature_row(self.values, self.days, 730)
        changed = self.values.copy()
        changed[730:] = 999
        self.assertEqual(row, feature_row(changed, self.days, 730))
        self.assertEqual(row[:5], [self.values[730 - lag] for lag in (1, 2, 7, 14, 28)])

    def test_every_method_ignores_current_and_future_targets(self):
        model = fit_ridge(self.values, self.days, 730)
        changed = self.values.copy()
        changed[730:] = 999
        for method in METHODS:
            self.assertEqual(predict_one(method, self.values, self.days, 730, model),
                             predict_one(method, changed, self.days, 730, model))

    def test_model_fit_ignores_values_after_training_stop(self):
        before = fit_ridge(self.values, self.days, 365)
        changed = self.values.copy()
        changed[365:] = 999
        after = fit_ridge(changed, self.days, 365)
        np.testing.assert_array_equal(before["coefficients"], after["coefficients"])
        np.testing.assert_array_equal(before["mean"], after["mean"])

    def test_future_trained_model_is_rejected(self):
        model = fit_ridge(self.values, self.days, 800)
        with self.assertRaisesRegex(ValueError, "before"):
            predict_one("ridge_ar", self.values, self.days, 730, model)

    def test_test_labels_do_not_select_method(self):
        before = run_backtest(self.rows, self.metadata)
        changed = copy.deepcopy(self.rows)
        for row in changed[730:]:
            row["portcalls_container"] = 150
        after = run_backtest(changed, self.metadata)
        self.assertEqual(before["selected_method"], after["selected_method"])
        self.assertEqual(before["validation"], after["validation"])
        self.assertEqual(before["final_ridge_fit"], after["final_ridge_fit"])
        self.assertNotEqual(before["test"], after["test"])

    def test_splits_leap_day_and_prediction_count(self):
        report = run_backtest(self.rows, self.metadata)
        self.assertEqual([split["n"] for split in report["splits"].values()], [365, 365, 366])
        self.assertEqual(len(report["forecasts"]), 366)
        self.assertIn("2024-02-29", [row["date"] for row in report["forecasts"]])
        self.assertEqual(report["final_ridge_fit"]["trained_through"], "2023-12-31")
        self.assertEqual(sum(row["n"] for row in report["monthly"]), 366)

    def test_repeat_run_is_deterministic(self):
        self.assertEqual(run_backtest(self.rows, self.metadata), run_backtest(self.rows, self.metadata))

    def test_tampered_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "singapore_daily.json").write_bytes(b"[]")
            (path / "provenance.json").write_text(json.dumps({"snapshot_sha256": "wrong"}))
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_snapshot(path)

    def test_raw_response_integrity_is_not_bypassed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            content = json.dumps(self.rows).encode()
            (path / "singapore_daily.json").write_bytes(content)
            (path / "page.json").write_bytes(b"tampered")
            (path / "provenance.json").write_text(json.dumps({"snapshot_sha256": hashlib.sha256(content).hexdigest(),
                                                              "raw_pages": [{"file": "page.json", "sha256": "wrong"}]}))
            with self.assertRaisesRegex(ValueError, "Raw API"):
                load_snapshot(path)

    def test_bilingual_evidence_uses_same_daily_results(self):
        report = run_backtest(self.rows, self.metadata)
        for language in ("en", "zh"):
            page = build_page(report, language)
            self.assertIn(f'<html lang="{language}">', page)
            self.assertIn("1,096", page)
            self.assertIn(f'{report["test"][report["selected_method"]]["mae"]:.2f}', page)
            self.assertIn("real-data-report.json", page)
            self.assertIn("AI", page)
            self.assertIn('role="img"', page)
        self.assertEqual(COPY["en"].keys(), COPY["zh"].keys())

    def test_report_reconciles_to_frozen_real_snapshot(self):
        rows, metadata = load_snapshot(ROOT / "data/portwatch")
        saved = json.loads((ROOT / "reports/real-data-report.json").read_text())
        self.assertEqual(saved, run_backtest(rows, metadata))


if __name__ == "__main__":
    unittest.main()
