"""Streamlit views for public-event economics and structured document demonstrations."""
import copy
import json

import pandas as pd
import plotly.express as px
import streamlit as st

from .business_case import compare_options, decision_summary, load_case
from .case_documents import documents_from_case
from .trade_documents import (check_documents, new_demo_key, parse_json_bytes,
                              public_key_text, sign_document, verify_document)


def render_business_case(root):
    case = load_case(root / "data/cases/singapore_2024.json")
    st.subheader("Singapore 2024 · replenishment and working capital")
    st.caption("Historical public event, constructed USD order. These inputs are independent of the route-simulation sidebar.")
    source = case["sources"][0]
    st.markdown(f"[MPA, 30 May 2024]({source['url']}): most container ships berthed on arrival; where schedule adjustment was infeasible, average waiting was about 2–3 days.")
    st.warning("All order details, service options, quotes, premiums and funding rates below are constructed. 2.5 days is an affected-order assumption, not a fitted port-delay distribution.")
    a, b, c = st.columns(3)
    delay = a.slider("Case port-delay assumption (days)", 0.0, 14.0, 2.5, step=0.5)
    stock = b.slider("Case stock cover (days)", 0.0, 30.0, 12.0, step=0.5)
    rate = c.slider("Case annual funding assumption (%)", 0.0, 30.0, 8.0, step=0.5) / 100
    a, b, c = st.columns(3)
    demand = a.number_input("Case daily demand (units)", min_value=0, max_value=10000, value=200, step=50)
    payment = b.slider("Case customer payment after availability (days)", 0, 90, 14)
    cash = c.number_input("Case own cash available (USD)", min_value=0, max_value=500000, value=25000, step=5000)
    a, b, c = st.columns(3)
    limit = a.number_input("Assumed external funding limit (USD)", min_value=0, max_value=1000000, value=140000, step=1000)
    deadline = b.number_input("Latest stock-availability day", min_value=0.0, max_value=365.0, value=15.0, step=0.5)
    minimum = c.number_input("Minimum net economic contribution (USD)", min_value=0, max_value=1000000, value=0, step=1000)
    st.caption("Constructed screening criteria, not approved credit or a delivery commitment. Funding need already deducts own cash; zero is a binding limit.")
    case["order"].update(stock_cover_days=stock, annual_funding_rate=rate,
                         daily_demand=demand, customer_payment_days=payment, initial_cash=cash)
    case["selected_port_delay_days"] = delay
    case["constraints"] = {"funding_limit": limit, "latest_availability_day": deadline,
                           "minimum_net_contribution": minimum}
    st.session_state["current_business_case"] = copy.deepcopy(case)
    rows = compare_options(case)
    st.session_state["case_comparison"] = rows
    decision = decision_summary(rows)
    st.session_state["case_decision"] = decision
    best = next((row for row in rows if row["option_id"] == decision["recommended_option_id"]), None)
    if best is None:
        st.error("No eligible option meets all assumed funding, availability and contribution criteria. No recommendation is made.")
    else:
        a, b, c = st.columns(3)
        a.metric("Lowest burden among eligible options", best["option"])
        b.metric("Availability from departure", f"{best['availability_day']:.2f} days")
        c.metric("Peak funding need", f"US${best['peak_funding_need']:,.0f}")
    st.caption(f"Unconstrained cost minimum (not a recommendation): {rows[0]['option']}.")
    columns = ["option", "availability_day", "stockout_opportunity_cost", "logistics_cost",
               "funding_cost", "economic_burden", "net_economic_contribution"]
    frame = pd.DataFrame(rows)[columns]
    display = frame.copy()
    for column in columns[2:]:
        display[column] = display[column].map(lambda value: f"US${value:,.2f}")
    display.columns = ["Constructed option", "Available day", "Stockout opportunity", "Logistics",
                       "Funding interest", "Economic burden", "Net economic contribution"]
    st.dataframe(display, hide_index=True, width="stretch")
    st.dataframe(pd.DataFrame([{"Option": r["option"], "Eligible under assumptions": r["eligible"],
                                "Reasons": ", ".join(r["ineligibility_reasons"]) or "Meets all criteria"} for r in rows]),
                 hide_index=True, width="stretch")
    st.caption("Economic burden = logistics + funding interest + foregone pre-arrival contribution. The opportunity cost is not a cash outflow. No separate daily-delay charge is added.")
    selected = st.selectbox("Inspect case cash-flow ledger", [row["option"] for row in rows])
    row = next(row for row in rows if row["option"] == selected)
    ledger = pd.DataFrame(row["events"])
    chart = px.line(ledger, x="day", y="cash_balance", markers=True,
                    labels={"day": "Days from departure", "cash_balance": "Incremental cash including own funds (USD)"},
                    title="Event ledger · negative balances imply funding need")
    chart.update_traces(line_shape="hv")
    chart.add_hline(y=0, line_dash="dot")
    st.plotly_chart(chart)
    st.dataframe(ledger, hide_index=True, width="stretch")
    st.caption(f"Negative-balance area: {row['funding_dollar_days']:,.0f} USD-days. Interest = area × annual rate / 365. Events on the same day are netted; interest is not capitalised. Calculation stops at collection.")
    if row["residual_funding_need"] > 0:
        st.warning("Principal remains unpaid after collection; future funding cost is outside this model.")
    baseline = decision_summary(compare_options(case, 0))
    st.write(f"With no added port wait under the same criteria: {baseline['recommended_option_id'] or 'no eligible option'}.")
    with st.expander("All assumptions and full constructed input"):
        st.write("5,000 units · purchase US$30/unit · sales US$42/unit · 30% supplier deposit on day −7 · balance and logistics on departure.")
        for assumption in case["assumptions"]:
            st.write(assumption)
        st.json(case)
    st.download_button("Download current constructed case (JSON)", json.dumps(case, indent=2, ensure_ascii=False),
                       "harborshield_case_inputs.json", "application/json")
    st.download_button("Download current case comparison (CSV)", frame.to_csv(index=False),
                       "harborshield_case_comparison.csv", "text/csv")


def render_document_lab(root):
    current_case = st.session_state.get("current_business_case")
    demo = documents_from_case(current_case) if current_case else parse_json_bytes((root / "data/cases/demo_documents.json").read_bytes())
    st.subheader("Trade documents · consistency and tamper detection")
    st.caption("Structured JSON only, not OCR or PDF extraction. No uploads are sent to third-party services or saved by this application.")
    st.markdown("Inspired by the [2023 TradeTrust transaction](https://www.tradetrust.io/happenings-and-resources/press-release-singapore-india-kick-off-interoperable-ebills-of-lading-for-trade-finance/) involving DBS, ICICI and Maersk. Its physical shipment was **Miami → Gujarat**. This project is not connected to that transaction or to TradeTrust.")
    st.caption("The default bundle is generated from the current business-case order, including its inputs digest and screening decision. Changing funding assumptions changes the signed context, not the invoice amount. Uploaded bundles are checked and signed as separate DEMO inputs, never treated as issuer-approved.")
    st.download_button("Download constructed document bundle", json.dumps(demo, indent=2),
                       "harborshield_demo_documents.json", "application/json")
    upload = st.file_uploader("Check your structured document bundle (JSON, max 200 KB)", type=["json"])
    bundle = demo
    checked = None
    try:
        if upload is not None:
            bundle = parse_json_bytes(upload.getvalue())
        checked = check_documents(bundle)
        st.session_state["document_checks"] = checked
        if checked["consistent"]:
            st.success("Supported document-consistency checks pass. This does not verify the underlying trade.")
        else:
            st.error("Document checks found missing or inconsistent fields.")
            st.dataframe(pd.DataFrame(checked["issues"]), hide_index=True, width="stretch")
    except ValueError as exc:
        st.session_state["document_checks"] = {"consistent": False, "issues": [{"message": str(exc)}]}
        st.error(str(exc))
    with st.expander("Supported fields and rules"):
        st.write("Order IDs, currencies, unique document IDs, SKU quantities, invoice arithmetic, declared cargo value, explicit insured-value multiplier, and departure within the requested cover window. Duplicate invoice checking is available through the Python API when a comparison register is supplied.")
        st.json(demo)
    st.divider()
    st.markdown("#### Sign the checked DEMO bundle")
    st.warning("This is a project-local Ed25519 envelope, not a TradeTrust credential or legal eBL. A valid signature detects changes relative to a key; it does not prove cargo, policy coverage or an issuer's real-world identity.")
    if "document_demo_key" not in st.session_state:
        st.session_state["document_demo_key"] = new_demo_key()
    key = st.session_state["document_demo_key"]
    anchor = public_key_text(key)
    if checked is None or not checked["consistent"]:
        st.session_state.pop("signed_demo_payload", None)
        st.session_state["signature_demo_result"] = {"accepted_demo_signature": False, "status": "blocked_inconsistent_bundle"}
        st.warning("Signing is blocked: fix the selected bundle first. No default bundle is substituted for an invalid upload.")
        return
    original = sign_document(bundle, key)
    st.session_state["signed_demo_payload"] = copy.deepcopy(bundle)
    st.caption(f"Signing source: {'uploaded structured JSON (DEMO only)' if upload is not None else 'current constructed business-case order'} · order {bundle['invoice']['order_id']}")
    mode = st.selectbox("Signature test case", ["Original signed demo", "Amount altered after signing", "Replacement-key re-signing"])
    candidate = copy.deepcopy(original)
    if mode == "Amount altered after signing":
        candidate["payload"]["invoice"]["total_value"] = float(candidate["payload"]["invoice"]["total_value"]) + 1
    elif mode == "Replacement-key re-signing":
        candidate = sign_document(bundle, new_demo_key())
    result = verify_document(candidate, anchor)
    st.session_state["signature_demo_result"] = result
    st.json(result)
    st.caption("The anchor is established separately from the envelope. A replacement key can make a mathematically valid signature, but fails the original demo-key anchor check. All keys are temporary, local teaching keys; no private key is exported.")
    st.download_button("Download original signed DEMO envelope", json.dumps(original, indent=2),
                       "harborshield_signed_demo.json", "application/json")
    st.download_button("Download separate DEMO public-key anchor", anchor,
                       "harborshield_demo_public_key.txt", "text/plain")
    signed_upload = st.file_uploader("Verify a saved DEMO envelope (JSON)", type=["json"], key="signed_envelope")
    expected = st.text_input("Previously obtained public-key anchor (base64)", value="",
                             help="Supply the independently obtained anchor, not a key copied from an untrusted envelope.")
    if signed_upload is not None:
        try:
            st.json(verify_document(parse_json_bytes(signed_upload.getvalue()), expected.strip() or None))
        except ValueError as exc:
            st.error(str(exc))
