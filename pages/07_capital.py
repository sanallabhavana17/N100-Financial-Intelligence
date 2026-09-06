import streamlit as st
import pandas as pd
import plotly.express as px

from src.dashboard.data_loader import load_db
from src.dashboard.style import configure_page, apply_styles


# ============================================================
# PAGE SETUP
# ============================================================

configure_page()
apply_styles()

st.title("Capital Allocation Map")

st.caption(
    "Explore how NIFTY 100 companies allocate cash through "
    "operating, investing and financing activities."
)


# ============================================================
# LOAD COMPANY MASTER
# ============================================================

companies = load_db(
    """
    SELECT
        id AS company_id,
        company_name
    FROM companies
    ORDER BY company_name
    """
)

if companies.empty:
    st.warning("No companies found in the database.")
    st.stop()

companies["company_id"] = (
    companies["company_id"]
    .astype(str)
    .str.strip()
)


# ============================================================
# LOAD FINANCIAL RATIO CAPITAL PATTERNS
# ============================================================

ratio_df = load_db(
    """
    SELECT
        company_id,
        year,
        capital_allocation_pattern,
        cash_from_operations_cr,
        capex_cr,
        total_debt_cr
    FROM financial_ratios
    ORDER BY company_id, year
    """
)

if ratio_df.empty:
    st.warning(
        "No capital allocation data was found."
    )
    st.stop()


ratio_df["company_id"] = (
    ratio_df["company_id"]
    .astype(str)
    .str.strip()
)

ratio_df["year"] = pd.to_numeric(
    ratio_df["year"],
    errors="coerce",
)

ratio_df["capital_allocation_pattern"] = (
    ratio_df["capital_allocation_pattern"]
    .astype(str)
    .str.strip()
)

# Convert empty strings and textual nulls to actual missing values.
ratio_df["capital_allocation_pattern"] = (
    ratio_df["capital_allocation_pattern"]
    .replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "None": pd.NA,
            "NULL": pd.NA,
            "null": pd.NA,
        }
    )
)


# ============================================================
# LOAD ACTUAL CASH FLOW DATA
# ============================================================

cashflow_df = load_db(
    """
    SELECT
        company_id,
        year,
        operating_activity,
        investing_activity,
        financing_activity
    FROM cashflow
    ORDER BY company_id, year
    """
)

if not cashflow_df.empty:

    cashflow_df["company_id"] = (
        cashflow_df["company_id"]
        .astype(str)
        .str.strip()
    )

    cashflow_df["year"] = pd.to_numeric(
        cashflow_df["year"],
        errors="coerce",
    )

    for column in [
        "operating_activity",
        "investing_activity",
        "financing_activity",
    ]:

        cashflow_df[column] = pd.to_numeric(
            cashflow_df[column],
            errors="coerce",
        )


# ============================================================
# HELPER: SIGN
# ============================================================

def sign_value(value):

    if pd.isna(value):
        return "0"

    try:
        number = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return "0"

    if number > 0:
        return "+"

    if number < 0:
        return "-"

    return "0"


# ============================================================
# PREPARE CAPITAL ALLOCATION DATA
# ============================================================

df = ratio_df.copy()


# ------------------------------------------------------------
# Join actual cash-flow information
# ------------------------------------------------------------

if not cashflow_df.empty:

    df = df.merge(
        cashflow_df,
        on=[
            "company_id",
            "year",
        ],
        how="left",
        suffixes=(
            "",
            "_cashflow",
        ),
    )


# ============================================================
# DERIVE CASH FLOW SIGNS
# ============================================================

# CFO = operating cash flow
if "operating_activity" in df.columns:

    df["cfo_sign"] = df[
        "operating_activity"
    ].apply(sign_value)

else:

    df["cfo_sign"] = df[
        "cash_from_operations_cr"
    ].apply(sign_value)


# CFI = investing cash flow
if "investing_activity" in df.columns:

    df["cfi_sign"] = df[
        "investing_activity"
    ].apply(sign_value)

else:

    df["cfi_sign"] = df[
        "capex_cr"
    ].apply(
        lambda value:
        "-"
        if pd.notna(value)
        and float(value) > 0
        else (
            "+"
            if pd.notna(value)
            and float(value) < 0
            else "0"
        )
    )


# CFF = financing cash flow
if "financing_activity" in df.columns:

    df["cff_sign"] = df[
        "financing_activity"
    ].apply(sign_value)

else:

    df["cff_sign"] = df[
        "total_debt_cr"
    ].apply(sign_value)


# ============================================================
# NORMALIZE EXISTING PATTERN LABELS
# ============================================================

def normalize_pattern(value):

    if pd.isna(value):
        return None

    value = str(value).strip()

    if not value:
        return None

    # Normalize common separators.
    value = (
        value
        .replace(" ", "")
        .replace("(", "")
        .replace(")", "")
        .replace(",", "")
        .replace("→", "")
        .replace(">", "")
    )

    return value


df["stored_pattern"] = (
    df["capital_allocation_pattern"]
    .apply(normalize_pattern)
)


# ============================================================
# CREATE STANDARD PATTERN
# ============================================================

df["derived_pattern"] = (
    "CFO "
    + df["cfo_sign"]
    + " | CFI "
    + df["cfi_sign"]
    + " | CFF "
    + df["cff_sign"]
)


# ============================================================
# USE STORED PATTERN WHEN AVAILABLE
# OTHERWISE DERIVE FROM CASH FLOW
# ============================================================

df["pattern_label"] = (
    df["capital_allocation_pattern"]
    .where(
        df["capital_allocation_pattern"].notna()
        & (
            df[
                "capital_allocation_pattern"
            ].astype(str).str.strip() != ""
        )
    )
)


df["pattern_label"] = (
    df["pattern_label"]
    .fillna(
        df["derived_pattern"]
    )
)


df["pattern_label"] = (
    df["pattern_label"]
    .astype(str)
    .str.strip()
)


# ============================================================
# REMOVE INVALID YEARS
# ============================================================

df = df[
    df["year"].notna()
].copy()

df["year"] = df[
    "year"
].astype(int)


if df.empty:
    st.warning(
        "No valid yearly capital allocation records found."
    )
    st.stop()


# ============================================================
# YEAR SELECTOR
# ============================================================

years = sorted(
    df["year"]
    .dropna()
    .unique()
    .tolist(),
    reverse=True,
)


selected_year = st.selectbox(
    "Select Year",
    years,
    index=0,
)


# ============================================================
# SELECT LATEST RECORD PER COMPANY FOR YEAR
# ============================================================

year_df = df[
    df["year"] == selected_year
].copy()


# Remove duplicate records for the same company.
year_df = (
    year_df
    .sort_values(
        [
            "company_id",
            "year",
        ]
    )
    .drop_duplicates(
        subset=[
            "company_id"
        ],
        keep="last",
    )
)


# ============================================================
# ADD COMPANY NAMES
# ============================================================

year_df = year_df.merge(
    companies,
    on="company_id",
    how="left",
)


# ============================================================
# SUMMARY
# ============================================================

pattern_counts = (
    year_df[
        "pattern_label"
    ]
    .fillna("Unknown")
    .value_counts()
    .reset_index()
)

pattern_counts.columns = [
    "pattern_label",
    "company_count",
]


# Remove impossible zero-count records.
pattern_counts = pattern_counts[
    pattern_counts[
        "company_count"
    ] > 0
].copy()


# ============================================================
# SUMMARY KPI
# ============================================================

col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Companies",
        year_df[
            "company_id"
        ].nunique(),
    )


with col2:

    st.metric(
        "Capital Patterns",
        8,
    )


with col3:

    if not pattern_counts.empty:

        largest_pattern = (
            pattern_counts.iloc[0][
                "pattern_label"
            ]
        )

    else:

        largest_pattern = "N/A"

    st.metric(
        "Largest Pattern",
        largest_pattern,
    )


with col4:

    st.metric(
        "Patterns in Use",
        len(pattern_counts),
    )


# ============================================================
# TREEMAP
# ============================================================

st.subheader(
    "Capital Allocation Treemap"
)

if pattern_counts.empty:

    st.warning(
        "No capital allocation patterns are available "
        f"for {int(selected_year)}."
    )

else:

    fig = px.treemap(
        pattern_counts,
        path=[
            "pattern_label"
        ],
        values="company_count",
        title=(
            "Eight Capital Allocation Patterns — "
            f"{int(selected_year)}"
        ),
    )

    fig.update_traces(
        textinfo="label+value+percent parent",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Companies: %{value}<br>"
            "Share: %{percentParent:.1%}"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        height=550,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ============================================================
# PATTERN SUMMARY TABLE
# ============================================================

st.subheader(
    "Pattern Summary"
)

if not pattern_counts.empty:

    pattern_summary = pattern_counts.copy()

    pattern_summary[
        "percentage"
    ] = (
        pattern_summary[
            "company_count"
        ]
        / pattern_summary[
            "company_count"
        ].sum()
        * 100
    )

    pattern_summary = (
        pattern_summary
        .rename(
            columns={
                "pattern_label":
                    "Capital Allocation Pattern",
                "company_count":
                    "Companies",
                "percentage":
                    "Coverage (%)",
            }
        )
    )

    pattern_summary[
        "Coverage (%)"
    ] = pattern_summary[
        "Coverage (%)"
    ].round(2)

    st.dataframe(
        pattern_summary,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.info(
        "No pattern summary is available."
    )


# ============================================================
# PATTERN DRILLDOWN
# ============================================================

st.divider()

st.subheader(
    "Pattern Drilldown"
)


patterns = sorted(
    year_df[
        "pattern_label"
    ]
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
        year_df[
            "pattern_label"
        ] == selected_pattern
    ].copy()


    st.write(
        f"**{len(pattern_df)} companies** follow "
        f"the **{selected_pattern}** pattern."
    )


    display_columns = [
        "company_id",
        "company_name",
        "year",
        "cfo_sign",
        "cfi_sign",
        "cff_sign",
        "pattern_label",
    ]


    display_columns = [
        column
        for column in display_columns
        if column in pattern_df.columns
    ]


    display_df = pattern_df[
        display_columns
    ].copy()


    display_df = display_df.sort_values(
        by=(
            "company_name"
            if "company_name"
            in display_df.columns
            else "company_id"
        )
    )


    display_df = display_df.rename(
        columns={
            "company_id":
                "Company ID",
            "company_name":
                "Company Name",
            "year":
                "Year",
            "cfo_sign":
                "CFO",
            "cfi_sign":
                "CFI",
            "cff_sign":
                "CFF",
            "pattern_label":
                "Capital Allocation Pattern",
        }
    )


    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.info(
        "No capital allocation patterns are available "
        "for this year."
    )


# ============================================================
# CAPITAL ALLOCATION LEGEND
# ============================================================

st.divider()

st.subheader(
    "Capital Allocation Pattern Legend"
)


legend = pd.DataFrame(
    [
        [
            "+ | + | +",
            "Positive operating, investing and financing cash flow",
        ],
        [
            "+ | + | -",
            "Positive operating and investing cash flow; financing outflow",
        ],
        [
            "+ | - | +",
            "Operating inflow, investing outflow and financing inflow",
        ],
        [
            "+ | - | -",
            "Operating inflow with investing and financing outflows",
        ],
        [
            "- | + | +",
            "Operating outflow with investing and financing inflows",
        ],
        [
            "- | + | -",
            "Operating outflow, investing inflow and financing outflow",
        ],
        [
            "- | - | +",
            "Operating and investing outflows with financing inflow",
        ],
        [
            "- | - | -",
            "Negative operating, investing and financing cash flow",
        ],
    ],
    columns=[
        "Pattern",
        "Meaning",
    ],
)


st.dataframe(
    legend,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# FULL DATA
# ============================================================

with st.expander(
    "View Capital Allocation Data"
):

    full_display = year_df.copy()

    full_display = full_display[
        [
            column
            for column in [
                "company_id",
                "company_name",
                "year",
                "cfo_sign",
                "cfi_sign",
                "cff_sign",
                "pattern_label",
            ]
            if column in full_display.columns
        ]
    ]

    st.dataframe(
        full_display.sort_values(
            "company_name"
        ),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# FOOTNOTE
# ============================================================

st.caption(
    "Capital allocation patterns classify companies using "
    "the signs of operating, investing and financing cash flows. "
    "Historical coverage may vary by company and year."
)