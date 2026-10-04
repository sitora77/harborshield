import copy
from pathlib import Path
import unittest

from harborshield.trade_documents import (check_documents, new_demo_key, parse_json_bytes,
                                        public_key_text, sign_document, verify_document)

ROOT = Path(__file__).resolve().parents[1]


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.bundle = parse_json_bytes((ROOT / "data/cases/demo_documents.json").read_bytes())

    def codes(self, bundle):
        return {issue["code"] for issue in check_documents(bundle)["issues"]}

    def test_valid_bundle_including_explicit_110_percent_valuation(self):
        self.assertTrue(check_documents(self.bundle)["consistent"])

    def test_invoice_arithmetic_and_insurance_value(self):
        self.bundle["invoice"]["total_value"] += 1
        self.assertIn("INVOICE_ARITHMETIC", self.codes(self.bundle))
        self.assertIn("CARGO_VALUE_MISMATCH", self.codes(self.bundle))
        self.bundle["insurance_application"]["requested_insured_value"] = 150000
        self.assertIn("INSURED_VALUE_MISMATCH", self.codes(self.bundle))

    def test_sku_quantity_and_order_currency_mismatch(self):
        self.bundle["packing_list"]["items"][0]["quantity"] -= 1
        self.bundle["packing_list"]["order_id"] = "OTHER"
        self.bundle["packing_list"]["currency"] = "SGD"
        self.assertIn("SKU_QUANTITY_MISMATCH", self.codes(self.bundle))
        self.assertIn("CROSS_DOCUMENT_MISMATCH", self.codes(self.bundle))

    def test_missing_fields_are_not_healthy_zero(self):
        del self.bundle["invoice"]["items"][0]["unit_price"]
        self.assertIn("INVALID_NUMBER", self.codes(self.bundle))
        del self.bundle["insurance_application"]
        self.assertIn("MISSING_DOCUMENT", self.codes(self.bundle))

    def test_bad_date_and_departure_window(self):
        self.bundle["invoice"]["departure_date"] = "2024-02-30"
        self.assertIn("INVALID_DATE", self.codes(self.bundle))
        self.bundle["invoice"]["departure_date"] = "2024-07-01"
        self.assertIn("DEPARTURE_OUTSIDE_COVER_WINDOW", self.codes(self.bundle))

    def test_only_calendar_yyyy_mm_dd_on_all_python_versions(self):
        for value in ("2024-W21-1", "20240520", "2024-5-20", "2024-02-30", "２０２４-05-20"):
            with self.subTest(value=value):
                self.bundle["invoice"]["departure_date"] = value
                self.assertIn("INVALID_DATE", self.codes(self.bundle))
        self.bundle["invoice"]["departure_date"] = "2024-02-29"
        self.bundle["insurance_application"].update(cover_start="2024-02-28", cover_end="2024-03-01")
        self.assertTrue(check_documents(self.bundle)["consistent"])

    def test_duplicate_ids_and_duplicate_register(self):
        self.bundle["packing_list"]["document_id"] = self.bundle["invoice"]["document_id"]
        self.assertIn("DUPLICATE_DOCUMENT_ID", self.codes(self.bundle))
        result = check_documents(self.bundle, ["DEMO-INV-001"])
        self.assertIn("POSSIBLE_DUPLICATE_INVOICE", {issue["code"] for issue in result["issues"]})

    def test_duplicate_sku_and_noninteger_quantity(self):
        self.bundle["invoice"]["items"].append(copy.deepcopy(self.bundle["invoice"]["items"][0]))
        self.assertIn("DUPLICATE_SKU", self.codes(self.bundle))
        self.bundle["packing_list"]["items"][0]["quantity"] = 3.5
        self.assertIn("INVALID_QUANTITY", self.codes(self.bundle))

    def test_nonfinite_and_bad_shapes(self):
        self.bundle["invoice"]["total_value"] = float("nan")
        self.bundle["packing_list"]["items"] = [{"sku": [], "quantity": True}]
        self.assertFalse(check_documents(self.bundle)["consistent"])
        self.assertFalse(check_documents([])["consistent"])
        self.bundle["invoice"]["total_value"] = "1e999999"
        self.assertIn("INVALID_NUMBER", self.codes(self.bundle))

    def test_json_size_duplicate_keys_and_nonfinite_rejected(self):
        for data in (b'{"x":1,"x":2}', b'{"x":NaN}', b'[]', b'x' * 200001):
            with self.subTest(data=data[:20]), self.assertRaises(ValueError):
                parse_json_bytes(data)

    def test_signature_valid_only_against_separate_anchor(self):
        key = new_demo_key()
        signed = sign_document(self.bundle, key)
        result = verify_document(signed, public_key_text(key))
        self.assertTrue(result["accepted_demo_signature"])
        self.assertFalse(result["document_truth_verified"])
        no_anchor = verify_document(signed)
        self.assertTrue(no_anchor["signature_valid"])
        self.assertFalse(no_anchor["accepted_demo_signature"])

    def test_tampering_and_issuer_metadata_fail(self):
        key = new_demo_key()
        signed = sign_document(self.bundle, key)
        altered = copy.deepcopy(signed)
        altered["payload"]["invoice"]["total_value"] += 1
        self.assertFalse(verify_document(altered, public_key_text(key))["signature_valid"])
        signed["issuer"] = "An actual bank"
        self.assertFalse(verify_document(signed, public_key_text(key))["signature_valid"])

    def test_replacement_key_cannot_self_assert_trust(self):
        trusted = new_demo_key()
        replacement = sign_document(self.bundle, new_demo_key())
        result = verify_document(replacement, public_key_text(trusted))
        self.assertTrue(result["signature_valid"])
        self.assertFalse(result["issuer_key_matches_anchor"])
        self.assertFalse(result["accepted_demo_signature"])

    def test_malformed_signature_returns_false_and_keys_not_exported(self):
        signed = sign_document(self.bundle, new_demo_key())
        self.assertNotIn("private_key", signed)
        signed["signature"] = "@@invalid@@"
        self.assertFalse(verify_document(signed)["signature_valid"])
        self.assertFalse(verify_document({})["signature_valid"])


if __name__ == "__main__":
    unittest.main()
