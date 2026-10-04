"""Small bilingual evidence pages, rendered from the same measured results."""
from collections import defaultdict
from datetime import timedelta
from html import escape

from harborshield.portwatch import METHODS, strict_date


COPY = {
    "en": {
        "title": "Real data. An honest forecast test.",
        "subtitle": "Singapore container-ship port calls · IMF PortWatch · 2022–2024",
        "back": "← Portfolio", "switch": "中文", "other": "real-data.html",
        "boundary": "Real AIS-derived activity observations, not simulated cargo orders. This experiment tests next-day port-call forecasts. It does not validate cargo delay, insurance prices or business savings.",
        "counts": "Daily observations", "target": "Final test days (2024)", "error": "Selected method · mean absolute error",
        "unit": "calls / day", "quality": "Source quality checks",
        "quality_text": "No missing dates, duplicate dates or invalid counts in this snapshot. Missing values are rejected, never replaced by zero. Source-page and snapshot SHA-256 checksums reconcile.",
        "split": "Past first. Future last.",
        "protocol": "2022: fit models. 2023: choose the method with the lowest validation MAE. Refit ridge on 2022–2023, then freeze coefficients. 2024: rolling one-day-ahead test using only previously observed counts. Earlier 2024 observations are allowed as lag inputs; current and future targets are not. This is not a forecast of the entire year made on 1 January.",
        "train": "TRAIN / 2022", "validation": "SELECT / 2023", "test": "TEST / 2024",
        "selected": "Method selected before the final test", "gain": "MAE change versus yesterday baseline",
        "no_guarantee": "Selection uses 2023, not the best-looking 2024 result. A more complex model is not assumed to win. Negative improvement means worse error. These historical records were retrieved later and may contain revisions; this is not a contemporaneous 2024 data-vintage backtest.",
        "comparison": "Simple baselines versus an interpretable model",
        "headers": ["Method", "2023 MAE ↓", "2024 MAE ↓", "2024 RMSE ↓", "2024 WAPE ↓"],
        "methods": dict(METHODS), "chosen": "Selected on 2023",
        "plot": "Forecast versus observed activity",
        "plot_note": "Weekly means for legibility; first and last partial weeks are retained. All forecast errors above are calculated on the 366 daily targets, not these averages.",
        "actual": "Observed", "predicted": "Selected forecast", "axis": "Container-ship calls / UTC day (weekly mean)",
        "months": "Where does error vary?",
        "month_headers": ["2024 month", "Days", "Observed mean", "Forecast mean", "Daily MAE", "WAPE"],
        "use": "A realistic role — and the missing link",
        "use_text": "A freight-forwarding operations analyst could use port-call forecasts as an activity-monitoring input and review unusually large forecast errors. To make an actual routing or replenishment recommendation, the next study still needs matched waiting-time, schedule, delivery, quote and cost observations. More calls alone do not prove congestion. There is deliberately no automatic conversion from forecast calls to the constructed order's delay assumption.",
        "sources": "Source, methodology and reproduction",
        "source_text": "A fixed, noncommercial research subset: Singapore port1201 only, not all Singapore-area port boundaries. Dates are UTC. Counts indicate container-ship entries into the source port boundary, not unique ships, containers or TEU. AIS coverage, classification and historical revisions can affect the indicator.",
        "paper": "IMF Working Paper 2021/225: Tracking Trade from Space",
        "reference": "World Bank example: port-call trends monitoring",
        "reference_note": "These references inform data provenance, AIS limitations, pagination and activity monitoring. The forecast experiment is implemented here, not reported as a replication of their findings.",
        "retrieved": "Retrieved (UTC)", "hash": "Snapshot SHA-256", "terms": "IMF data usage terms — separate from the code's MIT licence",
        "downloads": "Download complete experiment JSON", "repo": "View data, tests and reproduction guide on GitHub",
        "limitations": "One port and one final test year. No enterprise pilot, insurance/credit calibration or realised savings. AI-assisted implementation is disclosed; the owner's independent learning record is not invented.",
    },
    "zh": {
        "title": "真实数据，不回避预测误差。", "subtitle": "新加坡集装箱船靠港次数 · IMF PortWatch · 2022–2024",
        "back": "← 个人主页", "switch": "English", "other": "real-data-en.html",
        "boundary": "这里是基于 AIS 的真实港口活动观测，不是构造订单。实验验证的是次日靠港次数预测，不能据此声称验证了货物延误、保险费率或商业节省。",
        "counts": "逐日观测记录", "target": "最终测试天数（2024）", "error": "预先选定方法 · 平均绝对误差", "unit": "次 / 天",
        "quality": "来源与数据质量检查", "quality_text": "本快照没有缺失日期、重复日期或非法计数。缺失值会阻止运行，不会用零填充。原始接口响应和整理快照的 SHA-256 校验一致。",
        "split": "先过去，再未来。",
        "protocol": "2022 年拟合；2023 年按平均绝对误差（MAE）选择方法。岭回归随后仅用 2022–2023 年重新拟合并冻结系数。2024 年逐日向前预测：可以使用此前已观察到的 2024 年记录，不能使用当天或未来的真实值。这不是在 1 月 1 日一次性预测整年。",
        "train": "训练 / 2022", "validation": "选方法 / 2023", "test": "最终测试 / 2024",
        "selected": "进入最终测试前选定的方法", "gain": "相比“直接用昨天”的 MAE 改善",
        "no_guarantee": "方法由 2023 年决定，不按 2024 年结果挑选赢家。复杂模型不一定更好；负的改善值代表误差更大。这是后来下载的历史数据，可能经过修订，不是使用 2024 年当时数据版本的回测。",
        "comparison": "简单基线与可解释模型的比较", "headers": ["方法", "2023 MAE ↓", "2024 MAE ↓", "2024 RMSE ↓", "2024 WAPE ↓"],
        "methods": {"yesterday": "直接使用昨天次数", "last_week": "使用上周同一天", "mean_28": "此前 28 天均值", "weekday_4": "此前四周同一星期几的均值", "ridge_ar": "岭回归自回归（固定惩罚 10）"},
        "chosen": "2023 年选定", "plot": "预测与真实观测的对照",
        "plot_note": "图中使用周均值方便阅读；首尾不足一周的记录保留。上面的误差按 366 个逐日目标计算，不按周均值计算。",
        "actual": "真实观测", "predicted": "选定方法预测", "axis": "集装箱船靠港次数 / UTC 日（周均值）",
        "months": "哪些月份更难预测？", "month_headers": ["2024 月份", "天数", "真实日均次数", "预测日均次数", "逐日 MAE", "WAPE"],
        "use": "可以对应实际工作，但还缺关键证据",
        "use_text": "货代运营分析人员可以把靠港次数预测作为活动监测输入，在预测误差异常时进一步核查。若要据此做真实航线或补货决策，还需要同时间、同港口的等待时间、船期、交付、报价和成本观测。次数增多不等于拥堵，因此本实验不会自动把靠港次数换算成构造订单中的延误天数。",
        "sources": "来源、方法参考与复现", "source_text": "仅选取新加坡 port1201 的非商业研究子集，不代表所有新加坡周边港区。日期为 UTC；次数指集装箱船进入来源定义港区的事件，不是独立船舶数量、集装箱数或 TEU。AIS 覆盖、分类和历史修订可能影响指标。",
        "paper": "IMF 工作论文 2021/225：Tracking Trade from Space", "reference": "世界银行公开示例：港口靠港活动监测",
        "reference_note": "参考资料用于理解 AIS 数据来源、局限、分页和活动监测。本项目自行实现预测实验，不冒充对这些论文结论的复现。",
        "retrieved": "下载时间（UTC）", "hash": "快照 SHA-256", "terms": "IMF 数据使用条款——与代码的 MIT 许可分开",
        "downloads": "下载完整实验结果 JSON", "repo": "在 GitHub 查看数据、测试和复现指南",
        "limitations": "只有一个港口、一个最终测试年份；未做企业试点，未校准保险或信用模型，未证明真实节省。开发使用 AI 辅助；不会编造申请者独立学习或复现记录。",
    },
}


def table(headers, rows, selected=None):
    head = "".join(f'<th scope="col">{escape(str(value))}</th>' for value in headers)
    body = "".join('<tr' + (' class="selected"' if index == selected else '') + '>' +
                   "".join(f"<td>{escape(str(value))}</td>" for value in row) + "</tr>"
                   for index, row in enumerate(rows))
    return f'<div class="table-scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def activity_svg(forecasts, text):
    groups = defaultdict(list)
    for row in forecasts:
        day = strict_date(row["date"])
        groups[day - timedelta(days=day.weekday())].append(row)
    weeks = sorted(groups)
    means = {field: [sum(r[field] for r in groups[week]) / len(groups[week]) for week in weeks]
             for field in ("actual", "predicted")}
    ceiling = max(10, int(max(means["actual"] + means["predicted"]) / 10 + 1) * 10)
    width, height, left, bottom = 1100, 310, 52, 258
    x = lambda index: left + index / (len(weeks) - 1) * (width - left - 24)
    y = lambda value: bottom - value / ceiling * 204
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="chart-title chart-desc">',
             f'<title id="chart-title">{escape(text["plot"])}</title>',
             f'<desc id="chart-desc">{escape(text["plot_note"])}</desc>',
             f'<text x="{left}" y="22" fill="#afc1bd" font-size="13">{escape(text["axis"])}</text>']
    for value in range(0, ceiling + 1, 10):
        parts.extend([f'<line x1="{left}" y1="{y(value):.1f}" x2="1076" y2="{y(value):.1f}" stroke="#31474c"/>',
                      f'<text x="40" y="{y(value) + 4:.1f}" text-anchor="end" fill="#afc1bd" font-size="12">{value}</text>'])
    for index in range(0, len(weeks), 8):
        parts.append(f'<text x="{x(index):.1f}" y="282" text-anchor="middle" fill="#afc1bd" font-size="12">{weeks[index].isoformat()[:7]}</text>')
    for field, colour in (("actual", "#a8d6c4"), ("predicted", "#e8c989")):
        points = " ".join(f"{x(i):.1f},{y(value):.1f}" for i, value in enumerate(means[field]))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{colour}" stroke-width="2.5"/>')
    parts.append('</svg>')
    return "".join(parts)


def build_page(report, language="zh"):
    t = COPY[language]
    selected = report["selected_method"]
    number = lambda value: f"{value:.2f}"
    percent = lambda value: f"{value:.1%}" if value is not None else "—"
    rows = [[t["methods"][method] + (f' · {t["chosen"]}' if method == selected else ''),
             number(report["validation"][method]["mae"]), number(report["test"][method]["mae"]),
             number(report["test"][method]["rmse"]), percent(report["test"][method]["wape"])] for method in METHODS]
    months = [[r["month"], r["n"], number(r["actual_mean"]), number(r["predicted_mean"]), number(r["mae"]), percent(r["wape"])]
              for r in report["monthly"]]
    source = report["source"]
    quality = report["quality"]
    e = escape
    return f'''<!doctype html>
<html lang="{language}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{e(t['subtitle'])}"><title>HarborShield · {e(t['title'])}</title>
<link rel="stylesheet" href="real-data.css"></head><body><main>
<nav aria-label="Navigation"><a href="index.html">{e(t['back'])}</a><a href="{t['other']}" lang="{'en' if language == 'zh' else 'zh'}">{e(t['switch'])}</a></nav>
<header><p class="eyebrow">HARBORSHIELD / v0.5 / REAL-DATA EVIDENCE</p><h1>{e(t['title'])}</h1><p class="subtitle">{e(t['subtitle'])}</p></header>
<p class="boundary">{e(t['boundary'])}</p>
<section class="metrics" aria-label="Key results"><div class="metric"><small>{e(t['counts'])}</small><strong>{quality['rows']:,}</strong></div>
<div class="metric"><small>{e(t['target'])}</small><strong>{report['splits']['test']['n']}</strong></div>
<div class="metric"><small>{e(t['error'])}</small><strong>{number(report['test'][selected]['mae'])} {e(t['unit'])}</strong></div></section>
<section class="panel"><h2>{e(t['split'])}</h2><div class="split"><div>{e(t['train'])}<strong>365</strong></div><div>{e(t['validation'])}<strong>365</strong></div><div>{e(t['test'])}<strong>366</strong></div></div><p>{e(t['protocol'])}</p>
<p class="decision-notice">{e(t['selected'])}: <strong>{e(t['methods'][selected])}</strong><br>{e(t['gain'])}: <strong>{percent(report['mae_improvement_vs_yesterday'])}</strong></p><p class="note">{e(t['no_guarantee'])}</p></section>
<section class="panel"><h2>{e(t['comparison'])}</h2>{table(t['headers'], rows, list(METHODS).index(selected))}<p class="note">MAE = mean absolute error · RMSE = root mean squared error · WAPE = Σ|error| / Σobserved. MAE/RMSE: {e(t['unit'])}.</p></section>
<section class="panel"><h2>{e(t['plot'])}</h2><p class="legend"><span class="observed">— {e(t['actual'])}</span> <span class="forecast">— {e(t['predicted'])}</span></p>{activity_svg(report['forecasts'], t)}<p class="note">{e(t['plot_note'])}</p></section>
<section class="panel"><h2>{e(t['months'])}</h2>{table(t['month_headers'], months)}</section>
<section class="panel"><h2>{e(t['use'])}</h2><p>{e(t['use_text'])}</p><h3>{e(t['quality'])}</h3><p>{e(t['quality_text'])}</p><p class="note">{quality['start']} → {quality['end']} · port1201 · {quality['zero_count_days']} zero-count days</p></section>
<section class="panel"><h2>{e(t['sources'])}</h2><p>{e(t['source_text'])}</p><p><a href="{e(source['dataset'], quote=True)}">IMF PortWatch · Daily_Ports_Data</a><br>{e(source['attribution'])}</p>
<p><a href="https://www.imf.org/en/Publications/WP/Issues/2021/08/20/Tracking-Trade-from-Space-An-Application-to-Pacific-Island-Countries-464345">{e(t['paper'])}</a><br>
<a href="https://worldbank.github.io/alternative-data-for-crisis/notebooks/disruptions-business-trade/port-calls-trends-monitor.html">{e(t['reference'])}</a></p><p class="note">{e(t['reference_note'])}</p>
<p>{e(t['retrieved'])}: {e(source['retrieved_at_utc'])}<br>{e(t['hash'])}: <code class="digest">{source['snapshot_sha256']}</code></p>
<p><a href="{e(source['terms'], quote=True)}">{e(t['terms'])}</a></p>
<p><a class="download" href="real-data-report.json" download>{e(t['downloads'])}</a></p><p><a href="https://github.com/sitora77/harborshield/blob/main/docs/REAL_DATA_GUIDE_ZH.md">{e(t['repo'])}</a></p></section>
<footer>{e(t['limitations'])}</footer></main></body></html>'''
