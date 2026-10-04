"""Shared-language rendering and same-order constructed evidence tests."""
import copy
import hashlib
import json
from pathlib import Path
import re
import unittest

from harborshield.business_case import case_report, load_case
from harborshield.case_documents import documents_from_case
from harborshield.case_page import build_page
from harborshield.trade_documents import (canonical_bytes, check_documents, new_demo_key,
                                        public_key_text, sign_document, verify_document)

ROOT = Path(__file__).resolve().parents[1]


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.case = load_case(ROOT / "data/cases/singapore_2024.json")

    def test_documents_follow_order_amount_and_quantity(self):
        self.case["order"].update(order_id="DEMO-MY-ORDER", quantity=1234, unit_purchase_price=32.5)
        bundle = documents_from_case(self.case)
        self.assertTrue(check_documents(bundle)["consistent"])
        self.assertEqual(bundle["invoice"]["total_value"], 40105)
        self.assertEqual(bundle["packing_list"]["items"][0]["quantity"], 1234)
        self.assertEqual(bundle["insurance_application"]["cargo_value"], 40105)
        self.assertEqual(bundle["case_context"]["inputs"], self.case)
        self.assertEqual(bundle["case_context"]["inputs_sha256"], hashlib.sha256(canonical_bytes(self.case)).hexdigest())

    def test_signed_context_changes_with_screening_and_tampering(self):
        before = documents_from_case(self.case)
        self.case["constraints"].update(funding_limit=129000, latest_availability_day=12)
        after = documents_from_case(self.case)
        self.assertEqual(before["invoice"], after["invoice"])
        self.assertNotEqual(before["case_context"]["inputs_sha256"], after["case_context"]["inputs_sha256"])
        self.assertIsNone(after["case_context"]["decision"]["recommended_option_id"])
        key = new_demo_key()
        signed = sign_document(after, key)
        self.assertTrue(verify_document(signed, public_key_text(key))["accepted_demo_signature"])
        signed["payload"]["case_context"]["inputs"]["constraints"]["funding_limit"] += 1
        self.assertFalse(verify_document(signed, public_key_text(key))["signature_valid"])

    def test_factory_rejects_invalid_document_terms(self):
        for terms in ({}, {"valuation_multiplier": "not a number"}, {"valuation_multiplier": float("nan")}, []):
            self.case["document_terms"] = terms
            with self.assertRaises(ValueError):
                documents_from_case(self.case)

    def test_bilingual_pages_share_inputs_and_assets(self):
        report = json.loads((ROOT / "reports/case_study.json").read_text(encoding="utf-8"))
        pages = [build_page(report, ROOT, language) for language in ("zh", "en")]
        for page in pages:
            self.assertNotRegex(page, r"@@[a-z0-9_]+@@")
            embedded = re.search(r'<script id="case-inputs" type="application/json">(.*?)</script>', page).group(1)
            self.assertEqual(json.loads(embedded), report["inputs"])
            self.assertIn('id="funding"', page)
            self.assertIn('id="deadline"', page)
            self.assertIn('id="minimum"', page)
            self.assertIn("AI", page)
        self.assertIn('<html lang="en">', pages[1])
        self.assertIn("No eligible option", pages[1])
        self.assertIn('href="case-study.html"', pages[1])
        self.assertEqual(re.findall(r'src="(case-.*?\.js\?v=.*?)"', pages[0]),
                         re.findall(r'src="(case-.*?\.js\?v=.*?)"', pages[1]))

    def test_bilingual_copy_keys_and_reason_codes_match(self):
        copies = json.loads((ROOT / "web/case-copy.json").read_text(encoding="utf-8"))
        self.assertEqual(copies["zh"].keys(), copies["en"].keys())
        self.assertEqual(copies["zh"]["reasons"].keys(), copies["en"]["reasons"].keys())
        self.assertEqual(len(copies["en"]["labels"]), 9)


if __name__ == "__main__":
    unittest.main()
