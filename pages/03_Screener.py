import streamlit as st
import pandas as pd
from pathlib import Path

from src.dashboard.style import configure_page, apply_styles


configure_page()
apply_styles()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREENER_FILE = PROJECT_ROOT / "output" / "screener_output.csv"


st.title("?? Financial Screener")
st.caption("Filter and compare NIFTY 100 companies using Sprint 3 financial screening results.")

if not SCREENER_FILE.exists():
    st.error(f"Screener output not found: {SCREENER_FILE}")
    st.stop()

df = pd.read_csv(SCREENER_FILE)

# ------------------------------------------------------------
# Sidebar filters
# ------------------------------------------------------------

st.sidebar.header("Screener Filters")

def numeric_filter(label, column, min_value=None, max_value=None, step=1.0):
    if column not in df.columns:
        return None

    series = pd.to_numeric(df[column], errors="coerce").dropna()

    if series.empty:
        return None

    actual_min = float(series.min()) if min_value is None else min_value
    actual_max = float(series.max()) if max_value is None else max_value

    if actual_min == actual_max:
        return actual_min

    return st.sidebar.slider(
        label,
        min_value=actual_min,
        max_value=actual_max,
        value=actual_min,
        step=step,
    )


# Preset screener
screeners = ["All Screeners"]

if "screener" in df.columns:
    screeners += sorted(df["screener"].dropna().unique().tolist())

selected_screener = st.sidebar.selectbox(
    "Preset Screener",
    screeners,
)

# Sector
if "broad_sector" in df.columns:
    sectors = ["All Sectors"] + sorted(
        df["broad_sector"].dropna().unique().tolist()
    )

    selected_sector = st.sidebar.selectbox(
        "Sector",
        sectors,
    )
else:
    selected_sector = "All Sectors"


# ------------------------------------------------------------
# 10 financial filters
# ------------------------------------------------------------

roe_min = numeric_filter(
    "ROE minimum (%)",
    "return_on_equity_pct",
    step=1.0,
)

de_min = None

if "debt_to_equity" in df.columns:
    de_series = pd.to_numeric(
        df["debt_to_equity"],
        errors="coerce",
    ).dropna()

    if not de_series.empty:
        de_max = st.sidebar.slider(
            "Debt / Equity maximum",
            min_value=0.0,
            max_value=max(1.0, float(de_series.max())),
            value=min(2.0, max(1.0, float(de_series.max()))),
            step=0.1,
        )
    else:
        de_max = None
else:
    de_max = None


fcf_min = numeric_filter(
    "Free Cash Flow minimum (Cr)",
    "free_cash_flow_cr",
    step=100.0,
)

revenue_cagr_min = numeric_filter(
    "Revenue CAGR 5Y minimum (%)",
    "revenue_cagr_5yr",
    step=1.0,
)

pat_cagr_min = numeric_filter(
    "PAT CAGR 5Y minimum (%)",
    "pat_cagr_5yr",
    step=1.0,
)

opm_min = numeric_filter(
    "OPM minimum (%)",
    "operating_profit_margin_pct",
    step=1.0,
)

pe_max = None

if "pe_ratio" in df.columns:
    pe_series = pd.to_numeric(
        df["pe_ratio"],
        errors="coerce",
    ).dropna()

    if not pe_series.empty:
        pe_max = st.sidebar.slider(
            "P/E maximum",
            min_value=0.0,
            max_value=max(25.0, float(pe_series.max())),
            value=min(50.0, max(25.0, float(pe_series.max()))),
            step=1.0,
        )

pb_max = None

if "pb_ratio" in df.columns:
    pb_series = pd.to_numeric(
        df["pb_ratio"],
        errors="coerce",
    ).dropna()

    if not pb_series.empty:
        pb_max = st.sidebar.slider(
            "P/B maximum",
            min_value=0.0,
            max_value=max(5.0, float(pb_series.max())),
            value=min(5.0, max(5.0, float(pb_series.max()))),
            step=0.5,
        )

dividend_min = numeric_filter(
    "Dividend Yield minimum (%)",
    "dividend_yield_pct",
    step=0.5,
)

icr_min = numeric_filter(
    "Interest Coverage minimum",
    "interest_coverage",
    step=1.0,
)

market_cap_min = numeric_filter(
    "Market Cap minimum (Cr)",
    "market_cap_crore",
    step=1000.0,
)


# ------------------------------------------------------------
# Apply filters
# ------------------------------------------------------------

filtered = df.copy()

if selected_screener != "All Screeners":
    filtered = filtered[
        filtered["screener"] == selected_screener
    ]

if selected_sector != "All Sectors":
    filtered = filtered[
        filtered["broad_sector"] == selected_sector
    ]


def apply_min_filter(frame, column, value):
    if value is not None and column in frame.columns:
        values = pd.to_numeric(
            frame[column],
            errors="coerce",
        )
        return frame[values >= value]
    return frame


def apply_max_filter(frame, column, value):
    if value is not None and column in frame.columns:
        values = pd.to_numeric(
            frame[column],
            errors="coerce",
        )
        return frame[values <= value]
    return frame


filtered = apply_min_filter(
    filtered,
    "return_on_equity_pct",
    roe_min,
)

filtered = apply_max_filter(
    filtered,
    "debt_to_equity",
    de_max,
)

filtered = apply_min_filter(
    filtered,
    "free_cash_flow_cr",
    fcf_min,
)

filtered = apply_min_filter(
    filtered,
    "revenue_cagr_5yr",
    revenue_cagr_min,
)

filtered = apply_min_filter(
    filtered,
    "pat_cagr_5yr",
    pat_cagr_min,
)

filtered = apply_min_filter(
    filtered,
    "operating_profit_margin_pct",
    opm_min,
)

filtered = apply_max_filter(
    filtered,
    "pe_ratio",
    pe_max,
)

filtered = apply_max_filter(
    filtered,
    "pb_ratio",
    pb_max,
)

filtered = apply_min_filter(
    filtered,
    "dividend_yield_pct",
    dividend_min,
)

filtered = apply_min_filter(
    filtered,
    "interest_coverage",
    icr_min,
)

filtered = apply_min_filter(
    filtered,
    "market_cap_crore",
    market_cap_min,
)


# ------------------------------------------------------------
# Results
# ------------------------------------------------------------

st.subheader("Screener Results")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Matching Rows",
        len(filtered),
    )

with col2:
    st.metric(
        "Companies",
        filtered["company_id"].nunique()
        if "company_id" in filtered.columns
        else 0,
    )

with col3:
    avg_score = (
        pd.to_numeric(
            filtered["composite_score"],
            errors="coerce",
        ).mean()
        if not filtered.empty and "composite_score" in filtered.columns
        else None
    )

    st.metric(
        "Average Composite Score",
        f"{avg_score:.1f}"
        if pd.notna(avg_score)
        else "N/A",
    )


display_columns = [
    "ranking",
    "company_id",
    "year",
    "screener",
    "broad_sector",
    "composite_score",
    "profitability_score",
    "growth_score",
    "valuation_score",
    "return_on_equity_pct",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "fcf_yield",
]

display_columns = [
    column
    for column in display_columns
    if column in filtered.columns
]

if filtered.empty:
    st.warning("No companies match the selected filters.")
else:
    st.dataframe(
        filtered[display_columns],
        use_container_width=True,
        hide_index=True,
    )

    csv_data = filtered.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="?? Download Results as CSV",
        data=csv_data,
        file_name="screener_filtered_results.csv",
        mime="text/csv",
    )
