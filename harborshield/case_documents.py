"""Bind constructed order inputs, checked JSON documents and decision evidence.

This teaching pipeline does not issue policies or certify real trades.
"""
import copy
import hashlib
from decimal import Decimal, InvalidOperation

from .business_case import compare_options, decision_summary, validate_case
from .trade_documents import canonical_bytes, check_documents


def documents_from_case(case):
    validate_case(case)
    order = case["order"]
    terms = case.get("document_terms", {})
    if not isinstance(terms, dict):
        raise ValueError("document_terms must be an object")
    value = Decimal(str(order["quantity"])) * Decimal(str(order["unit_purchase_price"]))
    try:
        multiplier = Decimal(str(terms.get("valuation_multiplier", 1.1)))
        if not multiplier.is_finite() or multiplier <= 0:
            raise InvalidOperation
    except InvalidOperation as exc:
        raise ValueError("A positive finite document valuation multiplier is required") from exc
    shared = {"order_id": order["order_id"], "currency": order["currency"]}
    bundle = {
        "data_status": "Constructed, AI-assisted educational demonstration; not issuer-approved documents",
        "invoice": {**shared, "document_id": "DEMO-INV-001", "departure_date": terms.get("departure_date"),
                    "total_value": float(value), "items": [{"sku": "DEMO-ELECTRONIC", "quantity": order["quantity"],
                                                           "unit_price": order["unit_purchase_price"]}]},
        "packing_list": {**shared, "document_id": "DEMO-PACK-001",
                         "items": [{"sku": "DEMO-ELECTRONIC", "quantity": order["quantity"]}]},
        "insurance_application": {**shared, "document_id": "DEMO-INS-001", "cargo_value": float(value),
                                  "valuation_multiplier": float(multiplier), "requested_insured_value": float(value * multiplier),
                                  "cover_start": terms.get("cover_start"), "cover_end": terms.get("cover_end")},
        "case_context": {"inputs": copy.deepcopy(case), "decision": decision_summary(compare_options(case)),
                         "inputs_sha256": hashlib.sha256(canonical_bytes(case)).hexdigest()},
    }
    checks = check_documents(bundle)
    if not checks["consistent"]:
        raise ValueError("Constructed document terms are missing, inconsistent or exceed the document checker limits")
    return bundle
