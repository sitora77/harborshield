# Singapore 2024: port delay, inventory and working capital

Version 0.4 · case reconstruction reviewed 4 October 2026

Public event context with **entirely constructed** order and option inputs. Not a company pilot, observed savings or a financing offer.

[Try the browser calculator](https://sitorastudio.com/case-study-en.html). The full document/signature lab runs in the local Streamlit app.

## Public facts and provenance

[MPA response on extended waiting times, 30 May 2024](https://www.mpa.gov.sg/media-centre/details/in-response-to-media-queries-on--vessels--extended-waiting-times-for-berths-in-the-port-of-singapore) · accessed 2026-10-04

- MPA linked off-schedule arrivals and vessel bunching to upstream disruptions and Cape of Good Hope diversions.
- Most container vessels berthed on arrival. Where schedule adjustment was infeasible, average waiting was about 2–3 days.
- January–April 2024 container throughput was 13.36 million TEU, up 8.8% year on year.
- Additional resources raised stated weekly handling capacity from 770,000 to 820,000 TEU.

This statement does not provide shipment-level arrival observations, a delay probability distribution, freight quotes or insurance rates.

[TradeTrust Singapore–India trade-finance transaction, 25 August 2023](https://www.tradetrust.io/happenings-and-resources/press-release-singapore-india-kick-off-interoperable-ebills-of-lading-for-trade-finance/) · accessed 2026-10-04

- The documented physical shipment was scrap metal from Miami to Gujarat.
- DBS, ICICI Bank, traders and Maersk participated in a paperless eBL and letter-of-credit workflow with documentary checks and title transfers.

HarborShield has no access to those transaction documents and no bank, TradeTrust or eBL title-transfer integration.

## Constructed decision

A Singapore replenishment order of 5,000 units costs US$150,000, with assumed sales of US$210,000. Own cash is US$25,000. A 30% supplier deposit is paid on day −7; the balance and logistics on day 0. Customer cash arrives 14 days after stock availability. Annual funding is assumed at 8%, not a lender quote. Existing stock covers 12 days and demand is assumed at 200 units/day.

| Assumed option | Availability day | Logistics | Stockout opportunity | Funding | Economic burden | Net economic contribution |
|---|---:|---:|---:|---:|---:|---:|
| Hypothetical priority service | 12.000 | US$5,200.00 | US$0.00 | US$772.65 | US$5,972.65 | US$54,027.35 |
| Hypothetical alternate-port + road | 12.125 | US$6,400.00 | US$300.00 | US$783.08 | US$7,483.08 | US$52,516.92 |
| Standard sea service | 14.500 | US$3,600.00 | US$6,000.00 | US$833.99 | US$10,433.99 | US$49,566.01 |

In these assumptions, the lowest burden changes from **Standard sea service** at zero added port delay to **Hypothetical priority service** at 2.5 days. This is a conditional model result, not evidence of actual service availability or achieved savings.

## Calculation and reconciliation

- Availability = transit + assumed port wait × option exposure + document-release time.
- Pre-arrival unmet units = min(order quantity, daily demand × max(availability − stock cover, 0)). Continuous demand approximation; lost demand is not backordered.
- Opportunity cost = unmet units × (unit sale price − unit purchase price). This is foregone contribution, not a cash payment. The eventually sold replenishment order still has its assumed full receipt.
- Cash ledger starts with own cash; supplier deposit, balance, logistics and customer receipt are then booked. Same-day flows are netted.
- Funding dollar-days = sum(max(−cash balance, 0) × days until next event). Funding interest = dollar-days × annual rate / 365, ending at customer collection.
- Economic burden = logistics + funding interest + stockout opportunity cost. Net economic contribution = planned order contribution − economic burden. It is not audited accounting profit.
- The closing cash ledger independently reconciles to own cash + sales − purchases − logistics, before interest. Opportunity cost never enters the cash ledger.

## Assumptions and exclusions

- The 140,000 USD external-funding limit, day-15 stock-availability deadline and zero minimum net contribution are constructed screening criteria, not confirmed credit or a contractual delivery commitment. Peak funding already deducts own cash. Null funding/deadline means not applied; zero is a binding limit. Cost ranking is retained even when no option is eligible.
- 2.5 days is a constructed affected-shipment scenario inspired by the reported 2–3-day wait; it is not the mean for all Singapore arrivals.
- 0 and 7 days are counterfactual sensitivity settings, not reported shipment observations.
- Every service option, freight amount, premium, interest rate, demand and document-release time is hypothetical. Priority capacity and alternate-port customs feasibility are unverified.
- The entire replenishment order is eventually sold, with one simplified receipt after availability plus the payment term. Existing-stock sales and other business cash flows are excluded.
- Pre-arrival unmet demand is lost rather than backordered. Its lost unit contribution is an opportunity cost, not a second cash payment or a reduction of this order's assumed sales receipt.
- Simple interest on negative incremental cash balance is calculated only until customer collection. No credit approval, taxes, FX, compound interest or future residual-debt repayment is modelled.
- This deterministic case is separate from the uncalibrated v0.2 stochastic insurance model; no daily-delay charge is added again.

## Deterministic sensitivity

27 combinations of port delay (0 / 2.5 / 7 days), annual funding (3 / 8 / 15%) and stock cover (8 / 12 / 18 days). These are constructed settings, not a calibrated probability distribution. Full results are in `reports/case_study.json`.

## Feasibility before recommendation

Cost ranking remains visible. Only options meeting the assumed external-funding limit, latest stock-availability day and minimum net economic contribution are eligible. Peak funding already deducts own cash. Null funding/deadline means not applied; zero is binding. When no option is eligible, no recommendation is made.

At 2.5 days of assumed port wait, US$129,000 and day 15 select standard sea; tightening the deadline to day 12 leaves no eligible option. US$130,200 and day 12 admit the priority option exactly on both boundaries. These are assumed screening examples, not confirmed credit or delivery commitments. Four examples with full option-level reasons are exported in the JSON report.

## Document checks and signatures

The local app generates a document bundle from the current constructed order, including the same case inputs, their SHA-256 digest and the screening decision. Only the selected, consistency-checked DEMO bundle is signed; invalid uploads block signing rather than substituting a default order. Uploaded context fields are not certified by the consistency rules, input digest or signature.

Supported input is structured JSON, not arbitrary scans/PDFs. Rules check IDs, currency, SKU quantities, invoice arithmetic, declared cargo value, the explicitly supplied insured-value multiplier and requested cover dates. Register-based duplicate invoice warnings are not fraud findings.

Eight deliberately seeded fixtures match their expected consistency outcomes. They demonstrate rule implementation, not real-world detection accuracy. Signature tests distinguish (1) an unchanged signature, (2) a changed amount, and (3) a valid replacement-key signature that fails the separately supplied issuer-key anchor.

Ed25519 uses the cryptography library, not hand-written cryptographic primitives. The envelope and sorted JSON encoding are project-local, not TradeTrust/W3C/RFC 8785. Private keys exist only in memory. A matching demo-key anchor is not a real-world identity certificate. Signature validity does not prove the shipment, insurance coverage, creditworthiness, unique financing or legal title.

## Reproduce

```bash
python scripts/run_case_study.py
node scripts/test_case_calculator.cjs
python -m unittest discover -s tests -v
```

Browser and Python calculations are cross-checked on 27 sensitivity combinations, four constraint examples, no-eligible decisions, zero-rate, zero-demand and ample-own-cash boundaries. Both presentation languages share one template and calculator; switching language preserves inputs. The browser calculator is executable locally and on GitHub Pages. The uploaded-document and signing lab requires local Streamlit; the website's document table is a static test snapshot.

## Application relevance

SCM: replenishment, service level, disruption response and inventory/transport trade-offs. FinTech: structured trade-data integrity, signatures and issuer-key trust boundaries. Finance/business: cash timing, funding needs, contribution and assumptions-based sensitivity. Maritime/ISE/ITS: connects the existing risk-allocation research with a business decision. This is not a credit-scoring or asset-pricing project.

AI-assisted implementation is disclosed. No confidential company material or paid scraping service was used.
