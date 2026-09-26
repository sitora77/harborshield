"""Utilities for traceable public maritime data snapshots."""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class PortActivityObservation:
    month: str
    vessel_arrivals: int
    gross_tonnage_thousand: float


def load_port_activity(path: Path) -> List[PortActivityObservation]:
    observations: List[PortActivityObservation] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            observations.append(
                PortActivityObservation(
                    month=row["month"],
                    vessel_arrivals=int(row["vessel_arrivals"]),
                    gross_tonnage_thousand=float(row["gross_tonnage_thousand"]),
                )
            )
    return observations


def activity_summary(observations: List[PortActivityObservation]) -> Dict[str, float]:
    """Calculate a transparent activity-pressure proxy from the MPA series.

    Vessel arrivals are not waiting time and therefore are not labelled as a
    direct congestion measure. The index compares the latest observation with
    the median of the preceding 12 months.
    """
    if len(observations) < 13:
        raise ValueError("at least 13 monthly observations are required")
    latest = observations[-1]
    baseline = statistics.median(
        item.vessel_arrivals for item in observations[-13:-1]
    )
    prior_year = observations[-13]
    return {
        "latest_month": latest.month,
        "latest_vessel_arrivals": float(latest.vessel_arrivals),
        "latest_gross_tonnage_thousand": latest.gross_tonnage_thousand,
        "activity_pressure_index": latest.vessel_arrivals / baseline,
        "year_over_year_change": (
            latest.vessel_arrivals / prior_year.vessel_arrivals - 1.0
        ),
    }

