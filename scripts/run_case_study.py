#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild the public-event case report and the browser calculator from fixtures."""
import copy
from html import escape
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harborshield.business_case import case_report, load_case
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
             "Version 0.3 · case reconstruction reviewed 4 October 2026", "",
             "Public event context with **entirely constructed** order and option inputs. Not a company pilot, observed savings or a financing offer.", "",
             "[Try the browser calculator](https://sitorastudio.com/case-study.html). The full document/signature lab runs in the local Streamlit app.", "",
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
                  "## Document checks and signatures", "",
                  "Supported input is structured JSON, not arbitrary scans/PDFs. Rules check IDs, currency, SKU quantities, invoice arithmetic, declared cargo value, the explicitly supplied insured-value multiplier and requested cover dates. Register-based duplicate invoice warnings are not fraud findings.", "",
                  "Eight deliberately seeded fixtures match their expected consistency outcomes. They demonstrate rule implementation, not real-world detection accuracy. Signature tests distinguish (1) an unchanged signature, (2) a changed amount, and (3) a valid replacement-key signature that fails the separately supplied issuer-key anchor.", "",
                  "Ed25519 uses the cryptography library, not hand-written cryptographic primitives. The envelope and sorted JSON encoding are project-local, not TradeTrust/W3C/RFC 8785. Private keys exist only in memory. A matching demo-key anchor is not a real-world identity certificate. Signature validity does not prove the shipment, insurance coverage, creditworthiness, unique financing or legal title.", "",
                  "## Reproduce", "", "```bash", "python scripts/run_case_study.py", "node scripts/test_case_calculator.cjs", "python -m unittest discover -s tests -v", "```", "",
                  "Browser and Python calculations are cross-checked on 27 sensitivity combinations plus zero-rate, zero-demand and ample-own-cash boundaries. The browser calculator is executable locally and on GitHub Pages. The uploaded-document and signing lab requires local Streamlit; the website's document table is a static test snapshot.", "",
                  "## Application relevance", "",
                  "SCM: replenishment, service level, disruption response and inventory/transport trade-offs. FinTech: structured trade-data integrity, signatures and issuer-key trust boundaries. Finance/business: cash timing, funding needs, contribution and assumptions-based sensitivity. Maritime/ISE/ITS: connects the existing risk-allocation research with a business decision. This is not a credit-scoring or asset-pricing project.", "",
                  "AI-assisted implementation is disclosed. No confidential company material or paid scraping service was used.", ""])
    return "\n".join(lines)


def build_html(report):
    c = report["inputs"]
    rows = report["selected_comparison"]
    tr = "".join("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in
         [r["option"], f"{r['availability_day']:.2f}", money(r["logistics_cost"]),
          money(r["stockout_opportunity_cost"]), money(r["funding_cost"]), money(r["economic_burden"]), money(r["net_economic_contribution"])]) + "</tr>" for r in rows)
    sources = "".join(f'<div class="source"><a href="{escape(s["url"], quote=True)}">{escape(s["title"])}</a><p>{escape(" ".join(s["facts"]))}</p><p class="note">{escape(s["not_supported"])} Reviewed {s["accessed"]}.</p></div>' for s in c["sources"])
    assumptions = "".join(f"<li>{escape(a)}</li>" for a in c["assumptions"])
    doc_rows = "".join(f'<tr><td>{escape(r["test_case"])}</td><td>{str(r["expected_consistent"]).lower()}</td><td>{str(r["observed_consistent"]).lower()}</td><td>{escape(", ".join(r["issue_codes"]) or "No rule discrepancies")}</td></tr>' for r in report["document_evidence"]["consistency_fixtures"])
    sig_rows = "".join(f'<tr><td>{escape(r["test_case"])}</td><td>{str(r["signature_valid"]).lower()}</td><td>{str(r["issuer_key_matches_anchor"]).lower()}</td><td>{str(r["document_truth_verified"]).lower()}</td></tr>' for r in report["document_evidence"]["signature_demonstration"])
    inputs = json.dumps(c, ensure_ascii=False).replace("<", "\\u003c")
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>HarborShield · 真实事件与订单现金流案例</title><meta name="description" content="Singapore 2024 port delay, constructed order economics and trade-document integrity. An interactive, assumption-led HarborShield case study."><link rel="stylesheet" href="case-study.css"></head>
<body><main><nav><a href="https://sitorastudio.com/">Sitora Studio</a><div><a href="https://sitorastudio.com/experiment.html">v0.2 风险实验</a> · <a href="https://github.com/sitora77/harborshield">GitHub 源码</a></div></nav>
<header><p class="eyebrow">HARBORSHIELD / v0.3 / PUBLIC-EVENT CASE</p><h1>港口延误，如何影响<br>一笔订单的现金流？</h1><p class="subtitle">Singapore 2024 · replenishment, working capital and trade-document integrity</p><p>从公开港口事件出发，比较“省运费”“避免缺货”“减少资金占用”之间的取舍。调整下面的假设，结果会在你的浏览器中重新计算。</p></header>
<div class="boundary">真实的是公开事件；订单、运费、保费、利率及备选服务均为构造示例。这里没有真实客户交易、企业部署、银行授信或实际节省金额。</div>
<section class="panel"><p class="tag">01 / INTERACTIVE BUSINESS CASE</p><h2>先选假设，再比较方案</h2><p class="note">模拟订单：5,000 件，采购 US$30/件，销售 US$42/件。发运前 7 天支付 30% 订金，发运当天支付尾款及物流费。其余固定输入可在下载文件中查看。</p>
<div class="inputs"><label for="delay">额外港口等待（天）<input id="delay" type="number" min="0" max="14" step="0.5" value="2.5" required></label><label for="stock">现有库存覆盖（天）<input id="stock" type="number" min="0" max="30" step="0.5" value="12" required></label><label for="rate">假设年化资金利率（%）<input id="rate" type="number" min="0" max="30" step="0.5" value="8" required></label><label for="cash">可用自有现金（USD）<input id="cash" type="number" min="0" max="500000" step="5000" value="25000" required></label><label for="demand">假设日需求（件）<input id="demand" type="number" min="0" max="10000" step="50" value="200" required></label><label for="payment">可售后回款等待（天）<input id="payment" type="number" min="0" max="90" step="1" value="14" required></label></div>
<p id="calculation-status" role="status" aria-live="polite">表中为默认假设计算快照；需要 JavaScript 才能交互。</p><noscript><p>JavaScript 已关闭。默认结果可阅读，但输入不会重新计算。</p></noscript>
<div class="metrics"><div class="metric"><small>当前假设下最低经济负担</small><strong id="best-option">{escape(rows[0]['option'])}</strong></div><div class="metric"><small>物流＋利息＋缺货机会成本</small><strong id="best-burden">{money(rows[0]['economic_burden'])}</strong></div><div class="metric"><small>该方案峰值资金缺口</small><strong id="peak-funding">{money(rows[0]['peak_funding_need'])}</strong></div></div>
<div class="table-scroll"><table><thead><tr><th>构造方案</th><th>可用日（发运=0）</th><th>物流现金成本</th><th>缺货机会成本</th><th>资金利息</th><th>经济负担</th><th>净经济贡献</th></tr></thead><tbody id="comparison-body">{tr}</tbody></table></div>
<p class="note">缺货机会成本是未满足需求的毛利损失，不是第二笔现金支出。该模型假设补货订单最终全部售出；没有再叠加“每天延误费”。净经济贡献不是经审计的会计利润。</p><p id="baseline-note"></p><button id="download-case" type="button" disabled>下载当前输入与计算结果</button><button id="reset-case" type="button" class="secondary">恢复示例假设</button>
<h3>查看资金缺口从何时开始</h3><label for="ledger-option">选择方案<select id="ledger-option"></select></label><div class="table-scroll"><table><thead><tr><th>相对发运日</th><th>现金事件</th><th>净现金变动</th><th>含自有资金的余额</th><th>所需融资</th></tr></thead><tbody id="ledger-body"></tbody></table></div><p id="ledger-note" class="note"></p></section>
<section class="columns"><article class="panel"><p class="tag">02 / SUPPLY CHAIN MANAGEMENT</p><h2>更快不一定更划算</h2><p>库存够用时，额外支付加急运费可能不值得；库存不足时，省下的运费可能抵不过缺货损失。把延误改成 0 天，再增加库存覆盖，观察方案排序如何变化。</p><p class="note">三种方案的可订舱性、优先服务及替代港口通关条件均未验证。27 组敏感性情景是确定性比较，不是预测概率。</p></article><article class="panel"><p class="tag">03 / FINANCE & BUSINESS</p><h2>利润和现金不是一回事</h2><p>订单有预计毛利，也可能在回款前需要资金。现金事件表展示订金、尾款、运费与收款的时间差。资金利息按负现金余额的持续时间计算，而非对全部货值重复收费。</p><p class="note">利率不是贷款报价；模型未包含银行审批、汇率、税费、复利或公司全部经营现金流。</p></article></section>
<section class="panel"><p class="tag">04 / TRADE-DOCUMENT INTEGRITY</p><h2>单证一致，不等于交易已被证明</h2><p>本地应用可检查结构化发票、装箱单和投保申请，并演示数字签名。下表是构造测试的静态快照，不是网页正在读取你的文件，也不是对真实单据的识别准确率。</p><div class="table-scroll"><table><thead><tr><th>构造测试</th><th>预期一致</th><th>实际一致</th><th>规则提示</th></tr></thead><tbody>{doc_rows}</tbody></table></div><h3>篡改内容与替换密钥，是两种不同的问题</h3><div class="table-scroll"><table><thead><tr><th>签名测试</th><th>签名数学上有效</th><th>符合单独提供的原始密钥</th><th>真实交易已验证</th></tr></thead><tbody>{sig_rows}</tbody></table></div><p class="note">使用 cryptography 的 Ed25519，密钥只在内存生成。签名能检查内容完整性，但不证明真实货物、保单有效、信用资格或法律上的货权。项目未接入 TradeTrust、银行或区块链；也不符合它们的凭证格式。</p><a href="demo_documents.json" download>下载构造单证 JSON</a> · <a href="https://github.com/sitora77/harborshield/blob/main/docs/TRADE_DOCUMENT_GUIDE_ZH.md">本地单证实验使用指南</a></section>
<section class="panel"><p class="tag">05 / PUBLIC SOURCES & ASSUMPTIONS</p><h2>可核查的来源与边界</h2>{sources}<details><summary>展开全部计算假设与排除项</summary><ul>{assumptions}</ul></details><p><a href="case_study.json" download>下载完整案例及 27 组敏感性结果</a> · <a href="https://github.com/sitora77/harborshield/blob/main/docs/CASE_STUDY.md">阅读可复现实验说明</a></p></section>
<footer>Built with AI-assisted coding. Public facts, constructed assumptions and computed outputs are kept separate. Browser calculator works without a server; document upload/signing requires local Streamlit. Version 0.3 · 4 October 2026.</footer></main><script id="case-inputs" type="application/json">{inputs}</script><script src="case-calculator.js"></script><script src="case-page.js"></script></body></html>'''


def main():
    report = case_report(load_case(ROOT / "data/cases/singapore_2024.json"))
    bundle = parse_json_bytes((ROOT / "data/cases/demo_documents.json").read_bytes())
    report["document_evidence"] = document_evidence(bundle)
    target = ROOT / "reports"
    target.mkdir(exist_ok=True)
    (target / "case_study.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (target / "case-study.html").write_text(build_html(report), encoding="utf-8")
    (ROOT / "docs/CASE_STUDY.md").write_text(build_markdown(report), encoding="utf-8")
    for name in ("case-calculator.js", "case-page.js", "case-study.css"):
        shutil.copyfile(ROOT / "web" / name, target / name)
    shutil.copyfile(ROOT / "data/cases/demo_documents.json", target / "demo_documents.json")
    print(f"Built v0.3 case: {len(report['sensitivity'])} sensitivity settings, 8 constructed document fixtures")


if __name__ == "__main__":
    main()
