#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild the public-event case report and the browser calculator from fixtures."""
import copy
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harborshield.business_case import case_report, load_case
from harborshield.case_documents import documents_from_case
from harborshield.trade_documents import (check_documents, new_demo_key, parse_json_bytes,
                                        public_key_text, sign_document, verify_document)


def document_evidence(bundle):
    mutations = [("Original constructed bundle", copy.deepcopy(bundle), True)]
    for label, document, key, value in [
        ("Invoice total altered", "invoice", "total_value", 150001),
        ("Different order identifier", "packing_list", "order_id", "OTHER"),
        ("Currency mismatch", "packing_list", "currency", "SGD"),
        ("Requested value inconsistent with multiplier", "insurance_application", "requested_insured_value", 150000),
        ("Departure outside requested window", "invoice", "departure_date", "2024-07-01"),
    ]:
        altered = copy.deepcopy(bundle)
        altered[document][key] = value
        mutations.append((label, altered, False))
    altered = copy.deepcopy(bundle)
    altered["packing_list"]["items"][0]["quantity"] = 4999
    mutations.append(("Packing quantity mismatch", altered, False))
    altered = copy.deepcopy(bundle)
    del altered["invoice"]["items"][0]["unit_price"]
    mutations.append(("Missing unit price", altered, False))
    checks = []
    for name, candidate, expected in mutations:
        result = check_documents(candidate)
        checks.append({"test_case": name, "expected_consistent": expected,
                       "observed_consistent": result["consistent"],
                       "matches_fixture_expectation": result["consistent"] == expected,
                       "issue_codes": [issue["code"] for issue in result["issues"]]})
    key = new_demo_key()
    original = sign_document(bundle, key)
    tampered = copy.deepcopy(original)
    tampered["payload"]["invoice"]["total_value"] += 1
    # Store verification outcomes only. Random keys/signatures never enter reproducible output.
    signatures = [{"test_case": label, **verify_document(candidate, public_key_text(key))}
                  for label, candidate in [("Original", original), ("Amount tampered", tampered),
                                           ("Re-signed with replacement key", sign_document(bundle, new_demo_key()))]]
    return {"scope": "8 deliberately constructed fixtures, not a real-document accuracy benchmark",
            "consistency_fixtures": checks, "signature_demonstration": signatures}


def money(value):
    return f"US${value:,.2f}"


def build_markdown(report):
    inputs = report["inputs"]
    lines = ["# Singapore 2024: port delay, inventory and working capital", "",
             "Version 0.4 · case reconstruction reviewed 4 October 2026", "",
             "Public event context with **entirely constructed** order and option inputs. Not a company pilot, observed savings or a financing offer.", "",
             "[Try the browser calculator](https://sitorastudio.com/case-study-en.html). The full document/signature lab runs in the local Streamlit app.", "",
             "## Public facts and provenance", ""]
    for source in inputs["sources"]:
        lines.append(f"[{source['title']}]({source['url']}) · accessed {source['accessed']}")
        lines.extend(["", *[f"- {fact}" for fact in source["facts"]], "", source["not_supported"], ""])
    lines.extend(["## Constructed decision", "",
                  "A Singapore replenishment order of 5,000 units costs US$150,000, with assumed sales of US$210,000. Own cash is US$25,000. A 30% supplier deposit is paid on day −7; the balance and logistics on day 0. Customer cash arrives 14 days after stock availability. Annual funding is assumed at 8%, not a lender quote. Existing stock covers 12 days and demand is assumed at 200 units/day.", "",
                  "| Assumed option | Availability day | Logistics | Stockout opportunity | Funding | Economic burden | Net economic contribution |",
                  "|---|---:|---:|---:|---:|---:|---:|"])
    for row in report["selected_comparison"]:
        lines.append(f"| {row['option']} | {row['availability_day']:.3f} | {money(row['logistics_cost'])} | {money(row['stockout_opportunity_cost'])} | {money(row['funding_cost'])} | {money(row['economic_burden'])} | {money(row['net_economic_contribution'])} |")
    normal = report["no_port_delay_comparison"][0]
    best = report["selected_comparison"][0]
    lines.extend(["", f"In these assumptions, the lowest burden changes from **{normal['option']}** at zero added port delay to **{best['option']}** at 2.5 days. This is a conditional model result, not evidence of actual service availability or achieved savings.", "",
                  "## Calculation and reconciliation", "",
                  "- Availability = transit + assumed port wait × option exposure + document-release time.",
                  "- Pre-arrival unmet units = min(order quantity, daily demand × max(availability − stock cover, 0)). Continuous demand approximation; lost demand is not backordered.",
                  "- Opportunity cost = unmet units × (unit sale price − unit purchase price). This is foregone contribution, not a cash payment. The eventually sold replenishment order still has its assumed full receipt.",
                  "- Cash ledger starts with own cash; supplier deposit, balance, logistics and customer receipt are then booked. Same-day flows are netted.",
                  "- Funding dollar-days = sum(max(−cash balance, 0) × days until next event). Funding interest = dollar-days × annual rate / 365, ending at customer collection.",
                  "- Economic burden = logistics + funding interest + stockout opportunity cost. Net economic contribution = planned order contribution − economic burden. It is not audited accounting profit.",
                  "- The closing cash ledger independently reconciles to own cash + sales − purchases − logistics, before interest. Opportunity cost never enters the cash ledger.", "",
                  "## Assumptions and exclusions", ""])
    lines.extend(f"- {assumption}" for assumption in inputs["assumptions"])
    lines.extend(["", "## Deterministic sensitivity", "",
                  "27 combinations of port delay (0 / 2.5 / 7 days), annual funding (3 / 8 / 15%) and stock cover (8 / 12 / 18 days). These are constructed settings, not a calibrated probability distribution. Full results are in `reports/case_study.json`.", "",
                  "## Feasibility before recommendation", "",
                  "Cost ranking remains visible. Only options meeting the assumed external-funding limit, latest stock-availability day and minimum net economic contribution are eligible. Peak funding already deducts own cash. Null funding/deadline means not applied; zero is binding. When no option is eligible, no recommendation is made.", "",
                  "At 2.5 days of assumed port wait, US$129,000 and day 15 select standard sea; tightening the deadline to day 12 leaves no eligible option. US$130,200 and day 12 admit the priority option exactly on both boundaries. These are assumed screening examples, not confirmed credit or delivery commitments. Four examples with full option-level reasons are exported in the JSON report.", "",
                  "## Document checks and signatures", "",
                  "The local app generates a document bundle from the current constructed order, including the same case inputs, their SHA-256 digest and the screening decision. Only the selected, consistency-checked DEMO bundle is signed; invalid uploads block signing rather than substituting a default order. Uploaded context fields are not certified by the consistency rules, input digest or signature.", "",
                  "Supported input is structured JSON, not arbitrary scans/PDFs. Rules check IDs, currency, SKU quantities, invoice arithmetic, declared cargo value, the explicitly supplied insured-value multiplier and requested cover dates. Register-based duplicate invoice warnings are not fraud findings.", "",
                  "Eight deliberately seeded fixtures match their expected consistency outcomes. They demonstrate rule implementation, not real-world detection accuracy. Signature tests distinguish (1) an unchanged signature, (2) a changed amount, and (3) a valid replacement-key signature that fails the separately supplied issuer-key anchor.", "",
                  "Ed25519 uses the cryptography library, not hand-written cryptographic primitives. The envelope and sorted JSON encoding are project-local, not TradeTrust/W3C/RFC 8785. Private keys exist only in memory. A matching demo-key anchor is not a real-world identity certificate. Signature validity does not prove the shipment, insurance coverage, creditworthiness, unique financing or legal title.", "",
                  "## Reproduce", "", "```bash", "python scripts/run_case_study.py", "node scripts/test_case_calculator.cjs", "python -m unittest discover -s tests -v", "```", "",
                  "Browser and Python calculations are cross-checked on 27 sensitivity combinations, four constraint examples, no-eligible decisions, zero-rate, zero-demand and ample-own-cash boundaries. Both presentation languages share one template and calculator; switching language preserves inputs. The browser calculator is executable locally and on GitHub Pages. The uploaded-document and signing lab requires local Streamlit; the website's document table is a static test snapshot.", "",
                  "## Application relevance", "",
                  "SCM: replenishment, service level, disruption response and inventory/transport trade-offs. FinTech: structured trade-data integrity, signatures and issuer-key trust boundaries. Finance/business: cash timing, funding needs, contribution and assumptions-based sensitivity. Maritime/ISE/ITS: connects the existing risk-allocation research with a business decision. This is not a credit-scoring or asset-pricing project.", "",
                  "AI-assisted implementation is disclosed. No confidential company material or paid scraping service was used.", ""])
    return "\n".join(lines)


def build_html(report, language="zh"):
    from harborshield.case_page import build_page
    return build_page(report, ROOT, language)


def main():
    report = case_report(load_case(ROOT / "data/cases/singapore_2024.json"))
    bundle = documents_from_case(report["inputs"])
    report["document_evidence"] = document_evidence(bundle)
    target = ROOT / "reports"
    target.mkdir(exist_ok=True)
    (target / "case_study.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (target / "case-study.html").write_text(build_html(report), encoding="utf-8")
    (target / "case-study-en.html").write_text(build_html(report, "en"), encoding="utf-8")
    (ROOT / "docs/CASE_STUDY.md").write_text(build_markdown(report), encoding="utf-8")
    for name in ("case-calculator.js", "case-page.js", "case-study.css"):
        shutil.copyfile(ROOT / "web" / name, target / name)
    (target / "demo_documents.json").write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Built v0.4 bilingual case: {len(report['sensitivity'])} sensitivity settings, 8 constructed document fixtures")


if __name__ == "__main__":
    main()
