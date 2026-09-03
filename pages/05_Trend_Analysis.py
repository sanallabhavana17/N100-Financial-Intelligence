import streamlit as st
import pandas as pd
import plotly.express as px

from src.dashboard.data_loader import load_db
from src.dashboard.style import configure_page, apply_styles


configure_page()
apply_styles()

st.title("Trend Analysis")
st.caption(
    "Explore historical financial trends and growth across NIFTY 100 companies."
)


# ---------------------------------------------------------
# Company list
# ---------------------------------------------------------

companies = load_db(
    """
    SELECT id, company_name
    FROM companies
    ORDER BY company_name
    """
)

if companies.empty:
    st.warning("No companies found in the database.")
    st.stop()


company_labels = dict(
    zip(
        companies["id"],
        companies["company_name"],
    )
)

company_ids = companies["id"].tolist()

selected_company = st.sidebar.selectbox(
    "Company",
    company_ids,
    format_func=lambda x: company_labels.get(x, x),
)


# ---------------------------------------------------------
# Metric selection
# ---------------------------------------------------------

metric_options = [
    "Revenue",
    "Net Profit",
    "EPS",
    "ROE",
    "ROCE",
    "ROA",
    "Net Profit Margin",
    "Operating Profit Margin",
    "Debt to Equity",
    "Interest Coverage",
    "Free Cash Flow",
    "Asset Turnover",
    "Dividend Payout",
]

selected_metric = st.sidebar.selectbox(
    "Metric",
    metric_options,
)


# ---------------------------------------------------------
# Raw historical data
# ---------------------------------------------------------

# Revenue, Net Profit and EPS are stored in profitandloss.
if selected_metric in ["Revenue", "Net Profit", "EPS"]:

    pnl_column_map = {
        "Revenue": "sales",
        "Net Profit": "net_profit",
        "EPS": "eps",
    }

    value_column = pnl_column_map[selected_metric]

    query = f"""
    SELECT
        year,
        {value_column} AS metric_value
    FROM profitandloss
    WHERE company_id = ?
    ORDER BY year
    """

    trend_df = load_db(
        query,
        (selected_company,),
    )

# Other metrics are stored in financial_ratios.
else:

    ratio_column_map = {
        "ROE": "return_on_equity_pct",
        "ROCE": "return_on_capital_employed_pct",
        "ROA": "return_on_assets_pct",
        "Net Profit Margin": "net_profit_margin_pct",
        "Operating Profit Margin": "operating_profit_margin_pct",
        "Debt to Equity": "debt_to_equity",
        "Interest Coverage": "interest_coverage",
        "Free Cash Flow": "free_cash_flow_cr",
        "Asset Turnover": "asset_turnover",
        "Dividend Payout": "dividend_payout_ratio_pct",
    }

    value_column = ratio_column_map[selected_metric]

    query = f"""
    SELECT
        year,
        {value_column} AS metric_value
    FROM financial_ratios
    WHERE company_id = ?
    ORDER BY year
    """

    trend_df = load_db(
        query,
        (selected_company,),
    )


if trend_df.empty:
    st.warning(
        f"No historical data available for "
        f"{company_labels.get(selected_company, selected_company)}."
    )
    st.stop()


# ---------------------------------------------------------
# Numeric conversion
# ---------------------------------------------------------

trend_df["year"] = pd.to_numeric(
    trend_df["year"],
    errors="coerce",
)

trend_df["metric_value"] = pd.to_numeric(
    trend_df["metric_value"],
    errors="coerce",
)

trend_df = trend_df.dropna(
    subset=["year", "metric_value"]
)

if trend_df.empty:
    st.warning("No valid numeric historical data is available.")
    st.stop()


# ---------------------------------------------------------
# Company heading
# ---------------------------------------------------------

company_name = company_labels.get(
    selected_company,
    selected_company,
)

st.subheader(
    f"{company_name} — {selected_metric} Trend"
)


# ---------------------------------------------------------
# Trend chart
# ---------------------------------------------------------

fig = px.line(
    trend_df,
    x="year",
    y="metric_value",
    markers=True,
    title=f"{selected_metric} Historical Trend",
)

fig.update_layout(
    height=500,
    xaxis_title="Year",
    yaxis_title=selected_metric,
    margin=dict(
        l=10,
        r=10,
        t=50,
        b=10,
    ),
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ---------------------------------------------------------
# Historical table
# ---------------------------------------------------------

st.subheader("Historical Data")

table_df = trend_df.copy()

table_df["year"] = table_df["year"].astype(int)

table_df = table_df.rename(
    columns={
        "year": "Year",
        "metric_value": selected_metric,
    }
)

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# CAGR helper
# ---------------------------------------------------------

def calculate_cagr(dataframe, years):
    if dataframe.empty:
        return None

    data = dataframe.sort_values("year")

    latest_year = data["year"].max()
    target_year = latest_year - years

    eligible = data[
        data["year"] <= target_year
    ]

    if eligible.empty:
        return None

    start_row = eligible.iloc[-1]
    end_row = data.iloc[-1]

    start_value = start_row["metric_value"]
    end_value = end_row["metric_value"]

    if pd.isna(start_value) or pd.isna(end_value):
        return None

    if start_value <= 0 or end_value <= 0:
        return None

    actual_years = (
        end_row["year"] - start_row["year"]
    )

    if actual_years <= 0:
        return None

    return (
        (end_value / start_value)
        ** (1 / actual_years)
        - 1
    ) * 100


# ---------------------------------------------------------
# Growth / CAGR section
# ---------------------------------------------------------

st.subheader("Growth Analysis")

cagr_1 = calculate_cagr(trend_df, 1)
cagr_3 = calculate_cagr(trend_df, 3)
cagr_5 = calculate_cagr(trend_df, 5)
cagr_10 = calculate_cagr(trend_df, 10)


def format_cagr(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("1Y CAGR", format_cagr(cagr_1))

with col2:
    st.metric("3Y CAGR", format_cagr(cagr_3))

with col3:
    st.metric("5Y CAGR", format_cagr(cagr_5))

with col4:
    st.metric("10Y CAGR", format_cagr(cagr_10))


# ---------------------------------------------------------
# Ratio Engine CAGR cross-check
# ---------------------------------------------------------

if selected_metric in ["Revenue", "Net Profit", "EPS"]:

    ratio_cagr_map = {
        "Revenue": {
            "1Y": "revenue_cagr_3yr",
            "3Y": "revenue_cagr_3yr",
            "5Y": "revenue_cagr_5yr",
            "10Y": "revenue_cagr_10yr",
        },
        "Net Profit": {
            "1Y": "pat_cagr_3yr",
            "3Y": "pat_cagr_3yr",
            "5Y": "pat_cagr_5yr",
            "10Y": "pat_cagr_10yr",
        },
        "EPS": {
            "1Y": "eps_cagr_3yr",
            "3Y": "eps_cagr_3yr",
            "5Y": "eps_cagr_5yr",
            "10Y": "eps_cagr_10yr",
        },
    }

    # The Ratio Engine stores 3Y/5Y/10Y CAGR.
    # Keep this section as a reference rather than
    # replacing the directly calculated trend CAGR.
    ratio_columns = ratio_cagr_map[selected_metric]

    ratio_query = f"""
    SELECT
        year,
        {ratio_columns["3Y"]} AS cagr_3yr,
        {ratio_columns["5Y"]} AS cagr_5yr,
        {ratio_columns["10Y"]} AS cagr_10yr
    FROM financial_ratios
    WHERE company_id = ?
    ORDER BY year DESC
    LIMIT 1
    """

    ratio_df = load_db(
        ratio_query,
        (selected_company,),
    )

    if not ratio_df.empty:

        latest_ratio = ratio_df.iloc[0]

        st.caption(
            "Ratio Engine CAGR reference"
        )

        ref1, ref2, ref3 = st.columns(3)

        with ref1:
            value = pd.to_numeric(
                latest_ratio["cagr_3yr"],
                errors="coerce",
            )
            st.metric(
                "3Y Ratio Engine CAGR",
                f"{value:.2f}%"
                if pd.notna(value)
                else "N/A",
            )

        with ref2:
            value = pd.to_numeric(
                latest_ratio["cagr_5yr"],
                errors="coerce",
            )
            st.metric(
                "5Y Ratio Engine CAGR",
                f"{value:.2f}%"
                if pd.notna(value)
                else "N/A",
            )

        with ref3:
            value = pd.to_numeric(
                latest_ratio["cagr_10yr"],
                errors="coerce",
            )
            st.metric(
                "10Y Ratio Engine CAGR",
                f"{value:.2f}%"
                if pd.notna(value)
                else "N/A",
            )
