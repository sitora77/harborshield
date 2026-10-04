"""Independent real-data analysis; no coupling to the synthetic cargo-risk UI."""
import json

import pandas as pd
import plotly.express as px
import streamlit as st

from harborshield.portwatch import load_snapshot, run_backtest


def render_portwatch(root):
    st.subheader("Real-data backtest · Singapore container-ship port calls")
    st.caption("真实数据回测：2022 训练 → 2023 选择方法 → 2024 最终测试。Counts per UTC day, not TEU or port waiting time.")
    try:
        rows, metadata = load_snapshot(root / "data/portwatch")
        report = run_backtest(rows, metadata)
    except (ValueError, OSError, KeyError) as error:
        st.session_state.pop("real_data_summary", None)
        st.error(f"Real-data analysis blocked: {error}. No synthetic data is substituted.")
        return
    st.session_state["real_data_summary"] = report
    method = report["selected_method"]
    names = report["method_names"]
    columns = st.columns(3)
    columns[0].metric("Real daily observations", f"{len(rows):,}")
    columns[1].metric("Held-out days · 2024", report["splits"]["test"]["n"])
    columns[2].metric("Selected model · daily MAE (calls)", f"{report['test'][method]['mae']:.2f}")
    st.success(f"Selected on 2023 only: {names[method]}. All source hashes and daily quality checks pass.")
    st.write(report["protocol"])
    table = pd.DataFrame([{"Method": names[key], "Selected on 2023": key == method,
                           "2023 MAE": report["validation"][key]["mae"], "2024 MAE": result["mae"],
                           "2024 RMSE": result["rmse"], "2024 WAPE": result["wape"]}
                          for key, result in report["test"].items()])
    st.dataframe(table, hide_index=True, width="stretch")
    forecasts = pd.DataFrame(report["forecasts"]).rename(columns={"actual": "Observed calls", "predicted": "Selected forecast"})
    figure = px.line(forecasts, x="date", y=["Observed calls", "Selected forecast"],
                     labels={"value": "Container-ship calls / UTC day", "date": "2024 target date", "variable": "Series"},
                     title="Daily historical observations versus one-day-ahead forecasts")
    st.plotly_chart(figure)
    st.dataframe(pd.DataFrame(report["monthly"]), hide_index=True, width="stretch")
    st.warning("This real-data experiment validates port-activity forecasts only. It does not measure port waiting, shipment delay, cargo loss, insurance prices or finance outcomes. Forecast counts are NOT converted to the case calculator's assumed delay.")
    st.markdown("Source: [IMF PortWatch](" + report["source"]["dataset"] + "). " + report["source"]["attribution"])
    st.caption("Retrieved UTC: " + metadata["retrieved_at_utc"] + " · SHA-256: " + metadata["snapshot_sha256"])
    st.download_button("Download real-data backtest (JSON)", json.dumps(report, ensure_ascii=False, indent=2),
                       "harborshield_real_data.json", "application/json")
