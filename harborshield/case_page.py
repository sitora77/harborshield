"""Render two presentation languages from one template and one calculation."""
import hashlib
from html import escape
import json
import re


def build_page(report, root, language="zh"):
    copies = json.loads((root / "web/case-copy.json").read_text(encoding="utf-8"))
    text = copies[language]
    context = {key: escape(value, quote=True) for key, value in text.items() if isinstance(value, str)}
    inputs = report["inputs"]
    rows = report["selected_comparison"]
    selected_id = report["selected_decision"]["recommended_option_id"]
    best = next((r for r in rows if r["option_id"] == selected_id), None)
    money = lambda value: f"US${value:,.2f}"
    name = lambda r: text["option_names"].get(r["option_id"], r["option"])
    def table_row(values):
        return "<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in values) + "</tr>"
    context.update(default_option=escape(name(best) if best else text["no_eligible"]),
                   default_burden=money(best["economic_burden"]) if best else "—",
                   default_funding=money(best["peak_funding_need"]) if best else "—")
    context["valid_notice"] = escape(text["valid_notice"] if best else text["none_notice"])
    for i, label in enumerate(text["metrics"]):
        context[f"metric_{i}"] = escape(label)
    fields = [("delay", 0, 14, .5, inputs["selected_port_delay_days"], True),
              ("stock", 0, 30, .5, inputs["order"]["stock_cover_days"], True),
              ("rate", 0, 30, .5, inputs["order"]["annual_funding_rate"] * 100, True),
              ("cash", 0, 500000, 5000, inputs["order"]["initial_cash"], True),
              ("demand", 0, 10000, 50, inputs["order"]["daily_demand"], True),
              ("payment", 0, 90, 1, inputs["order"]["customer_payment_days"], True),
              ("funding", 0, 1000000, 100, inputs["constraints"].get("funding_limit"), False),
              ("deadline", 0, 365, .5, inputs["constraints"].get("latest_availability_day"), False),
              ("minimum", 0, 1000000, 100, inputs["constraints"].get("minimum_net_contribution", 0), True)]
    context["input_fields"] = "".join(f'<label for="{id_}">{escape(label)}<input id="{id_}" type="number" min="{minimum}" max="{maximum}" step="{step}" value="{value if value is not None else ""}" {"required" if required else ""}></label>'
                                        for label, (id_, minimum, maximum, step, value, required) in zip(text["labels"], fields))
    for key in ("comparison_headers", "ledger_headers", "document_headers", "signature_headers"):
        context[key] = "".join(f"<th>{escape(label)}</th>" for label in text[key])
    context["comparison_rows"] = "".join(table_row([name(r), f"{r['availability_day']:.2f}", money(r["logistics_cost"]),
                money(r["stockout_opportunity_cost"]), money(r["funding_cost"]), money(r["economic_burden"]),
                money(r["net_economic_contribution"]), text["eligible"] if r["eligible"] else "; ".join(text["reasons"][code] for code in r["ineligibility_reasons"])]) for r in rows)
    context["document_rows"] = "".join(table_row([text["test_names"][r["test_case"]], str(r["expected_consistent"]).lower(),
                str(r["observed_consistent"]).lower(), ", ".join(r["issue_codes"]) or text["no_discrepancies"]]) for r in report["document_evidence"]["consistency_fixtures"])
    context["signature_rows"] = "".join(table_row([text["test_names"][r["test_case"]], str(r["signature_valid"]).lower(),
                str(r["issuer_key_matches_anchor"]).lower(), str(r["document_truth_verified"]).lower()]) for r in report["document_evidence"]["signature_demonstration"])
    context["sources"] = "".join(f'<div class="source"><a href="{escape(s["url"], quote=True)}">{escape(s["title"])}</a><p>{escape(" ".join(s["facts"]))}</p><p class="note">{escape(s["not_supported"])} · {s["accessed"]}</p></div>' for s in inputs["sources"])
    context["assumptions"] = "".join(f"<li>{escape(a)}</li>" for a in inputs["assumptions"])
    for key, data in (("inputs_json", inputs), ("locale_json", text)):
        context[key] = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    for key, name_ in (("css_version", "case-study.css"), ("calculator_version", "case-calculator.js"), ("page_version", "case-page.js")):
        context[key] = hashlib.sha256((root / "web" / name_).read_bytes()).hexdigest()[:12]
    template = (root / "web/case-study.template.html").read_text(encoding="utf-8")
    return re.sub(r"@@([a-z0-9_]+)@@", lambda match: context[match.group(1)], template)
