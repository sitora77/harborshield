"""Refresh the bundled MPA monthly vessel-arrivals snapshot."""

import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path


DATASET_ID = "d_d48c5a038904f6da3c603cd854b6c191"
API_URL = "https://data.gov.sg/api/action/datastore_search"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "mpa_vessel_arrivals_monthly.csv"


def main() -> None:
    query = urllib.parse.urlencode({"resource_id": DATASET_ID, "limit": 1000})
    with urllib.request.urlopen(f"{API_URL}?{query}", timeout=30) as response:
        payload = json.load(response)
    records = payload["result"]["records"]
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["month", "vessel_arrivals", "gross_tonnage_thousand"])
        for row in records:
            writer.writerow([row["month"], row["number_of_vessels"], row["gross_tonnage"]])
    print(f"Wrote {len(records)} observations to {OUTPUT}")


if __name__ == "__main__":
    main()

