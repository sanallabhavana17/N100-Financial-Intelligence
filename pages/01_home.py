import streamlit as st
import pandas as pd
import plotly.express as px

from src.dashboard.utils.db import (
    get_companies,
    get_ratios,
    get_valuation,
    get_sectors,
    get_years,
)

st.title("Nifty 100 Financial Intelligence")
st.caption("Financial overview of the Nifty 100 universe")

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------

companies = get_companies()
sectors = get_sectors()

years_df = get_years()

available_years = sorted(
    [int(y) for y in years_df["year"].dropna().tolist()]
)

# Official Sprint 4 selector: 2019–2024
dashboard_years = [
    y for y in range(2019, 2025)
    if y in available_years
]

if not dashboard_years:
    dashboard_years = available_years[-6:]

selected_year = st.sidebar.selectbox(
    "Analysis Year",
    dashboard_years,
    index=len(dashboard_years) - 1,
)

# ------------------------------------------------------------
# RATIOS
# ------------------------------------------------------------

ratio_frames = []

for ticker in companies["company_id"].dropna().unique():
    df = get_ratios(ticker, selected_year)

    if not df.empty:
        ratio_frames.append(df)

if ratio_frames:
    ratios = pd.concat(ratio_frames, ignore_index=True)
else:
    ratios = pd.DataFrame()

# ------------------------------------------------------------
# VALUATION
# ------------------------------------------------------------

valuation_frames = []

for ticker in companies["company_id"].dropna().unique():
    df = get_valuation(ticker)

    if not df.empty:
        df = df[df["year"] == selected_year]

        if not df.empty:
            valuation_frames.append(df)

if valuation_frames:
    valuations = pd.concat(
        valuation_frames,
        ignore_index=True
    )
else:
    valuations = pd.DataFrame()

# ------------------------------------------------------------
# KPI HELPERS
# ------------------------------------------------------------

def numeric_series(df, column):
    if df.empty or column not in df.columns:
        return pd.Series(dtype="float64")

    return pd.to_numeric(
        df[column],
        errors="coerce"
    ).dropna()


roe = numeric_series(
    ratios,
    "return_on_equity_pct"
)

de = numeric_series(
    ratios,
    "debt_to_equity"
)

revenue_cagr5 = numeric_series(
    ratios,
    "revenue_cagr_5yr"
)

pe = numeric_series(
    valuations,
    "pe_ratio"
)

# ------------------------------------------------------------
# SIX KPI TILES
# ------------------------------------------------------------

k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.metric(
        "Average ROE",
        f"{roe.mean():.2f}%" if not roe.empty else "N/A"
    )

with k2:
    st.metric(
        "Median P/E",
        f"{pe.median():.2f}" if not pe.empty else "N/A"
    )

with k3:
    st.metric(
        "Median D/E",
        f"{de.median():.2f}" if not de.empty else "N/A"
    )

with k4:
    st.metric(
        "Total Companies",
        f"{len(companies):,}"
    )

with k5:
    st.metric(
        "Median Revenue CAGR5",
        f"{revenue_cagr5.median():.2f}%"
        if not revenue_cagr5.empty
        else "N/A"
    )

with k6:
    debt_free = 0

    if not ratios.empty and "debt_to_equity" in ratios.columns:
        debt_values = pd.to_numeric(
            ratios["debt_to_equity"],
            errors="coerce"
        )

        debt_free = int(
            (debt_values.fillna(float("inf")) == 0).sum()
        )

    st.metric(
        "Debt-Free Companies",
        f"{debt_free:,}"
    )

# ------------------------------------------------------------
# SECTOR DONUT
# ------------------------------------------------------------

st.divider()

left, right = st.columns([1.2, 1])

with left:
    st.subheader("Nifty 100 Sector Distribution")

    sector_counts = (
        sectors.groupby("broad_sector")["company_id"]
        .nunique()
        .reset_index(name="companies")
        .sort_values("companies", ascending=False)
    )

    if not sector_counts.empty:
        fig = px.pie(
            sector_counts,
            names="broad_sector",
            values="companies",
            hole=0.55,
        )

        fig.update_layout(
            margin=dict(l=10, r=10, t=30, b=10),
            legend_title_text="Sector",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )
    else:
        st.info("Sector data unavailable.")

# ------------------------------------------------------------
# TOP 5 COMPOSITE SCORE
# ------------------------------------------------------------

with right:
    st.subheader("Top 5 Composite Scores")

    if not ratios.empty and "composite_quality_score" in ratios.columns:

        score_df = ratios.copy()

        score_df["composite_quality_score"] = pd.to_numeric(
            score_df["composite_quality_score"],
            errors="coerce",
        )

        score_df = (
            score_df[
                [
                    "company_id",
                    "composite_quality_score",
                ]
            ]
            .dropna()
            .sort_values(
                "composite_quality_score",
                ascending=False,
            )
            .drop_duplicates("company_id")
            .head(5)
        )

        score_df = score_df.merge(
            companies[
                [
                    "company_id",
                    "company_name",
                    "sector",
                ]
            ],
            on="company_id",
            how="left",
        )

        score_df = score_df[
            [
                "company_name",
                "sector",
                "composite_quality_score",
            ]
        ]

        score_df.columns = [
            "Company",
            "Sector",
            "Score",
        ]

        st.dataframe(
            score_df,
            hide_index=True,
            use_container_width=True,
        )

    else:
        st.info("Composite score data unavailable.")

# ------------------------------------------------------------
# DATA NOTE
# ------------------------------------------------------------

st.caption(
    f"Dashboard year: {selected_year} • "
    f"Companies in universe: {len(companies)}"
)
