import streamlit as st
import pandas as pd
import plotly.express as px

from src.dashboard.data_loader import load_db
from src.dashboard.style import configure_page, apply_styles

configure_page()
apply_styles()

st.title("Capital Allocation Map")
st.caption(
    "Explore how NIFTY 100 companies allocate cash through operating, "
    "investing and financing activities."
)

query = """
SELECT
    company_id,
    year,
    cfo_sign,
    cfi_sign,
    cff_sign,
    pattern_label
FROM (
    SELECT
        company_id,
        year,
        CASE
            WHEN cash_from_operations_cr > 0 THEN '+'
            WHEN cash_from_operations_cr < 0 THEN '-'
            ELSE '0'
        END AS cfo_sign,
        CASE
            WHEN capex_cr > 0 THEN '-'
            WHEN capex_cr < 0 THEN '+'
            ELSE '0'
        END AS cfi_sign,
        CASE
            WHEN total_debt_cr > 0 THEN '+'
            WHEN total_debt_cr < 0 THEN '-'
            ELSE '0'
        END AS cff_sign,
        capital_allocation_pattern AS pattern_label
    FROM financial_ratios
)
"""

df = load_db(query)

if df.empty:
    st.warning("No capital allocation data found.")
    st.stop()

df["year"] = pd.to_numeric(df["year"], errors="coerce")

years = sorted(df["year"].dropna().unique().tolist(), reverse=True)

selected_year = st.selectbox(
    "Select Year",
    years,
    index=0,
)

year_df = df[df["year"] == selected_year].copy()

if year_df.empty:
    st.warning("No data available for the selected year.")
    st.stop()

# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

pattern_counts = (
    year_df["pattern_label"]
    .fillna("Unknown")
    .value_counts()
    .reset_index()
)

pattern_counts.columns = ["pattern_label", "company_count"]

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Companies", len(year_df))

with col2:
    st.metric("Capital Patterns", year_df["pattern_label"].nunique())

with col3:
    st.metric(
        "Largest Pattern",
        pattern_counts.iloc[0]["pattern_label"]
        if not pattern_counts.empty
        else "N/A",
    )

# ---------------------------------------------------------
# Treemap
# ---------------------------------------------------------

st.subheader("Capital Allocation Treemap")

if pattern_counts.empty:
    st.info("No capital allocation patterns available.")
else:
    fig = px.treemap(
        pattern_counts,
        path=["pattern_label"],
        values="company_count",
        title=f"Companies by Capital Allocation Pattern — {int(selected_year)}",
    )

    fig.update_layout(
        height=550,
        margin=dict(l=10, r=10, t=50, b=10),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

# ---------------------------------------------------------
# Pattern drilldown
# ---------------------------------------------------------

st.subheader("Pattern Drilldown")

patterns = sorted(
    year_df["pattern_label"]
    .dropna()
    .unique()
    .tolist()
)

if patterns:
    selected_pattern = st.selectbox(
        "Select Capital Pattern",
        patterns,
    )

    pattern_df = year_df[
        year_df["pattern_label"] == selected_pattern
    ].copy()

    company_ids = pattern_df["company_id"].tolist()

    if company_ids:
        placeholders = ",".join(["?"] * len(company_ids))

        company_query = f"""
        SELECT
            id AS company_id,
            company_name
        FROM companies
        WHERE id IN ({placeholders})
        ORDER BY company_name
        """

        companies = load_db(
            company_query,
            tuple(company_ids),
        )

        pattern_df = pattern_df.merge(
            companies,
            on="company_id",
            how="left",
        )

    st.write(
        f"**{len(pattern_df)} companies** follow the "
        f"**{selected_pattern}** pattern."
    )

    display_columns = [
        "company_id",
        "company_name",
        "cfo_sign",
        "cfi_sign",
        "cff_sign",
        "pattern_label",
    ]

    available_columns = [
        col for col in display_columns
        if col in pattern_df.columns
    ]

    st.dataframe(
        pattern_df[available_columns].sort_values(
            by="company_name"
            if "company_name" in pattern_df.columns
            else "company_id"
        ),
        use_container_width=True,
        hide_index=True,
    )

# ---------------------------------------------------------
# Full data
# ---------------------------------------------------------

with st.expander("View Capital Allocation Data"):
    st.dataframe(
        year_df.sort_values("company_id"),
        use_container_width=True,
        hide_index=True,
    )
