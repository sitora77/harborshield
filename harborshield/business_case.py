"""Deterministic, assumption-led order economics, separate from claims simulation."""
import copy
import json
import math
from pathlib import Path

MAX_EVENT_AMOUNT = 1e15


def load_case(path):
    case = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_case(case)
    return case


def _number(record, key, minimum=0, maximum=1e9):
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key}: a numeric input is required")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{key}: must be finite and between {minimum} and {maximum}")
    return float(value)


def validate_case(case):
    if not isinstance(case, dict) or not isinstance(case.get("order"), dict):
        raise ValueError("A case object with an order is required")
    order = case["order"]
    if order.get("currency") != "USD":
        raise ValueError("Only USD is supported; no implicit FX conversion")
    if not isinstance(order.get("order_id"), str) or not order["order_id"].strip():
        raise ValueError("order_id is required")
    quantity = _number(order, "quantity", 1, 1e7)
    if quantity != int(quantity):
        raise ValueError("quantity must be a whole number of units")
    for key in ("unit_purchase_price", "unit_sale_price", "daily_demand", "initial_cash"):
        _number(order, key)
    if order["unit_sale_price"] < order["unit_purchase_price"]:
        raise ValueError("This contribution model requires sale price >= purchase price")
    for key in ("stock_cover_days", "customer_payment_days"):
        _number(order, key, 0, 365)
    _number(order, "supplier_deposit_day", -365, 0)
    _number(order, "supplier_deposit_fraction", 0, 1)
    _number(order, "annual_funding_rate", 0, 1)
    _number(case, "selected_port_delay_days", 0, 365)
    constraints = case.get("constraints", {})
    if not isinstance(constraints, dict):
        raise ValueError("constraints must be an object")
    for key, maximum in (("funding_limit", MAX_EVENT_AMOUNT), ("latest_availability_day", 5000)):
        if constraints.get(key) is not None:
            _number(constraints, key, 0, maximum)
    if "minimum_net_contribution" in constraints:
        _number(constraints, "minimum_net_contribution", 0, MAX_EVENT_AMOUNT)
    purchase = quantity * order["unit_purchase_price"]
    sales = quantity * order["unit_sale_price"]
    if max(purchase, sales) > MAX_EVENT_AMOUNT:
        raise ValueError("Order purchase/sales values exceed the supported 1e15 USD event limit")
    options = case.get("options")
    if not isinstance(options, list) or not 1 <= len(options) <= 20:
        raise ValueError("Provide 1–20 options")
    ids = []
    for option in options:
        if not isinstance(option, dict) or not isinstance(option.get("id"), str) or not option["id"]:
            raise ValueError("Every option requires a nonempty id")
        if not isinstance(option.get("name"), str) or not option["name"]:
            raise ValueError("Every option requires a name")
        ids.append(option["id"])
        for key in ("transit_days", "document_release_days"):
            _number(option, key, 0, 365)
        _number(option, "port_delay_multiplier", 0, 10)
        for key in ("freight_cost", "insurance_premium", "other_logistics_cost"):
            _number(option, key)
        logistics = sum(option[key] for key in ("freight_cost", "insurance_premium", "other_logistics_cost"))
        if purchase + logistics > MAX_EVENT_AMOUNT:
            raise ValueError("Purchase plus logistics exceeds the supported 1e15 USD event limit")
    if len(ids) != len(set(ids)):
        raise ValueError("Option ids must be unique")


def funding_ledger(events, initial_cash, annual_rate):
    """Integrate negative cash balances over exact intervals (ACT/365 simple).

    Same-day flows are netted. Own cash is available at the first event. Interest
    is an output, not capitalised into the ledger, which ends at collection.
    """
    _number({"cash": initial_cash}, "cash")
    _number({"rate": annual_rate}, "rate", 0, 1)
    if not events:
        raise ValueError("At least one cash-flow event is required")
    grouped = {}
    for event in events:
        day = _number(event, "day", -365, 5000)
        amount = _number(event, "amount", -MAX_EVENT_AMOUNT, MAX_EVENT_AMOUNT)
        grouped.setdefault(day, []).append((str(event.get("label", "Cash flow")), amount))
    balance, area, peak = float(initial_cash), 0.0, 0.0
    previous = min(grouped)
    rows = []
    for day in sorted(grouped):
        area += max(-balance, 0.0) * (day - previous)
        amount = sum(value for _, value in grouped[day])
        balance += amount
        peak = max(peak, -balance)
        rows.append({"day": day, "event": "; ".join(label for label, _ in grouped[day]),
                     "net_flow": amount, "cash_balance": balance,
                     "funding_need": max(-balance, 0.0)})
        previous = day
    return {"events": rows, "funding_dollar_days": area,
            "funding_cost": area * annual_rate / 365,
            "peak_funding_need": peak, "closing_cash_before_interest": balance,
            "residual_funding_need": max(-balance, 0.0)}


def evaluate_option(order, option, port_delay_days):
    """All financial terms are explicitly constructed, not market quotations."""
    # Reuse the same guards as imports, even for direct API calls.
    validate_case({"order": order, "options": [option],
                   "selected_port_delay_days": port_delay_days})
    purchase = order["quantity"] * order["unit_purchase_price"]
    sales = order["quantity"] * order["unit_sale_price"]
    unit_margin = order["unit_sale_price"] - order["unit_purchase_price"]
    availability = (option["transit_days"] + port_delay_days * option["port_delay_multiplier"]
                    + option["document_release_days"])
    shortage_days = max(availability - order["stock_cover_days"], 0)
    # Continuous daily-demand approximation; bounded by replenishment volume.
    unmet_units = min(order["quantity"], shortage_days * order["daily_demand"])
    opportunity = unmet_units * unit_margin
    logistics = sum(option[key] for key in ("freight_cost", "insurance_premium", "other_logistics_cost"))
    collection = availability + order["customer_payment_days"]
    deposit = purchase * order["supplier_deposit_fraction"]
    ledger = funding_ledger([
        {"day": order["supplier_deposit_day"], "amount": -deposit, "label": "Supplier deposit"},
        {"day": 0, "amount": -(purchase - deposit), "label": "Supplier balance"},
        {"day": 0, "amount": -logistics, "label": "Logistics paid"},
        {"day": collection, "amount": sales, "label": "Constructed customer receipt"},
    ], order["initial_cash"], order["annual_funding_rate"])
    burden = logistics + ledger["funding_cost"] + opportunity
    return {"option_id": option["id"], "option": option["name"], "currency": "USD",
            "availability_day": availability, "collection_day": collection,
            "stockout_days": shortage_days, "unmet_units": unmet_units,
            "purchase_value": purchase, "sales_receipt": sales,
            "planned_contribution": sales - purchase, "logistics_cost": logistics,
            "stockout_opportunity_cost": opportunity,
            "economic_burden": burden, "net_economic_contribution": sales - purchase - burden,
            **ledger}


def compare_options(case, port_delay_days=None):
    validate_case(case)
    delay = case["selected_port_delay_days"] if port_delay_days is None else port_delay_days
    rows = [evaluate_option(case["order"], option, delay) for option in case["options"]]
    constraints = case.get("constraints", {})
    for row in rows:
        reasons = []
        if constraints.get("funding_limit") is not None and row["peak_funding_need"] > constraints["funding_limit"]:
            reasons.append("FUNDING_LIMIT_EXCEEDED")
        if constraints.get("latest_availability_day") is not None and row["availability_day"] > constraints["latest_availability_day"]:
            reasons.append("AVAILABILITY_DEADLINE_MISSED")
        row["constraint_feasible"] = not reasons
        row["economically_acceptable"] = row["net_economic_contribution"] >= constraints.get("minimum_net_contribution", 0)
        if not row["economically_acceptable"]:
            reasons.append("CONTRIBUTION_BELOW_MINIMUM")
        row["ineligibility_reasons"] = reasons
        row["eligible"] = not reasons
    return sorted(rows, key=lambda row: (row["economic_burden"], row["option_id"]))


def decision_summary(rows):
    """Never confuse unconstrained cost rank with an admissible recommendation."""
    eligible = [row for row in rows if row["eligible"]]
    return {"status": "eligible_option_found" if eligible else "no_eligible_option",
            "recommended_option_id": eligible[0]["option_id"] if eligible else None,
            "unconstrained_lowest_burden_option_id": rows[0]["option_id"] if rows else None,
            "eligible_option_count": len(eligible)}


def case_report(case):
    validate_case(case)
    selected = compare_options(case)
    sensitivity = []
    for delay in (0, 2.5, 7):
        for rate in (0.03, 0.08, 0.15):
            for stock in (8, 12, 18):
                variant = copy.deepcopy(case)
                variant["order"].update(annual_funding_rate=rate, stock_cover_days=stock)
                rows = compare_options(variant, delay)
                sensitivity.append({"port_delay_days": delay, "annual_funding_rate": rate,
                                    "stock_cover_days": stock, "lowest_burden_option": rows[0]["option_id"],
                                    "minimum_economic_burden": rows[0]["economic_burden"],
                                    **decision_summary(rows)})
    constraint_examples = []
    for limit, deadline in ((129000, 15), (129000, 12), (130200, 12), (0, 0)):
        variant = copy.deepcopy(case)
        variant["constraints"] = {"funding_limit": limit, "latest_availability_day": deadline,
                                  "minimum_net_contribution": 0}
        rows = compare_options(variant)
        constraint_examples.append({"constraints": variant["constraints"],
                                    "comparison": rows, **decision_summary(rows)})
    return {"case_id": case.get("case_id", "user-supplied"), "version": "0.4",
            "data_status": "Constructed decision analysis, not observed savings or a financing offer",
            "inputs": copy.deepcopy(case), "selected_comparison": selected,
            "selected_decision": decision_summary(selected),
            "no_port_delay_comparison": compare_options(case, 0),
            "sensitivity": sensitivity, "constraint_examples": constraint_examples}
