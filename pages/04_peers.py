import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.dashboard.utils.db import (
    get_peer_group_names,
    get_peers,
    get_peer_group_percentiles,
)

st.title("Peer Analysis")
st.caption(
    "Compare companies against their peer group using financial performance metrics."
)

# ============================================================
# LOAD PEER GROUPS
# ============================================================

peer_group_names = get_peer_group_names()

if not peer_group_names:
    st.error("Peer-group data is unavailable.")
    st.stop()

selected_group = st.selectbox(
    "Select Peer Group",
    peer_group_names,
)

peers = get_peers(selected_group)

if peers.empty:
    st.warning("No companies are available for this peer group.")
    st.stop()

# ============================================================
# COMPANY SELECTION
# ============================================================

peer_options = (
    peers["company_id"]
    .dropna()
    .astype(str)
    .tolist()
)

company_labels = {}

for _, row in peers.iterrows():
    ticker = str(row["company_id"])
    name = row.get("company_name")

    if pd.isna(name):
        name = ticker

    company_labels[ticker] = f"{name} ({ticker})"

selected_ticker = st.selectbox(
    "Select Company",
    peer_options,
    format_func=lambda ticker: company_labels.get(
        ticker,
        ticker,
    ),
)

selected_company = peers[
    peers["company_id"].astype(str) == selected_ticker
]

selected_name = selected_ticker

if not selected_company.empty:
    name_value = selected_company.iloc[0].get("company_name")

    if pd.notna(name_value):
        selected_name = str(name_value)

# ============================================================
# PEER TABLE
# ============================================================

st.divider()

st.subheader(
    f"{selected_name} — {selected_group}"
)

display_peers = peers.copy()

display_peers["Benchmark"] = (
    pd.to_numeric(
        display_peers["is_benchmark"],
        errors="coerce",
    )
    .fillna(0)
    .map(
        {
            1: "⭐ Benchmark",
            0: "",
        }
    )
)

display_peers = display_peers[
    [
        "company_id",
        "company_name",
        "sector",
        "sub_sector",
        "Benchmark",
    ]
].copy()

display_peers.columns = [
    "Ticker",
    "Company",
    "Sector",
    "Sub-Sector",
    "Benchmark",
]

st.dataframe(
    display_peers,
    hide_index=True,
    use_container_width=True,
)

# ============================================================
# LOAD ALL PEER PERCENTILE DATA
# ============================================================

percentiles = get_peer_group_percentiles(
    selected_group
)

if percentiles.empty:
    st.warning(
        "Peer percentile data is unavailable for this group."
    )
    st.stop()

# ============================================================
# PREFERRED METRICS
# ============================================================

preferred_metrics = [
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "free_cash_flow_cr",
]

metric_labels = {
    "return_on_equity_pct": "ROE",
    "return_on_capital_employed_pct": "ROCE",
    "net_profit_margin_pct": "NPM",
    "operating_profit_margin_pct": "OPM",
    "debt_to_equity": "D/E",
    "revenue_cagr_5yr": "Revenue CAGR 5Y",
    "pat_cagr_5yr": "PAT CAGR 5Y",
    "free_cash_flow_cr": "FCF",
}

available_metrics = [
    metric
    for metric in preferred_metrics
    if metric in percentiles["metric"].astype(str).unique()
]

if not available_metrics:
    st.warning(
        "No comparable financial metrics are available "
        "for this peer group."
    )
    st.stop()

# ============================================================
# FIND LATEST COMMON YEAR
# ============================================================

percentiles["year"] = pd.to_numeric(
    percentiles["year"],
    errors="coerce",
)

valid_years = percentiles["year"].dropna()

if valid_years.empty:
    latest_peer_year = None
    latest_percentiles = percentiles.copy()
else:
    latest_peer_year = int(valid_years.max())

    latest_percentiles = percentiles[
        percentiles["year"] == latest_peer_year
    ].copy()

# ============================================================
# BUILD COMPANY VS PEER DATA
# ============================================================

comparison_rows = []

for metric in available_metrics:

    metric_data = latest_percentiles[
        latest_percentiles["metric"].astype(str) == metric
    ].copy()

    if metric_data.empty:
        continue

    metric_data["company_id"] = (
        metric_data["company_id"]
        .astype(str)
    )

    metric_data["value"] = pd.to_numeric(
        metric_data["value"],
        errors="coerce",
    )

    metric_data = metric_data.dropna(
        subset=["value"]
    )

    if metric_data.empty:
        continue

    # Selected company value
    selected_values = metric_data[
        metric_data["company_id"] == selected_ticker
    ]["value"]

    if selected_values.empty:
        continue

    selected_value = float(
        selected_values.iloc[0]
    )

    # All other companies in the peer group
    peer_values = metric_data[
        metric_data["company_id"] != selected_ticker
    ]["value"]

    peer_values = pd.to_numeric(
        peer_values,
        errors="coerce",
    ).dropna()

    if peer_values.empty:
        continue

    peer_average = float(
        peer_values.mean()
    )

    comparison_rows.append(
        {
            "metric": metric,
            "label": metric_labels.get(
                metric,
                metric,
            ),
            "company_value": selected_value,
            "peer_average": peer_average,
        }
    )

comparison = pd.DataFrame(
    comparison_rows
)

# ============================================================
# COMPANY VS PEER AVERAGE
# ============================================================

st.divider()

st.subheader("Company vs Peer Average")

if comparison.empty:

    st.info(
        "Peer comparison chart cannot be created "
        "because comparable values are unavailable."
    )

else:

    categories = comparison["label"].tolist()

    normalized_company = []
    normalized_peer = []

    for _, row in comparison.iterrows():

        company_value = float(
            row["company_value"]
        )

        peer_value = float(
            row["peer_average"]
        )

        denominator = max(
            abs(company_value),
            abs(peer_value),
            1e-9,
        )

        normalized_company.append(
            company_value / denominator * 100
        )

        normalized_peer.append(
            peer_value / denominator * 100
        )

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=normalized_company,
            theta=categories,
            fill="toself",
            name=selected_name,
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=normalized_peer,
            theta=categories,
            fill="toself",
            name="Peer Average",
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 110],
            )
        ),
        showlegend=True,
        margin=dict(
            l=40,
            r=40,
            t=30,
            b=30,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

# ============================================================
# KPI TABLE
# ============================================================

st.divider()

st.subheader("Peer KPI Comparison")

if not comparison.empty:

    kpi_table = comparison[
        [
            "label",
            "company_value",
            "peer_average",
        ]
    ].copy()

    kpi_table.columns = [
        "Metric",
        selected_name,
        "Peer Average",
    ]

    st.dataframe(
        kpi_table,
        hide_index=True,
        use_container_width=True,
    )

# ============================================================
# BENCHMARK COMPANY
# ============================================================

st.divider()

benchmark_rows = peers[
    pd.to_numeric(
        peers["is_benchmark"],
        errors="coerce",
    ) == 1
]

if not benchmark_rows.empty:

    benchmark_ticker = str(
        benchmark_rows.iloc[0]["company_id"]
    )

    benchmark_name = benchmark_rows.iloc[0].get(
        "company_name"
    )

    if pd.isna(benchmark_name):
        benchmark_name = benchmark_ticker

    st.info(
        f"Benchmark company: "
        f"{benchmark_name} ({benchmark_ticker})"
    )

# ============================================================
# DATA NOTE
# ============================================================

if latest_peer_year is not None:

    st.caption(
        f"Peer comparison year: {latest_peer_year} • "
        f"Peer group: {selected_group} • "
        f"Metrics compared: {len(comparison)}"
    )

else:

    st.caption(
        f"Peer group: {selected_group}"
    )
