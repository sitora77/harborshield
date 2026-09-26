"""Streamlit interface for the HarborShield MVP."""

from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from harborshield.analysis import (
    risk_weight_sensitivity,
    robust_route_summary,
    scenario_stress_test,
)
from harborshield.models import (
    CARGO_RISK,
    SCENARIOS,
    Shipment,
    load_routes,
    rank_routes,
    simulate_route,
)
from harborshield.optimization import optimize_container_portfolio
from harborshield.public_data import activity_summary, load_port_activity


ROOT = Path(__file__).resolve().parent
ROUTES = load_routes(ROOT / "data" / "sample_routes.csv")


def parse_path(path: str) -> List[Tuple[float, float]]:
    points = []
    for pair in path.split(";"):
        latitude, longitude = pair.split(":")
        points.append((float(latitude), float(longitude)))
    return points


def money(value: float) -> str:
    return f"US${value:,.0f}"


st.set_page_config(
    page_title="HarborShield",
    page_icon="⚓",
    layout="wide",
)

st.title("⚓ HarborShield")
st.caption("Risk-aware maritime cargo insurance and intermodal route decision support")
st.info(
    "This prototype uses transparent educational models and simulated route data. "
    "It is not an insurance quotation or operational shipping advice."
)

with st.sidebar:
    st.header("Shipment")
    cargo_value = st.number_input(
        "Cargo value (USD)", min_value=10_000, max_value=5_000_000, value=250_000, step=10_000
    )
    cargo_type = st.selectbox("Cargo type", list(CARGO_RISK.keys()), index=2)
    packaging_quality = st.slider(
        "Packaging quality", 1, 5, 3, help="1 = poor, 5 = robust"
    )
    coverage_ratio = st.slider("Insurance coverage", 0, 100, 90, step=5) / 100
    deductible_ratio = st.slider("Deductible", 0.0, 5.0, 1.0, step=0.25) / 100
    delay_cost = st.number_input(
        "Delay cost per day (USD)", min_value=0, max_value=50_000, value=500, step=100
    )

    st.header("Scenario")
    scenario_name = st.selectbox("Operating condition", list(SCENARIOS.keys()))
    iterations = st.select_slider(
        "Monte Carlo iterations", options=[1_000, 2_500, 5_000, 10_000], value=5_000
    )

    st.header("Decision priorities")
    cost_weight = st.slider("Cost", 0, 100, 40)
    risk_weight = st.slider("Risk", 0, 100, 30)
    time_weight = st.slider("Time", 0, 100, 20)
    carbon_weight = st.slider("Carbon", 0, 100, 10)


shipment = Shipment(
    cargo_value=float(cargo_value),
    cargo_type=cargo_type,
    packaging_quality=packaging_quality,
    coverage_ratio=coverage_ratio,
    deductible_ratio=deductible_ratio,
    delay_cost_per_day=float(delay_cost),
)
scenario = SCENARIOS[scenario_name]

results = [
    simulate_route(
        shipment,
        route,
        scenario,
        iterations=iterations,
        seed=42 + index,
    )
    for index, route in enumerate(ROUTES)
]
ranked = rank_routes(
    results,
    cost_weight=cost_weight,
    risk_weight=risk_weight,
    time_weight=time_weight,
    carbon_weight=carbon_weight,
)

if not ranked:
    st.error("No routes are available.")
    st.stop()

best = ranked[0]
best_route = next(route for route in ROUTES if route.route_id == best["route_id"])

st.subheader("Recommended option")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Route", best["route_name"])
col2.metric("Estimated claim probability", f"{best['claim_probability']:.2%}")
col3.metric("Expected total logistics cost", money(best["expected_total_cost"]))
col4.metric("Expected additional delay", f"{best['expected_delay_days']:.1f} days")

st.success(
    f"Under **{scenario_name}**, the model recommends **{best_route.name}** "
    f"({best_route.via}) because it has the lowest weighted decision score."
)

display_rows: List[Dict[str, object]] = []
for position, row in enumerate(ranked, start=1):
    display_rows.append(
        {
            "Rank": position,
            "Route": row["route_name"],
            "Decision score ↓": round(row["decision_score"], 1),
            "Claim probability": f"{row['claim_probability']:.2%}",
            "Expected cost": money(row["expected_total_cost"]),
            "CVaR95 cost": money(row["cvar95_total_cost"]),
            "Transit + delay": f"{row['duration_days'] + row['expected_delay_days']:.1f} days",
            "CO₂": f"{row['carbon_kg']:,.0f} kg",
        }
    )

st.subheader("Route comparison")
st.dataframe(pd.DataFrame(display_rows), width="stretch", hide_index=True)

chart_data = pd.DataFrame(
    {
        "Route": [row["route_name"] for row in ranked for _ in range(4)],
        "Component": [
            component
            for _ in ranked
            for component in ["Freight", "Insurance premium", "Retained loss", "Delay + carbon"]
        ],
        "USD": [
            value
            for row in ranked
            for value in [
                row["freight_cost"],
                row["insurance_premium"],
                row["expected_retained_loss"],
                row["expected_delay_cost"] + row["carbon_cost"],
            ]
        ],
    }
)
figure = px.bar(
    chart_data,
    x="Route",
    y="USD",
    color="Component",
    title="Expected cost composition",
    barmode="stack",
)
figure.update_layout(legend_title_text="")
st.plotly_chart(figure)

st.subheader("Illustrative route map")
map_figure = go.Figure()
palette = ["#0B6E99", "#F28E2B", "#59A14F"]
for route, color in zip(ROUTES, palette):
    points = parse_path(route.path)
    map_figure.add_trace(
        go.Scattermap(
            lat=[point[0] for point in points],
            lon=[point[1] for point in points],
            mode="lines+markers",
            line={"width": 3, "color": color},
            marker={"size": 8},
            name=route.name,
            text=route.via.split(" → "),
            hovertemplate="%{text}<extra>%{fullData.name}</extra>",
        )
    )
map_figure.update_layout(
    map={"style": "open-street-map", "center": {"lat": 15, "lon": 113}, "zoom": 2.6},
    margin={"l": 0, "r": 0, "t": 0, "b": 0},
    height=480,
    legend={"orientation": "h"},
)
st.plotly_chart(map_figure)

with st.expander("How the model works"):
    st.markdown(
        """
        1. A logistic risk model combines cargo sensitivity, packaging, voyage duration,
           transshipments, weather exposure, congestion, disruption, and reliability.
        2. Monte Carlo simulation samples cargo-loss events, loss severity, and delays.
        3. Insurance reduces retained cargo loss but adds a risk-based premium.
        4. Routes are normalised and ranked using the selected cost, risk, time, and carbon weights.

        Every assumption is visible in `harborshield/models.py` so the result can be audited.
        """
    )

download_frame = pd.DataFrame(ranked)
st.download_button(
    "Download simulation results (CSV)",
    download_frame.to_csv(index=False).encode("utf-8"),
    file_name="harborshield_results.csv",
    mime="text/csv",
)

st.divider()
st.header("Advanced analysis")
stress_tab, portfolio_tab, public_data_tab, model_tab = st.tabs(
    ["Scenario stress test", "Container portfolio", "Public data", "Model card"]
)

with stress_tab:
    st.subheader("Cross-scenario robustness")
    st.caption(
        "A robust choice should remain competitive across disruptions, not only "
        "under the currently selected scenario."
    )
    stress_rows = scenario_stress_test(
        shipment,
        ROUTES,
        iterations=min(iterations, 2_500),
        cost_weight=cost_weight,
        risk_weight=risk_weight,
        time_weight=time_weight,
        carbon_weight=carbon_weight,
    )
    stress_frame = pd.DataFrame(stress_rows)
    stress_display = stress_frame[
        [
            "scenario",
            "route_name",
            "rank",
            "decision_score",
            "claim_probability",
            "expected_total_cost",
            "cvar95_total_cost",
        ]
    ].copy()
    stress_display.columns = [
        "Scenario",
        "Route",
        "Rank",
        "Decision score",
        "Claim probability",
        "Expected cost",
        "CVaR95 cost",
    ]
    stress_display["Decision score"] = stress_display["Decision score"].round(1)
    stress_display["Claim probability"] = stress_display["Claim probability"].map(
        lambda value: f"{value:.2%}"
    )
    stress_display["Expected cost"] = stress_display["Expected cost"].map(money)
    stress_display["CVaR95 cost"] = stress_display["CVaR95 cost"].map(money)
    st.dataframe(stress_display, width="stretch", hide_index=True)

    robust_rows = robust_route_summary(stress_rows)
    robust_display = pd.DataFrame(robust_rows)
    robust_display = robust_display[
        [
            "route_name",
            "average_rank",
            "wins",
            "worst_case_cost",
            "maximum_claim_probability",
            "average_cost_regret",
        ]
    ]
    robust_display.columns = [
        "Route",
        "Average rank",
        "Scenario wins",
        "Worst CVaR95 cost",
        "Maximum claim probability",
        "Average cost regret",
    ]
    robust_display["Average rank"] = robust_display["Average rank"].round(2)
    robust_display["Worst CVaR95 cost"] = robust_display["Worst CVaR95 cost"].map(money)
    robust_display["Maximum claim probability"] = robust_display[
        "Maximum claim probability"
    ].map(lambda value: f"{value:.2%}")
    robust_display["Average cost regret"] = robust_display["Average cost regret"].map(
        money
    )
    st.markdown("**Robustness summary**")
    st.dataframe(robust_display, width="stretch", hide_index=True)

    stress_chart = px.line(
        stress_frame,
        x="scenario",
        y="expected_total_cost",
        color="route_name",
        markers=True,
        title="Expected cost under disruption scenarios",
        labels={
            "scenario": "Scenario",
            "expected_total_cost": "Expected cost (USD)",
            "route_name": "Route",
        },
    )
    st.plotly_chart(stress_chart)

    sensitivity_rows = risk_weight_sensitivity(
        shipment,
        ROUTES,
        scenario_name,
        iterations=min(iterations, 2_000),
    )
    sensitivity_frame = pd.DataFrame(sensitivity_rows)
    sensitivity_chart = px.line(
        sensitivity_frame,
        x="risk_weight_percent",
        y="decision_score",
        color="route_name",
        markers=True,
        title="Sensitivity to risk preference",
        labels={
            "risk_weight_percent": "Risk weight (%)",
            "decision_score": "Decision score (lower is better)",
            "route_name": "Route",
        },
    )
    st.plotly_chart(sensitivity_chart)
    recommended_by_weight = sensitivity_frame[sensitivity_frame["recommended"]][
        ["risk_weight_percent", "route_name"]
    ].copy()
    recommended_by_weight.columns = ["Risk weight (%)", "Recommended route"]
    st.dataframe(recommended_by_weight, width="stretch", hide_index=True)

with portfolio_tab:
    st.subheader("Risk-aware container allocation")
    st.caption(
        "OR-Tools solves an integer programme that allocates a batch across routes "
        "while limiting concentration and average transit time."
    )
    portfolio_col1, portfolio_col2, portfolio_col3 = st.columns(3)
    containers = portfolio_col1.slider(
        "Containers", 3, 100, 20, key="portfolio_containers"
    )
    maximum_share = portfolio_col2.slider(
        "Maximum share on one route",
        0.40,
        1.00,
        0.70,
        step=0.05,
        key="portfolio_share",
    )
    maximum_transit = portfolio_col3.slider(
        "Maximum average transit (days)",
        14.0,
        30.0,
        22.0,
        step=0.5,
        key="portfolio_transit",
    )
    risk_aversion = st.slider(
        "Tail-risk aversion",
        0.0,
        2.0,
        0.5,
        step=0.1,
        help="Adds a penalty for the gap between CVaR95 and expected cost.",
        key="portfolio_risk_aversion",
    )
    solution = optimize_container_portfolio(
        ROUTES,
        results,
        containers=containers,
        maximum_route_share=maximum_share,
        maximum_average_transit_days=maximum_transit,
        risk_aversion=risk_aversion,
    )
    if solution is None:
        st.warning(
            "No feasible allocation satisfies both constraints. Increase the "
            "maximum route share or average transit limit."
        )
    else:
        pcol1, pcol2, pcol3 = st.columns(3)
        pcol1.metric("Solver status", solution.status.title())
        pcol2.metric("Expected batch cost", money(solution.expected_total_cost))
        pcol3.metric("Average transit", f"{solution.average_transit_days:.1f} days")
        route_names = {route.route_id: route.name for route in ROUTES}
        allocation_frame = pd.DataFrame(
            [
                {
                    "Route": route_names[route_id],
                    "Containers": count,
                    "Share": count / containers,
                }
                for route_id, count in solution.allocations.items()
            ]
        )
        allocation_frame["Share"] = allocation_frame["Share"].map(
            lambda value: f"{value:.0%}"
        )
        st.dataframe(allocation_frame, width="stretch", hide_index=True)
        allocation_chart = px.bar(
            allocation_frame,
            x="Route",
            y="Containers",
            color="Route",
            title="Optimised container allocation",
        )
        allocation_chart.update_layout(showlegend=False)
        st.plotly_chart(allocation_chart)

with public_data_tab:
    st.subheader("Singapore port activity context")
    observations = load_port_activity(ROOT / "data" / "mpa_vessel_arrivals_monthly.csv")
    activity = activity_summary(observations)
    dcol1, dcol2, dcol3 = st.columns(3)
    dcol1.metric("Latest month", str(activity["latest_month"]))
    dcol2.metric(
        "Vessel arrivals",
        f"{activity['latest_vessel_arrivals']:,.0f}",
        f"{activity['year_over_year_change']:+.1%} YoY",
    )
    dcol3.metric(
        "Activity-pressure index",
        f"{activity['activity_pressure_index']:.2f}",
        help="Latest arrivals divided by the preceding 12-month median.",
    )
    activity_frame = pd.DataFrame(
        [
            {
                "Month": observation.month,
                "Vessel arrivals": observation.vessel_arrivals,
                "Gross tonnage (source unit)": observation.gross_tonnage_thousand,
            }
            for observation in observations
        ]
    )
    activity_chart = px.line(
        activity_frame,
        x="Month",
        y="Vessel arrivals",
        markers=True,
        title="Monthly vessel arrivals at Singapore",
    )
    st.plotly_chart(activity_chart)
    st.warning(
        "Vessel-arrival volume is an activity-pressure proxy, not a direct "
        "measurement of port waiting time or congestion. It is shown as context "
        "and is not used to claim causal congestion effects."
    )
    st.markdown(
        "Source: [Maritime and Port Authority of Singapore via data.gov.sg]"
        "(https://data.gov.sg/datasets/d_d48c5a038904f6da3c603cd854b6c191/view)."
    )

with model_tab:
    st.subheader("Model card and research basis")
    st.markdown(
        """
        **Purpose:** portfolio-level decision support and scenario exploration.  
        **Not intended for:** actuarial pricing, binding insurance quotations, or live vessel operations.  
        **Real public input:** monthly Singapore vessel arrivals from MPA/data.gov.sg.  
        **Simulated inputs:** route price, duration, reliability, exposure, and carbon values.  
        **Methods:** logistic risk scoring, Monte Carlo uncertainty propagation,
        weighted multi-criteria ranking, stress testing, and integer optimisation.

        Selected research references:

        - [Maritime Port Supply Chain Resilience: A Systematic Review](https://arxiv.org/abs/2510.09844v1)
        - [Temporal-IRL: Modeling Port Congestion and Berth Scheduling](https://arxiv.org/abs/2506.19843v1)
        - [Learning Large Neighborhood Search for Maritime Inventory Routing Optimization](https://arxiv.org/abs/2502.15244v2)
        - [Efficient Propagation of Uncertainties in Manufacturing Supply Chains](https://arxiv.org/abs/1808.07121v2)
        - [Performance-Based Risk Assessment for Large-Scale Transportation Networks](https://arxiv.org/abs/2411.03580v1)

        See `docs/LITERATURE_AND_OPEN_SOURCE.md` and `docs/METHODOLOGY.md`
        for the complete traceability notes and limitations.
        """
    )
