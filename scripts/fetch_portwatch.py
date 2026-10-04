#!/usr/bin/env python3
"""Fetch only Singapore daily calls, 2022–2024, preserving original API pages."""
from datetime import datetime, timezone
import argparse
import hashlib
from http.client import HTTPException
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harborshield.portwatch import ATTRIBUTION, ENDPOINT, SOURCE, TERMS, validate_records


def request(parameters, transport="urllib"):
    url = ENDPOINT + "?" + urlencode({"f": "json", **parameters})
    if transport == "curl":
        raw = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--retry", "2",
                              "--retry-all-errors", "--retry-delay", "1", "--max-time", "20", url],
                             check=True, stdout=subprocess.PIPE, timeout=70).stdout
        payload = json.loads(raw)
        if "error" in payload:
            raise RuntimeError(f"Source API error: {payload['error']}")
        return raw, payload, url
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": "HarborShield-academic-prototype/0.5"}), timeout=20) as response:
                raw = response.read()
            break
        except (OSError, HTTPException) as error:
            if attempt == 2:
                raise
            print(f"Transient source connection error ({type(error).__name__}); retry {attempt + 1}/2")
            time.sleep(attempt + 1)
    payload = json.loads(raw)
    if "error" in payload:
        raise RuntimeError(f"Source API error: {payload['error']}")
    return raw, payload, url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=("urllib", "curl"), default="urllib",
                        help="curl is an optional transport for connections with truncated urllib responses")
    transport = parser.parse_args().transport
    start, end = "2022-01-01", "2024-12-31"
    where = f"portid = 'port1201' AND date >= DATE '{start}' AND date <= DATE '{end}'"
    _, count_response, count_url = request({"where": where, "returnCountOnly": "true"}, transport)
    count = count_response["count"]
    if type(count) is not int or count != 1096:
        raise RuntimeError(f"Expected 1,096 days; source returned {count}. Investigate, do not fill gaps.")
    destination = ROOT / "data/portwatch"
    destination.mkdir(parents=True, exist_ok=True)
    # Publish the snapshot only after all pages, scope and date completeness pass.
    with tempfile.TemporaryDirectory(prefix="portwatch-") as staging_path:
        staging = Path(staging_path)
        (staging / "raw").mkdir()
        records, pages = [], []
        for offset in range(0, count, 500):
            raw, page, url = request({"where": where, "outFields": "date,portid,portname,portcalls_container,portcalls",
                                      "orderByFields": "date ASC,ObjectId ASC", "resultOffset": offset,
                                      "resultRecordCount": 500, "returnGeometry": "false"}, transport)
            features = page["features"]
            if len(features) != min(500, count - offset):
                raise RuntimeError("Unexpected pagination size; source may have changed")
            filename = f"raw/page-{offset:04d}.json"
            (staging / filename).write_bytes(raw)
            pages.append({"file": filename, "offset": offset, "rows": len(features),
                          "sha256": hashlib.sha256(raw).hexdigest(), "query_url": url})
            records.extend(feature["attributes"] for feature in features)
        if records != validate_records(records, start, end):
            raise RuntimeError("API page order is not chronological")
        content = (json.dumps(records, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        (staging / "singapore_daily.json").write_bytes(content)
        metadata = {"publisher": "IMF PortWatch; source AIS via UN Global Platform",
                    "dataset": SOURCE, "endpoint": ENDPOINT, "attribution": ATTRIBUTION, "terms": TERMS,
                    "scope": "Singapore port1201 only; not all Singapore-area port boundaries",
                    "start": start, "end": end, "source_count": count, "count_query_url": count_url,
                    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "snapshot_sha256": hashlib.sha256(content).hexdigest(), "raw_pages": pages,
                    "transformations": "Select five named fields and one port/date window; preserve all attribute values. "
                                       "Format canonical JSON; untouched response bytes also retained.",
                    "unit": "portcalls_container: container-ship calls per UTC day. portcalls: all tracked ship-type calls.",
                    "revision_note": "Later retrieval of historical data, not archived contemporaneous data vintages."}
        (staging / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        (destination / "raw").mkdir(exist_ok=True)
        for path in staging.rglob("*.json"):
            (destination / path.relative_to(staging)).write_bytes(path.read_bytes())
    print(f"Fetched and validated {count:,} real daily records; snapshot SHA-256 {metadata['snapshot_sha256']}")


if __name__ == "__main__":
    main()
