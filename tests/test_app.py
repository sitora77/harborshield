"""Browser-independent Streamlit interaction checks."""
import unittest
import json
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


class DashboardTests(unittest.TestCase):
    def test_real_data_tab_runs_independently_of_synthetic_shipment(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        report = app.session_state["real_data_summary"]
        self.assertEqual(report["selected_method"], "mean_28")
        self.assertEqual(report["splits"]["test"]["n"], 366)
        next(item for item in app.number_input if item.label == "Cargo value (USD)").set_value(500000).run()
        self.assertEqual(app.session_state["real_data_summary"], report)

    def test_real_data_failure_clears_previous_results_without_substitution(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertIn("real_data_summary", app.session_state)
        with patch("harborshield.portwatch_ui.load_snapshot", side_effect=ValueError("Missing dates")):
            app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertNotIn("real_data_summary", app.session_state)
        self.assertTrue(any("No synthetic data is substituted" in item.value for item in app.error))

    def test_case_inputs_update_decision_and_funding(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["case_comparison"][0]["option_id"], "priority_sea")
        next(item for item in app.slider if item.label == "Case port-delay assumption (days)").set_value(0).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["case_comparison"][0]["option_id"], "standard_sea")

    def test_signature_modes_distinguish_tampering_and_trust(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertTrue(app.session_state["document_checks"]["consistent"])
        self.assertTrue(app.session_state["signature_demo_result"]["accepted_demo_signature"])
        selector = next(item for item in app.selectbox if item.label == "Signature test case")
        selector.set_value("Amount altered after signing").run()
        self.assertFalse(app.session_state["signature_demo_result"]["signature_valid"])
        selector.set_value("Replacement-key re-signing").run()
        self.assertTrue(app.session_state["signature_demo_result"]["signature_valid"])
        self.assertFalse(app.session_state["signature_demo_result"]["accepted_demo_signature"])

    def test_default_dashboard_and_research_button(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        self.assertNotIn("joint_study", app.session_state)
        next(item for item in app.button if item.label == "Run joint-risk experiment").click().run()
        self.assertEqual(len(app.exception), 0)
        result = app.session_state["joint_study"]
        self.assertEqual(result["status"], "sample-optimal")
        self.assertEqual(len(result["comparison"]), 4)
        self.assertNotEqual(result["train_seed"], result["test_seed"])

    def test_all_zero_priorities_show_message_not_exception(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        for label in ("Cost", "Risk", "Time", "Carbon"):
            next(item for item in app.slider if item.label == label).set_value(0)
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("weight above zero" in warning.value for warning in app.warning))
        self.assertEqual(len(app.tabs), 8)
        self.assertEqual(app.session_state["real_data_summary"]["quality"]["rows"], 1096)
        self.assertTrue(app.session_state["document_checks"]["consistent"])
        self.assertIn("case_comparison", app.session_state)
        self.assertTrue(any(item.label == "Run joint-risk experiment" for item in app.button))
        next(item for item in app.slider if item.label == "Case port-delay assumption (days)").set_value(0).run()
        self.assertEqual(app.session_state["case_decision"]["recommended_option_id"], "standard_sea")

    def test_funding_constraint_changes_selection_and_no_option_is_clear(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        next(item for item in app.number_input if item.label == "Assumed external funding limit (USD)").set_value(129000).run()
        self.assertEqual(app.session_state["case_decision"]["recommended_option_id"], "standard_sea")
        next(item for item in app.number_input if item.label == "Latest stock-availability day").set_value(12.0).run()
        self.assertIsNone(app.session_state["case_decision"]["recommended_option_id"])
        self.assertTrue(any("No eligible option" in item.value for item in app.error))

    def test_signature_payload_tracks_current_order_context(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        original = app.session_state["signed_demo_payload"]["case_context"]["inputs_sha256"]
        next(item for item in app.slider if item.label == "Case port-delay assumption (days)").set_value(0).run()
        payload = app.session_state["signed_demo_payload"]
        self.assertNotEqual(original, payload["case_context"]["inputs_sha256"])
        self.assertEqual(payload["case_context"]["decision"]["recommended_option_id"], "standard_sea")
        self.assertEqual(payload["invoice"]["order_id"], app.session_state["current_business_case"]["order"]["order_id"])

    def test_invalid_upload_blocks_signing_instead_of_default_substitution(self):
        upload = SimpleNamespace(getvalue=lambda: b'{"invoice":{}}')
        with patch("streamlit.file_uploader", return_value=upload):
            app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["signature_demo_result"]["status"], "blocked_inconsistent_bundle")
        self.assertFalse(any(item.label == "Signature test case" for item in app.selectbox))

    def test_valid_uploaded_string_amount_signs_that_bundle_and_tamper_is_detected(self):
        bundle = json.loads((APP.parent / "data/cases/demo_documents.json").read_text())
        bundle["invoice"]["total_value"] = "150000"
        for document in ("invoice", "packing_list", "insurance_application"):
            bundle[document]["order_id"] = "DEMO-UPLOADED-ORDER"
        upload = SimpleNamespace(getvalue=lambda: json.dumps(bundle).encode())
        with patch("streamlit.file_uploader", return_value=upload):
            app = AppTest.from_file(str(APP), default_timeout=30).run()
            self.assertTrue(app.session_state["signature_demo_result"]["accepted_demo_signature"])
            self.assertEqual(app.session_state["signed_demo_payload"], bundle)
            next(item for item in app.selectbox if item.label == "Signature test case").set_value("Amount altered after signing").run()
        self.assertEqual(len(app.exception), 0)
        self.assertFalse(app.session_state["signature_demo_result"]["signature_valid"])


if __name__ == "__main__":
    unittest.main()
