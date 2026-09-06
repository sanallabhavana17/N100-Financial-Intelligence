import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.dashboard.data_loader import load_db
from src.dashboard.style import configure_page, apply_styles


# ============================================================
# PAGE SETUP
# ============================================================

configure_page()
apply_styles()

st.title("Trend Analysis")
st.caption(
    "Explore up to three financial metrics across the latest "
    "10 available years for a NIFTY 100 company."
)


# ============================================================
# COMPANY LIST
# ============================================================

companies = load_db(
    """
    SELECT
        id,
        company_name
    FROM companies
    ORDER BY company_name
    """
)

if companies.empty:
    st.warning("No companies found in the database.")
    st.stop()

companies["id"] = companies["id"].astype(str)

company_labels = dict(
    zip(
        companies["id"],
        companies["company_name"],
    )
)

company_ids = companies["id"].tolist()


selected_company = st.sidebar.selectbox(
    "Search / Select Company",
    company_ids,
    format_func=lambda x: company_labels.get(x, x),
)


# ============================================================
# METRIC DEFINITIONS
# ============================================================

metric_definitions = {
    "Revenue": {
        "table": "profitandloss",
        "column": "sales",
        "unit": "₹ Cr",
    },
    "Net Profit": {
        "table": "profitandloss",
        "column": "net_profit",
        "unit": "₹ Cr",
    },
    "EPS": {
        "table": "profitandloss",
        "column": "eps",
        "unit": "₹",
    },
    "ROE": {
        "table": "financial_ratios",
        "column": "return_on_equity_pct",
        "unit": "%",
    },
    "ROCE": {
        "table": "financial_ratios",
        "column": "return_on_capital_employed_pct",
        "unit": "%",
    },
    "ROA": {
        "table": "financial_ratios",
        "column": "return_on_assets_pct",
        "unit": "%",
    },
    "Net Profit Margin": {
        "table": "financial_ratios",
        "column": "net_profit_margin_pct",
        "unit": "%",
    },
    "Operating Profit Margin": {
        "table": "financial_ratios",
        "column": "operating_profit_margin_pct",
        "unit": "%",
    },
    "Debt to Equity": {
        "table": "financial_ratios",
        "column": "debt_to_equity",
        "unit": "x",
    },
    "Interest Coverage": {
        "table": "financial_ratios",
        "column": "interest_coverage",
        "unit": "x",
    },
    "Free Cash Flow": {
        "table": "financial_ratios",
        "column": "free_cash_flow_cr",
        "unit": "₹ Cr",
    },
    "Asset Turnover": {
        "table": "financial_ratios",
        "column": "asset_turnover",
        "unit": "x",
    },
    "Dividend Payout": {
        "table": "financial_ratios",
        "column": "dividend_payout_ratio_pct",
        "unit": "%",
    },
}


metric_options = list(metric_definitions.keys())


# ============================================================
# METRIC SELECTION - MAXIMUM 3
# ============================================================

selected_metrics = st.sidebar.multiselect(
    "Metrics (select up to 3)",
    metric_options,
    default=["Revenue"],
    max_selections=3,
)

if not selected_metrics:
    st.info("Select at least one metric from the sidebar.")
    st.stop()


# ============================================================
# LOAD METRIC DATA
# ============================================================

def load_metric(metric_name):
    """
    Load the complete historical series for one metric.

    The full history is loaded first so that CAGR calculations
    can use older observations. The chart itself is limited to
    the latest 10 available years.
    """

    definition = metric_definitions[metric_name]

    table = definition["table"]
    column = definition["column"]

    query = f"""
        SELECT
            year,
            {column} AS metric_value
        FROM {table}
        WHERE company_id = ?
        ORDER BY year
    """

    data = load_db(
        query,
        (selected_company,),
    )

    if data.empty:
        return pd.DataFrame(
            columns=[
                "year",
                "metric_value",
            ]
        )

    data["year"] = pd.to_numeric(
        data["year"],
        errors="coerce",
    )

    data["metric_value"] = pd.to_numeric(
        data["metric_value"],
        errors="coerce",
    )

    data = data.dropna(
        subset=[
            "year",
            "metric_value",
        ]
    )

    if data.empty:
        return pd.DataFrame(
            columns=[
                "year",
                "metric_value",
            ]
        )

    data["year"] = data["year"].astype(int)

    # Remove duplicate years if any exist.
    data = (
        data
        .drop_duplicates(
            subset=["year"],
            keep="last",
        )
        .sort_values("year")
        .reset_index(drop=True)
    )

    return data


# ============================================================
# LOAD ALL SELECTED METRICS
# ============================================================

metric_full_data = {}
metric_chart_data = {}

for metric in selected_metrics:

    full_data = load_metric(metric)

    if full_data.empty:
        continue

    metric_full_data[metric] = full_data

    # Chart uses latest 10 available years.
    chart_data = full_data.tail(10).copy()

    metric_chart_data[metric] = chart_data


if not metric_full_data:
    st.warning(
        f"No historical data available for "
        f"{company_labels.get(selected_company, selected_company)}."
    )
    st.stop()


# ============================================================
# COMPANY HEADING
# ============================================================

company_name = company_labels.get(
    selected_company,
    selected_company,
)

st.subheader(
    f"{company_name} — Financial Trends"
)

st.caption(
    f"Showing the latest 10 available years for "
    f"{len(metric_chart_data)} selected metric(s)."
)


# ============================================================
# HELPER: CAGR
# ============================================================

def calculate_cagr(dataframe, years):
    """
    Calculate CAGR using the latest available value and the
    closest available observation at least `years` years earlier.

    This works even when some financial years are missing.
    """

    if dataframe.empty:
        return None

    data = (
        dataframe[
            ["year", "metric_value"]
        ]
        .dropna()
        .sort_values("year")
        .reset_index(drop=True)
    )

    if len(data) < 2:
        return None

    latest_row = data.iloc[-1]

    latest_year = int(
        latest_row["year"]
    )

    latest_value = float(
        latest_row["metric_value"]
    )

    target_year = latest_year - years

    # Find the latest observation at or before the target year.
    eligible = data[
        data["year"] <= target_year
    ]

    if eligible.empty:
        return None

    start_row = eligible.iloc[-1]

    start_year = int(
        start_row["year"]
    )

    start_value = float(
        start_row["metric_value"]
    )

    actual_years = (
        latest_year - start_year
    )

    if actual_years <= 0:
        return None

    # CAGR is not meaningful when either endpoint is
    # non-positive.
    if start_value <= 0 or latest_value <= 0:
        return None

    try:
        cagr = (
            (
                latest_value / start_value
            )
            ** (1 / actual_years)
            - 1
        ) * 100

        return cagr

    except (
        ValueError,
        ZeroDivisionError,
        OverflowError,
    ):
        return None


# ============================================================
# TREND CHARTS
# ============================================================

st.markdown("## Historical Trends")

for metric, data in metric_chart_data.items():

    definition = metric_definitions[metric]

    unit = definition["unit"]

    chart_data = data.copy()

    # --------------------------------------------------------
    # Calculate YoY %
    # --------------------------------------------------------

    chart_data["yoy_pct"] = (
        chart_data["metric_value"]
        .pct_change()
        .mul(100)
    )

    # --------------------------------------------------------
    # Create chart annotations
    # --------------------------------------------------------

    annotations = []

    for value, yoy in zip(
        chart_data["metric_value"],
        chart_data["yoy_pct"],
    ):

        value_text = f"{value:,.2f}"

        if pd.isna(yoy):
            annotation = value_text
        else:
            annotation = (
                f"{value_text}"
                f"<br>"
                f"YoY: {yoy:+.1f}%"
            )

        annotations.append(annotation)

    # --------------------------------------------------------
    # Plotly chart
    # --------------------------------------------------------

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=chart_data["year"],
            y=chart_data["metric_value"],
            mode="lines+markers+text",
            text=annotations,
            textposition="top center",
            name=metric,
            customdata=chart_data[
                ["yoy_pct"]
            ].fillna(float("nan")),
            hovertemplate=(
                "<b>Year:</b> %{x}<br>"
                f"<b>{metric}:</b> "
                "%{y:,.2f} "
                f"{unit}<br>"
                "<b>YoY:</b> "
                "%{customdata[0]:+.2f}%"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        height=450,
        xaxis_title="Year",
        yaxis_title=f"{metric} ({unit})",
        margin=dict(
            l=30,
            r=30,
            t=50,
            b=30,
        ),
        hovermode="x unified",
    )

    fig.update_xaxes(
        dtick=1,
    )

    st.markdown(
        f"### {metric}"
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ============================================================
# YOY TABLES
# ============================================================

st.divider()

st.subheader("Year-over-Year Growth")

for metric, data in metric_chart_data.items():

    definition = metric_definitions[metric]

    unit = definition["unit"]

    yoy_data = data.copy()

    yoy_data["YoY %"] = (
        yoy_data["metric_value"]
        .pct_change()
        .mul(100)
    )

    yoy_display = yoy_data[
        [
            "year",
            "metric_value",
            "YoY %",
        ]
    ].copy()

    yoy_display.columns = [
        "Year",
        f"{metric} ({unit})",
        "YoY %",
    ]

    yoy_display[
        f"{metric} ({unit})"
    ] = yoy_display[
        f"{metric} ({unit})"
    ].round(2)

    yoy_display["YoY %"] = (
        yoy_display["YoY %"]
        .round(2)
    )

    # Format numbers while preserving N/A.
    value_column = f"{metric} ({unit})"

    yoy_display[value_column] = (
        yoy_display[value_column]
        .apply(
            lambda x:
            f"{x:,.2f}"
            if pd.notna(x)
            else "N/A"
        )
    )

    yoy_display["YoY %"] = (
        yoy_display["YoY %"]
        .apply(
            lambda x:
            f"{x:+.2f}%"
            if pd.notna(x)
            else "N/A"
        )
    )

    st.markdown(
        f"**{metric}**"
    )

    st.dataframe(
        yoy_display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# CAGR SUMMARY
# ============================================================

st.divider()

st.subheader("Growth Summary")

for metric, data in metric_full_data.items():

    cagr_3 = calculate_cagr(
        data,
        3,
    )

    cagr_5 = calculate_cagr(
        data,
        5,
    )

    cagr_10 = calculate_cagr(
        data,
        10,
    )

    st.markdown(
        f"**{metric}**"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "3Y CAGR",
            (
                f"{cagr_3:.2f}%"
                if cagr_3 is not None
                else "N/A"
            ),
        )

    with c2:

        st.metric(
            "5Y CAGR",
            (
                f"{cagr_5:.2f}%"
                if cagr_5 is not None
                else "N/A"
            ),
        )

    with c3:

        st.metric(
            "10Y CAGR",
            (
                f"{cagr_10:.2f}%"
                if cagr_10 is not None
                else "N/A"
            ),
        )


# ============================================================
# DATA COVERAGE NOTE
# ============================================================

st.divider()

st.subheader("Data Coverage")

coverage_rows = []

for metric, data in metric_full_data.items():

    first_year = (
        int(data["year"].min())
        if not data.empty
        else None
    )

    last_year = (
        int(data["year"].max())
        if not data.empty
        else None
    )

    available_years = len(data)

    coverage_rows.append(
        {
            "Metric": metric,
            "First Year": (
                first_year
                if first_year is not None
                else "N/A"
            ),
            "Latest Year": (
                last_year
                if last_year is not None
                else "N/A"
            ),
            "Available Years": available_years,
            "Status": (
                "Full / 10+ years"
                if available_years >= 10
                else "Partial data"
            ),
        }
    )

coverage_df = pd.DataFrame(
    coverage_rows
)

st.dataframe(
    coverage_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# PARTIAL DATA MESSAGE
# ============================================================

partial_metrics = [
    metric
    for metric, data in metric_full_data.items()
    if len(data) < 10
]

if partial_metrics:

    st.info(
        "Partial historical data is available for: "
        + ", ".join(partial_metrics)
        + ". The dashboard displays all available years "
          "without causing an application error."
    )
else:

    st.caption(
        "All selected metrics have at least 10 available "
        "historical observations."
    )


# ============================================================
# FOOTNOTE
# ============================================================

st.caption(
    "Note: CAGR is calculated from the latest available "
    "observation and the closest available observation at "
    "least 3, 5, or 10 years earlier. CAGR is shown as N/A "
    "when the required historical period is unavailable or "
    "when the calculation is not meaningful for non-positive "
    "values."
)