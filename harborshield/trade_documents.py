"""Structured-document checks and a standalone Ed25519 teaching envelope.

Not a TradeTrust/W3C credential, legal eBL, policy approval or fraud classifier.
Private keys are generated in memory; embedded public keys are NOT trust anchors.
"""
import base64
import copy
from datetime import date
from decimal import Decimal, InvalidOperation
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

MAX_JSON_BYTES = 200_000


def parse_json_bytes(data):
    if len(data) > MAX_JSON_BYTES:
        raise ValueError("JSON exceeds 200 KB limit")
    def reject_constant(value):
        raise ValueError(f"Non-finite JSON value: {value}")
    def unique_object(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError(f"Duplicate JSON key: {key}")
            obj[key] = value
        return obj
    try:
        value = json.loads(data, parse_constant=reject_constant, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Invalid or excessively nested JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def check_documents(bundle, known_invoice_ids=()):
    """Return explicit diagnostics; missing inputs cannot become a healthy PASS."""
    issues = []
    def issue(code, field, message):
        issues.append({"code": code, "field": field, "message": message})
    def amount(record, key, path, positive=False):
        value = record.get(key)
        try:
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise InvalidOperation
            result = Decimal(str(value))
            if not result.is_finite() or not Decimal(0) <= result <= Decimal("1e12") or (positive and result == 0):
                raise InvalidOperation
            return result
        except (InvalidOperation, ValueError):
            issue("INVALID_NUMBER", path + "." + key, "A finite amount between 0 and 1e12 is required (positive for quantities/multipliers)")
            return None
    if not isinstance(bundle, dict):
        return {"consistent": False, "issues": [{"code": "INVALID_BUNDLE", "field": "root", "message": "An object is required"}]}
    docs = {}
    for name in ("invoice", "packing_list", "insurance_application"):
        record = bundle.get(name)
        if not isinstance(record, dict):
            issue("MISSING_DOCUMENT", name, "A structured document object is required")
        else:
            docs[name] = record
            for key in ("document_id", "order_id", "currency"):
                if not isinstance(record.get(key), str) or not record[key].strip():
                    issue("MISSING_FIELD", name + "." + key, "A nonempty identifier is required")
    if len(docs) != 3:
        return {"consistent": False, "issues": issues}
    inv, pack, insurance = (docs[name] for name in ("invoice", "packing_list", "insurance_application"))
    for key in ("order_id", "currency"):
        values = [record.get(key) for record in docs.values()]
        if any(value != values[0] for value in values[1:]):
            issue("CROSS_DOCUMENT_MISMATCH", key, "Values differ between documents")
    if inv.get("currency") != "USD":
        issue("UNSUPPORTED_CURRENCY", "invoice.currency", "USD only; FX is not inferred")
    identifiers = [record.get("document_id") for record in docs.values()]
    if any(isinstance(value, str) and identifiers.count(value) > 1 for value in identifiers):
        issue("DUPLICATE_DOCUMENT_ID", "document_id", "Document identifiers must be distinct")
    if inv.get("document_id") in known_invoice_ids:
        issue("POSSIBLE_DUPLICATE_INVOICE", "invoice.document_id", "Identifier appears in the supplied comparison register; not proof of fraud")
    maps = {}
    invoice_sum = Decimal(0)
    invoice_complete = True
    for name, record in (("invoice", inv), ("packing_list", pack)):
        items = record.get("items")
        if not isinstance(items, list) or not 1 <= len(items) <= 1000:
            issue("INVALID_ITEMS", name + ".items", "Provide 1–1000 SKU lines")
            invoice_complete = False
            continue
        mapping = {}
        for index, item in enumerate(items):
            path = f"{name}.items[{index}]"
            if not isinstance(item, dict):
                issue("INVALID_ITEM", path, "An item object is required")
                invoice_complete = False
                continue
            sku = item.get("sku")
            if not isinstance(sku, str) or not sku.strip():
                issue("INVALID_SKU", path + ".sku", "SKU is required")
                invoice_complete = False
                continue
            qty = amount(item, "quantity", path, positive=True)
            if qty is not None and qty != qty.to_integral_value():
                issue("INVALID_QUANTITY", path + ".quantity", "Quantity is whole units, not carton count")
                qty = None
            if sku in mapping:
                issue("DUPLICATE_SKU", path + ".sku", "One aggregate line per SKU is required")
            mapping[sku] = qty
            if name == "invoice":
                price = amount(item, "unit_price", path)
                if qty is None or price is None:
                    invoice_complete = False
                else:
                    invoice_sum += qty * price
        maps[name] = mapping
    if "invoice" in maps and "packing_list" in maps:
        if maps["invoice"] != maps["packing_list"]:
            issue("SKU_QUANTITY_MISMATCH", "items", "SKU quantities differ between invoice and packing list")
    total = amount(inv, "total_value", "invoice")
    cargo = amount(insurance, "cargo_value", "insurance_application")
    multiplier = amount(insurance, "valuation_multiplier", "insurance_application", positive=True)
    insured = amount(insurance, "requested_insured_value", "insurance_application")
    # Monetary comparisons use cents; no claim that any multiplier is legally required.
    cents = lambda value: value.quantize(Decimal("0.01"))
    try:
        if total is not None and invoice_complete and cents(total) != cents(invoice_sum):
            issue("INVOICE_ARITHMETIC", "invoice.total_value", "Total differs from quantity × unit price")
        if total is not None and cargo is not None and cents(total) != cents(cargo):
            issue("CARGO_VALUE_MISMATCH", "insurance_application.cargo_value", "Declared cargo value differs from invoice")
        if None not in (cargo, multiplier, insured) and cents(cargo * multiplier) != cents(insured):
            issue("INSURED_VALUE_MISMATCH", "insurance_application.requested_insured_value", "Insured value differs from the explicitly supplied valuation multiplier")
    except InvalidOperation:
        issue("AMOUNT_OUT_OF_RANGE", "amounts", "Amount exceeds supported decimal precision")
    dates = {}
    for name, record, key in (("invoice", inv, "departure_date"),
                              ("insurance_application", insurance, "cover_start"),
                              ("insurance_application", insurance, "cover_end")):
        try:
            raw = record.get(key)
            if not isinstance(raw, str) or len(raw) != 10:
                raise ValueError
            dates[key] = date.fromisoformat(raw)
        except (ValueError, TypeError):
            issue("INVALID_DATE", name + "." + key, "An ISO YYYY-MM-DD date is required")
    if len(dates) == 3:
        if dates["cover_start"] > dates["cover_end"]:
            issue("INVALID_COVER_WINDOW", "insurance_application", "Cover start is after cover end")
        elif not dates["cover_start"] <= dates["departure_date"] <= dates["cover_end"]:
            issue("DEPARTURE_OUTSIDE_COVER_WINDOW", "invoice.departure_date", "Departure is outside the requested cover window; this is not a coverage determination")
    return {"consistent": not issues, "issues": issues,
            "scope": "Document consistency only; does not prove cargo existence, issuer identity, coverage or creditworthiness"}


def canonical_bytes(value):
    """Project-local encoding, NOT RFC 8785 / TradeTrust canonicalisation."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def new_demo_key():
    return Ed25519PrivateKey.generate()


def public_key_text(key):
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii")


def sign_document(payload, private_key):
    body = {"schema": "harborshield-demo-signature-v1", "algorithm": "Ed25519",
            "issuer": "HarborShield temporary DEMO issuer", "payload": copy.deepcopy(payload)}
    signature = private_key.sign(canonical_bytes(body))
    return {**body, "public_key": public_key_text(private_key),
            "signature": base64.b64encode(signature).decode("ascii")}


def verify_document(envelope, expected_public_key=None):
    result = {"signature_valid": False, "issuer_key_matches_anchor": False,
              "accepted_demo_signature": False, "document_truth_verified": False}
    try:
        if not isinstance(envelope, dict) or set(envelope) != {"schema", "algorithm", "issuer", "payload", "public_key", "signature"}:
            raise ValueError("Unexpected envelope fields")
        if envelope["schema"] != "harborshield-demo-signature-v1" or envelope["algorithm"] != "Ed25519":
            raise ValueError("Unsupported signature schema or algorithm")
        raw_key = base64.b64decode(envelope["public_key"], validate=True)
        key = Ed25519PublicKey.from_public_bytes(raw_key)
        body = {name: envelope[name] for name in ("schema", "algorithm", "issuer", "payload")}
        key.verify(base64.b64decode(envelope["signature"], validate=True), canonical_bytes(body))
        result["signature_valid"] = True
        result["issuer_key_matches_anchor"] = bool(expected_public_key and raw_key == base64.b64decode(expected_public_key, validate=True))
        result["accepted_demo_signature"] = result["issuer_key_matches_anchor"]
    except (InvalidSignature, ValueError, TypeError, KeyError, RecursionError):
        pass
    return result
