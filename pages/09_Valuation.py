import streamlit as st
import pandas as pd
import plotly.express as px

from pathlib import Path

from src.dashboard.style import configure_page, apply_styles


configure_page()
apply_styles()

st.title("Valuation")
st.caption(
    "Compare current valuation multiples with historical and sector benchmarks."
)

OUTPUT_DIR = Path("output")
SUMMARY_PATH = OUTPUT_DIR / "valuation_summary.xlsx"
FLAGS_PATH = OUTPUT_DIR / "valuation_flags.csv"


if not SUMMARY_PATH.exists():
    st.error("valuation_summary.xlsx was not found. Run the valuation engine first.")
    st.stop()

df = pd.read_excel(SUMMARY_PATH)

if df.empty:
    st.warning("No valuation data available.")
    st.stop()


# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------

st.sidebar.header("Valuation Filters")

badge_options = ["All"] + sorted(
    df["valuation_badge"].dropna().unique().tolist()
)

selected_badge = st.sidebar.selectbox(
    "Valuation Status",
    badge_options,
)

sector_options = ["All"] + sorted(
    df["broad_sector"].dropna().unique().tolist()
)

selected_sector = st.sidebar.selectbox(
    "Sector",
    sector_options,
)


filtered_df = df.copy()

if selected_badge != "All":
    filtered_df = filtered_df[
        filtered_df["valuation_badge"] == selected_badge
    ]

if selected_sector != "All":
    filtered_df = filtered_df[
        filtered_df["broad_sector"] == selected_sector
    ]


# ---------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Companies",
        len(filtered_df),
    )

with col2:
    st.metric(
        "Caution",
        int(
            (filtered_df["valuation_badge"] == "Caution").sum()
        ),
    )

with col3:
    st.metric(
        "Discount",
        int(
            (filtered_df["valuation_badge"] == "Discount").sum()
        ),
    )

with col4:
    st.metric(
        "Neutral",
        int(
            (filtered_df["valuation_badge"] == "Neutral").sum()
        ),
    )


# ---------------------------------------------------------
# Valuation distribution
# ---------------------------------------------------------

st.subheader("Valuation Status")

badge_counts = (
    filtered_df["valuation_badge"]
    .value_counts()
    .reset_index()
)

badge_counts.columns = [
    "valuation_badge",
    "company_count",
]

if not badge_counts.empty:
    fig = px.bar(
        badge_counts,
        x="valuation_badge",
        y="company_count",
        text="company_count",
        title="Companies by Valuation Status",
    )

    fig.update_layout(
        height=400,
        margin=dict(l=10, r=10, t=50, b=10),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ---------------------------------------------------------
# P/E comparison
# ---------------------------------------------------------

st.subheader("Current P/E vs 5-Year Median")

pe_df = filtered_df[
    [
        "company_name",
        "current_pe",
        "pe_5yr_median",
        "sector_median_pe",
        "valuation_badge",
    ]
].copy()

pe_long = pe_df.melt(
    id_vars=[
        "company_name",
        "valuation_badge",
    ],
    value_vars=[
        "current_pe",
        "pe_5yr_median",
        "sector_median_pe",
    ],
    var_name="benchmark",
    value_name="pe_ratio",
)

pe_long["benchmark"] = pe_long["benchmark"].replace(
    {
        "current_pe": "Current P/E",
        "pe_5yr_median": "5Y Median P/E",
        "sector_median_pe": "Sector Median P/E",
    }
)

fig_pe = px.bar(
    pe_long,
    x="company_name",
    y="pe_ratio",
    color="benchmark",
    barmode="group",
    title="P/E Benchmark Comparison",
)

fig_pe.update_layout(
    height=550,
    xaxis_tickangle=-45,
    margin=dict(l=10, r=10, t=50, b=10),
)

st.plotly_chart(
    fig_pe,
    use_container_width=True,
)


# ---------------------------------------------------------
# FCF Yield
# ---------------------------------------------------------

st.subheader("FCF Yield")

fcf_df = filtered_df[
    [
        "company_name",
        "fcf_yield_pct",
        "current_market_cap_crore",
        "current_fcf_cr",
    ]
].copy()

fcf_df = fcf_df.sort_values(
    "fcf_yield_pct",
    ascending=False,
)

fig_fcf = px.bar(
    fcf_df.head(20),
    x="company_name",
    y="fcf_yield_pct",
    title="Top 20 Companies by FCF Yield",
)

fig_fcf.update_layout(
    height=500,
    xaxis_tickangle=-45,
    margin=dict(l=10, r=10, t=50, b=10),
)

st.plotly_chart(
    fig_fcf,
    use_container_width=True,
)


# ---------------------------------------------------------
# Dividend Yield Ranker
# ---------------------------------------------------------

st.subheader("Dividend Yield Ranker")

dividend_df = filtered_df[
    [
        "company_name",
        "broad_sector",
        "current_dividend_yield_pct",
        "dividend_yield_rank",
    ]
].copy()

dividend_df = dividend_df.sort_values(
    "dividend_yield_rank"
)

st.dataframe(
    dividend_df,
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# Main valuation table
# ---------------------------------------------------------

st.subheader("Valuation Summary")

display_columns = [
    "company_id",
    "company_name",
    "broad_sector",
    "current_year",
    "current_pe",
    "pe_5yr_median",
    "sector_median_pe",
    "current_pb",
    "pb_5yr_median",
    "current_ev_ebitda",
    "ev_ebitda_5yr_median",
    "fcf_yield_pct",
    "current_dividend_yield_pct",
    "valuation_badge",
    "valuation_rationale",
]

display_columns = [
    column
    for column in display_columns
    if column in filtered_df.columns
]

st.dataframe(
    filtered_df[display_columns].sort_values(
        "company_name"
    ),
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# Downloads
# ---------------------------------------------------------

st.subheader("Download Valuation Data")

col1, col2 = st.columns(2)

with col1:
    st.download_button(
        label="Download Valuation Summary",
        data=SUMMARY_PATH.read_bytes(),
        file_name="valuation_summary.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )

with col2:
    if FLAGS_PATH.exists():
        st.download_button(
            label="Download Valuation Flags",
            data=FLAGS_PATH.read_bytes(),
            file_name="valuation_flags.csv",
            mime="text/csv",
        )
