import streamlit as st
import pandas as pd

from src.dashboard.data_loader import load_db
from src.dashboard.style import configure_page, apply_styles

configure_page()
apply_styles()

st.title("Annual Reports")
st.caption(
    "Browse the NIFTY 100 annual-report repository by company and year."
)

query = """
SELECT
    d.company_id,
    c.company_name,
    d.year,
    d.annual_report
FROM documents d
LEFT JOIN companies c
    ON d.company_id = c.id
ORDER BY c.company_name, d.year DESC
"""

df = load_db(query)

if df.empty:
    st.warning("No annual reports found in the database.")
    st.stop()

df["year"] = pd.to_numeric(df["year"], errors="coerce")

# ---------------------------------------------------------
# Filters
# ---------------------------------------------------------

companies = (
    df[["company_id", "company_name"]]
    .drop_duplicates()
    .sort_values("company_name")
)

company_options = ["All Companies"] + companies["company_id"].tolist()

selected_company = st.selectbox(
    "Select Company",
    company_options,
)

if selected_company != "All Companies":
    filtered_df = df[
        df["company_id"] == selected_company
    ].copy()
else:
    filtered_df = df.copy()

years = sorted(
    filtered_df["year"].dropna().unique().tolist(),
    reverse=True,
)

year_options = ["All Years"] + [int(year) for year in years]

selected_year = st.selectbox(
    "Select Year",
    year_options,
)

if selected_year != "All Years":
    filtered_df = filtered_df[
        filtered_df["year"] == selected_year
    ].copy()

# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Reports Available",
        len(filtered_df),
    )

with col2:
    st.metric(
        "Companies",
        filtered_df["company_id"].nunique(),
    )

with col3:
    st.metric(
        "Years Covered",
        filtered_df["year"].nunique(),
    )

# ---------------------------------------------------------
# Report repository
# ---------------------------------------------------------

st.subheader("Annual Report Repository")

display_df = filtered_df[
    [
        "company_id",
        "company_name",
        "year",
        "annual_report",
    ]
].copy()

display_df["annual_report"] = display_df["annual_report"].fillna("")

# Use clickable report links where URLs exist.
for _, row in display_df.iterrows():
    company_name = row["company_name"] or row["company_id"]
    year = (
        int(row["year"])
        if pd.notna(row["year"])
        else "N/A"
    )
    report_url = str(row["annual_report"]).strip()

    st.markdown(
        f"### {company_name} — {year}"
    )

    if report_url:
        st.markdown(
            f"[Open Annual Report]({report_url})"
        )
    else:
        st.caption("Annual report link not available.")

    st.divider()

# ---------------------------------------------------------
# Table view
# ---------------------------------------------------------

with st.expander("View Repository Table"):
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )
