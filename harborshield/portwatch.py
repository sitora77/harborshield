"""Auditable, historical one-day-ahead forecasts of AIS-derived port calls.

This independent evidence layer does not calibrate delays, claims or finance.
"""
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import re
from typing import Dict, List

import numpy as np

SOURCE = "https://portwatch.imf.org/datasets/83b1bbc7b3354c5fb1f40673bb8f852e/about"
ENDPOINT = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Ports_Data/FeatureServer/0/query"
TERMS = "https://www.imf.org/en/about/copyright-and-terms"
ATTRIBUTION = "Sources: UN Global Platform; IMF PortWatch (portwatch.imf.org)."
METHODS = {
    "yesterday": "Yesterday's observed count",
    "last_week": "Same weekday last week",
    "mean_28": "Previous 28-day mean",
    "weekday_4": "Same weekday, previous four weeks",
    "ridge_ar": "Ridge autoregression (fixed penalty 10)",
}
LAGS = (1, 2, 7, 14, 28)


def strict_date(value: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Expected YYYY-MM-DD date")
    return date.fromisoformat(value)


def validate_records(records: List[Dict], start="2022-01-01", end="2024-12-31") -> List[Dict]:
    """Reject gaps, duplicates, wrong scope and invalid counts; never fill with zero."""
    first, last = strict_date(start), strict_date(end)
    if last < first:
        raise ValueError("Reversed date window")
    seen = set()
    for row in records:
        day = strict_date(row.get("date"))
        if row.get("portid") != "port1201" or row.get("portname") != "Singapore":
            raise ValueError("Wrong port: expected Singapore port1201")
        if not first <= day <= last:
            raise ValueError("Date outside requested window")
        if day in seen:
            raise ValueError("Duplicate daily observation")
        seen.add(day)
        for key in ("portcalls_container", "portcalls"):
            value = row.get(key)
            if type(value) is not int or value < 0:
                raise ValueError("Port calls must be nonnegative integers, not missing values")
        if row["portcalls_container"] > row["portcalls"]:
            raise ValueError("Container calls exceed total calls")
    expected = (last - first).days + 1
    if len(seen) != expected:
        raise ValueError(f"Missing dates: expected {expected}, received {len(seen)}")
    return sorted(records, key=lambda row: row["date"])


def load_snapshot(directory: Path):
    """Check both the canonical snapshot and the untouched API-response hashes."""
    metadata = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
    content = (directory / "singapore_daily.json").read_bytes()
    if hashlib.sha256(content).hexdigest() != metadata["snapshot_sha256"]:
        raise ValueError("Snapshot checksum mismatch")
    original = []
    for page in metadata["raw_pages"]:
        path = Path(page["file"])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Invalid raw-page path")
        raw = (directory / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != page["sha256"]:
            raise ValueError("Raw API-response checksum mismatch")
        original.extend(feature["attributes"] for feature in json.loads(raw)["features"])
    records = json.loads(content)
    if records != original:
        raise ValueError("Canonical snapshot differs from original source attributes")
    rows = validate_records(records, metadata["start"], metadata["end"])
    if len(rows) != metadata["source_count"]:
        raise ValueError("Source count does not reconcile")
    metadata["hashes_verified"] = True
    return rows, metadata


def metrics(actual, predicted):
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if (actual.ndim != 1 or actual.shape != predicted.shape or not actual.size
            or not np.isfinite(actual).all() or not np.isfinite(predicted).all()
            or (actual < 0).any() or (predicted < 0).any()):
        raise ValueError("Metrics require matching, finite, nonnegative series")
    errors = predicted - actual
    total = float(actual.sum())
    return {"n": int(actual.size), "mae": float(np.abs(errors).mean()),
            "rmse": float(np.sqrt(np.square(errors).mean())),
            "wape": float(np.abs(errors).sum() / total) if total else None,
            "bias": float(errors.mean())}


def feature_row(values, days, index):
    if index < max(LAGS):
        raise ValueError("Insufficient lag history")
    # Only days strictly before the prediction target; weekday is known in advance.
    return [float(values[index - lag]) for lag in LAGS] + [
        float(days[index].weekday() == weekday) for weekday in range(1, 7)]


def fit_ridge(values, days, stop):
    if stop <= max(LAGS):
        raise ValueError("Insufficient training history")
    x = np.asarray([feature_row(values, days, i) for i in range(max(LAGS), stop)])
    y = np.asarray(values[max(LAGS):stop], dtype=float)
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale[scale == 0] = 1
    x = np.column_stack([np.ones(len(x)), (x - mean) / scale])
    penalty = np.eye(x.shape[1]) * 10.0
    penalty[0, 0] = 0  # intercept is not penalised
    # Explicit sums avoid platform-specific BLAS floating-point status warnings.
    gram = np.einsum("ni,nj->ij", x, x, optimize=False)
    rhs = np.einsum("ni,n->i", x, y, optimize=False)
    coefficients = np.linalg.solve(gram + penalty, rhs)
    return {"mean": mean, "scale": scale, "coefficients": coefficients,
            "trained_through": days[stop - 1].isoformat()}


def predict_one(method, values, days, index, model=None):
    if index < 28 or method not in METHODS:
        raise ValueError("Invalid method or insufficient history")
    if method == "yesterday":
        result = values[index - 1]
    elif method == "last_week":
        result = values[index - 7]
    elif method == "mean_28":
        result = np.mean(values[index - 28:index])
    elif method == "weekday_4":
        result = np.mean([values[index - lag] for lag in (7, 14, 21, 28)])
    else:
        if model is None or strict_date(model["trained_through"]) >= days[index]:
            raise ValueError("Ridge model must be fitted before the forecast target")
        feature = (np.asarray(feature_row(values, days, index)) - model["mean"]) / model["scale"]
        result = np.r_[1.0, feature] @ model["coefficients"]
    return max(0.0, float(result))


def run_backtest(records, metadata):
    records = validate_records(records)
    days = [strict_date(row["date"]) for row in records]
    values = np.asarray([row["portcalls_container"] for row in records], dtype=float)
    train_stop = days.index(date(2023, 1, 1))
    validation_stop = days.index(date(2024, 1, 1))
    validation_indices = list(range(train_stop, validation_stop))
    test_indices = list(range(validation_stop, len(days)))
    validation_model = fit_ridge(values, days, train_stop)
    validation = {}
    for method in METHODS:
        predictions = [predict_one(method, values, days, i, validation_model) for i in validation_indices]
        validation[method] = metrics(values[validation_indices], predictions)
    # Stable tie-breaking is specified by METHODS insertion order. No test label enters selection.
    selected = min(METHODS, key=lambda method: validation[method]["mae"])
    final_model = fit_ridge(values, days, validation_stop)
    test = {}
    predictions_by_method = {}
    for method in METHODS:
        predictions = [predict_one(method, values, days, i, final_model) for i in test_indices]
        predictions_by_method[method] = predictions
        test[method] = metrics(values[test_indices], predictions)
    selected_mae = test[selected]["mae"]
    baseline_mae = test["yesterday"]["mae"]
    forecasts = [{"date": days[i].isoformat(), "actual": int(values[i]),
                  "predicted": predictions_by_method[selected][j],
                  "yesterday": predictions_by_method["yesterday"][j]}
                 for j, i in enumerate(test_indices)]
    months = []
    for month in range(1, 13):
        subset = [row for row in forecasts if strict_date(row["date"]).month == month]
        months.append({"month": f"2024-{month:02d}",
                       "actual_mean": float(np.mean([row["actual"] for row in subset])),
                       "predicted_mean": float(np.mean([row["predicted"] for row in subset])),
                       **metrics([row["actual"] for row in subset], [row["predicted"] for row in subset])})
    return {"version": "0.5", "task": "One-day-ahead Singapore container-ship port-call forecasting",
            "unit": "AIS-derived container-ship port calls per UTC day; not unique vessels or TEU",
            "source": {"dataset": SOURCE, "attribution": ATTRIBUTION, "terms": TERMS,
                       "retrieved_at_utc": metadata["retrieved_at_utc"],
                       "snapshot_sha256": metadata["snapshot_sha256"], "portid": "port1201"},
            "quality": {"rows": len(records), "start": days[0].isoformat(), "end": days[-1].isoformat(),
                        "missing_dates": 0, "duplicate_dates": 0, "invalid_counts": 0,
                        "zero_count_days": int((values == 0).sum()),
                        "source_hashes_verified": metadata.get("hashes_verified") is True},
            "splits": {"train": {"start": "2022-01-01", "end": "2022-12-31", "n": train_stop},
                       "validation": {"start": "2023-01-01", "end": "2023-12-31", "n": len(validation_indices)},
                       "test": {"start": "2024-01-01", "end": "2024-12-31", "n": len(test_indices)}},
            "protocol": "Choose by 2023 validation MAE. Refit ridge on 2022–2023 only; freeze coefficients. "
                        "Each 2024 forecast uses observed earlier days, not the current or future target. "
                        "This is rolling one-day-ahead evaluation, not a year-ahead forecast. "
                        "Historical records downloaded later may be revised; this is not an as-of-2024 vintage backtest.",
            "selected_method": selected, "method_names": METHODS, "validation": validation, "test": test,
            "mae_improvement_vs_yesterday": 1 - selected_mae / baseline_mae if baseline_mae else None,
            "final_ridge_fit": {key: value.tolist() if isinstance(value, np.ndarray) else value
                                for key, value in final_model.items()},
            "monthly": months, "forecasts": forecasts,
            "limitations": ["Port calls are AIS-derived indicators, not observed port waiting times, cargo delays or losses.",
                            "No observed invoices, carrier quotations, claims, premiums or funding costs are available.",
                            "No causal congestion effect, calibrated insurance price or realised operational savings is established.",
                            "One port, one held-out year and a later-retrieved data vintage; external generalisation is untested.",
                            "No automatic mapping from predicted calls to the constructed order's port-delay assumption.",
                            "AI-assisted implementation; personal learning and independent replication remain to be documented."]}
