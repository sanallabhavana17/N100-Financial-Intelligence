import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

from src.dashboard.style import configure_page, apply_styles


configure_page()
apply_styles()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PEER_FILE = PROJECT_ROOT / "output" / "peer_percentile_table.csv"

st.title("?? Peer Comparison")
st.caption(
    "Compare companies against their peer group using financial metrics "
    "and percentile scores."
)

if not PEER_FILE.exists():
    st.error(f"Peer comparison file not found: {PEER_FILE}")
    st.stop()

df = pd.read_csv(PEER_FILE)

required_columns = [
    "peer_group_name",
    "company_id",
    "year",
    "peer_rank",
    "peer_group_size",
    "peer_composite_percentile",
]

missing = [c for c in required_columns if c not in df.columns]

if missing:
    st.error(f"Missing columns: {missing}")
    st.stop()


# Sidebar
st.sidebar.header("Peer Comparison")

peer_groups = sorted(
    df["peer_group_name"].dropna().unique().tolist()
)

selected_group = st.sidebar.selectbox(
    "Peer Group",
    peer_groups,
)

group_df = df[
    df["peer_group_name"] == selected_group
].copy()

years = sorted(
    pd.to_numeric(
        group_df["year"],
        errors="coerce",
    ).dropna().unique().tolist()
)

selected_year = st.sidebar.selectbox(
    "Year",
    years,
    index=len(years) - 1,
)

year_df = group_df[
    pd.to_numeric(group_df["year"], errors="coerce")
    == selected_year
].copy()

if year_df.empty:
    st.warning("No data available for the selected year.")
    st.stop()


# Summary
st.subheader(f"{selected_group} — {int(selected_year)}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Companies", year_df["company_id"].nunique())

with col2:
    st.metric(
        "Peer Group Size",
        int(year_df["peer_group_size"].max()),
    )

with col3:
    benchmark_rows = year_df[
        pd.to_numeric(
            year_df["is_benchmark"],
            errors="coerce",
        ).eq(1)
    ]

    benchmark_id = (
        str(benchmark_rows.iloc[0]["company_id"])
        if not benchmark_rows.empty
        else "N/A"
    )

    st.metric("Benchmark", benchmark_id)

with col4:
    median_percentile = pd.to_numeric(
        year_df["peer_composite_percentile"],
        errors="coerce",
    ).median()

    st.metric(
        "Median Peer Percentile",
        f"{median_percentile:.1f}"
        if pd.notna(median_percentile)
        else "N/A",
    )


# Company selection
st.subheader("Select Companies")

company_options = sorted(
    year_df["company_id"].dropna().unique().tolist()
)

default_companies = (
    year_df.sort_values("peer_rank")
    ["company_id"]
    .dropna()
    .head(5)
    .tolist()
)

selected_companies = st.multiselect(
    "Choose companies for radar comparison",
    company_options,
    default=default_companies,
    max_selections=8,
)


# Radar
st.subheader("Peer Radar Comparison")

radar_metrics = {
    "ROE": "return_on_equity_pct_percentile",
    "ROCE": "return_on_capital_employed_pct_percentile",
    "ROA": "return_on_assets_pct_percentile",
    "NPM": "net_profit_margin_pct_percentile",
    "OPM": "operating_profit_margin_pct_percentile",
    "Revenue CAGR": "revenue_cagr_5yr_percentile",
    "PAT CAGR": "pat_cagr_5yr_percentile",
    "Quality Score": "composite_quality_score_percentile",
}

available_radar = {
    label: column
    for label, column in radar_metrics.items()
    if column in year_df.columns
}

if selected_companies and available_radar:

    fig = go.Figure()

    categories = list(available_radar.keys())

    for company in selected_companies:

        company_row = year_df[
            year_df["company_id"] == company
        ]

        if company_row.empty:
            continue

        row = company_row.iloc[0]

        values = []

        for column in available_radar.values():

            value = pd.to_numeric(
                row[column],
                errors="coerce",
            )

            values.append(
                float(value)
                if pd.notna(value)
                else 0.0
            )

        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name=str(company),
            )
        )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
            )
        ),
        height=600,
        margin=dict(
            l=50,
            r=50,
            t=50,
            b=50,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

else:
    st.info("Select at least one company.")


# Side-by-side comparison
st.subheader("Side-by-Side Financial Comparison")

comparison_metrics = {
    "ROE (%)": "return_on_equity_pct",
    "ROCE (%)": "return_on_capital_employed_pct",
    "ROA (%)": "return_on_assets_pct",
    "Net Profit Margin (%)": "net_profit_margin_pct",
    "Operating Margin (%)": "operating_profit_margin_pct",
    "Debt / Equity": "debt_to_equity",
    "Interest Coverage": "interest_coverage",
    "Revenue CAGR 5Y (%)": "revenue_cagr_5yr",
    "PAT CAGR 5Y (%)": "pat_cagr_5yr",
    "EPS CAGR 5Y (%)": "eps_cagr_5yr",
    "Free Cash Flow (Cr)": "free_cash_flow_cr",
    "Asset Turnover": "asset_turnover",
    "Quality Score": "composite_quality_score",
    "Peer Percentile": "peer_composite_percentile",
    "Peer Rank": "peer_rank",
}

comparison_rows = []

for label, column in comparison_metrics.items():

    if column not in year_df.columns:
        continue

    row = {"Metric": label}

    for company in selected_companies:

        company_rows = year_df[
            year_df["company_id"] == company
        ]

        if company_rows.empty:
            row[company] = "N/A"
            continue

        value = company_rows.iloc[0][column]

        if pd.isna(value):
            row[company] = "N/A"
        elif column == "peer_rank":
            row[company] = int(float(value))
        else:
            try:
                row[company] = round(float(value), 2)
            except (ValueError, TypeError):
                row[company] = str(value)

    comparison_rows.append(row)

if comparison_rows and selected_companies:

    comparison_df = pd.DataFrame(comparison_rows)

    st.dataframe(
        comparison_df,
        use_container_width=True,
        hide_index=True,
    )

else:
    st.info(
        "Select companies above to display the comparison table."
    )


# Full peer ranking
st.subheader("Peer Ranking")

ranking_columns = [
    "peer_rank",
    "company_id",
    "peer_group_size",
    "peer_composite_percentile",
    "above_benchmark",
    "vs_benchmark_percentile",
]

ranking_columns = [
    c for c in ranking_columns
    if c in year_df.columns
]

ranking_df = year_df[
    ranking_columns
].sort_values(
    "peer_rank",
    na_position="last",
)

st.dataframe(
    ranking_df,
    use_container_width=True,
    hide_index=True,
)
