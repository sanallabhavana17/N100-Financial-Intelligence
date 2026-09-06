import streamlit as st
import pandas as pd
import plotly.express as px
from src.dashboard.data_loader import load_db
from src.dashboard.style import configure_page, apply_styles


configure_page()
apply_styles()


st.title("Sector Analysis")
st.caption(
    "Compare NIFTY 100 companies within sectors using profitability, "
    "growth and market-cap information."
)


# ------------------------------------------------------------
# Load sector data
# ------------------------------------------------------------

query = """
SELECT
    c.id AS company_id,
    c.company_name,
    s.broad_sector,
    s.sub_sector,
    r.year,
    r.return_on_equity_pct,
    r.return_on_capital_employed_pct,
    r.net_profit_margin_pct,
    r.operating_profit_margin_pct,
    r.revenue_cagr_5yr,
    r.pat_cagr_5yr,
    m.market_cap_crore
FROM companies c
JOIN sectors s
    ON c.id = s.company_id
LEFT JOIN financial_ratios r
    ON c.id = r.company_id
LEFT JOIN market_cap m
    ON c.id = m.company_id
    AND r.year = m.year
"""

df = load_db(query)


if df.empty:
    st.error("No sector analysis data found.")
    st.stop()


# ------------------------------------------------------------
# Convert numeric columns
# ------------------------------------------------------------

numeric_columns = [
    "year",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "market_cap_crore",
]

for column in numeric_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    )


df = df.dropna(
    subset=["year", "broad_sector"]
).copy()


# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------

st.sidebar.header("Sector Analysis")


sectors = sorted(
    df["broad_sector"]
    .dropna()
    .unique()
    .tolist()
)


selected_sector = st.sidebar.selectbox(
    "Sector",
    sectors,
)


sector_df = df[
    df["broad_sector"] == selected_sector
].copy()


years = sorted(
    sector_df["year"]
    .dropna()
    .unique()
    .tolist()
)


if not years:
    st.warning("No years available for this sector.")
    st.stop()


selected_year = st.sidebar.selectbox(
    "Year",
    years,
    index=len(years) - 1,
)


year_df = sector_df[
    sector_df["year"] == selected_year
].copy()


# ------------------------------------------------------------
# Summary KPIs
# ------------------------------------------------------------

st.subheader(
    f"{selected_sector} � {int(selected_year)}"
)


col1, col2, col3, col4 = st.columns(4)


with col1:
    st.metric(
        "Companies",
        year_df["company_id"].nunique(),
    )


with col2:
    median_roe = year_df[
        "return_on_equity_pct"
    ].median()

    st.metric(
        "Median ROE",
        f"{median_roe:.2f}%"
        if pd.notna(median_roe)
        else "N/A",
    )


with col3:
    median_revenue_cagr = year_df[
        "revenue_cagr_5yr"
    ].median()

    st.metric(
        "Median Revenue CAGR",
        f"{median_revenue_cagr:.2f}%"
        if pd.notna(median_revenue_cagr)
        else "N/A",
    )


with col4:
    total_market_cap = year_df[
        "market_cap_crore"
    ].sum()

    st.metric(
        "Total Market Cap",
        f"?{total_market_cap:,.0f} Cr"
        if pd.notna(total_market_cap)
        else "N/A",
    )


# ------------------------------------------------------------
# Revenue vs ROE bubble chart
# ------------------------------------------------------------

st.subheader("Revenue Growth vs ROE")


bubble_df = year_df.dropna(
    subset=[
        "revenue_cagr_5yr",
        "return_on_equity_pct",
    ]
).copy()


if not bubble_df.empty:

    bubble_df["market_cap_crore"] = (
        bubble_df["market_cap_crore"]
        .fillna(1)
        .clip(lower=1)
    )

    fig = px.scatter(
        bubble_df,
        x="revenue_cagr_5yr",
        y="return_on_equity_pct",
        size="market_cap_crore",
        hover_name="company_name",
        hover_data={
            "company_id": True,
            "broad_sector": True,
            "revenue_cagr_5yr": ":.2f",
            "return_on_equity_pct": ":.2f",
            "market_cap_crore": ":,.0f",
        },
        labels={
            "revenue_cagr_5yr": "Revenue CAGR 5Y (%)",
            "return_on_equity_pct": "ROE (%)",
            "market_cap_crore": "Market Cap (? Cr)",
        },
        title=(
            f"{selected_sector}: Revenue Growth vs ROE"
        ),
    )

    fig.update_layout(
        height=600,
        margin=dict(
            l=50,
            r=30,
            t=60,
            b=50,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

else:
    st.info(
        "Insufficient Revenue CAGR and ROE data "
        "for the selected sector and year."
    )


# ------------------------------------------------------------
# Sector median KPI chart
# ------------------------------------------------------------

st.subheader("Sector Median KPIs")


kpi_columns = {
    "ROE": "return_on_equity_pct",
    "ROCE": "return_on_capital_employed_pct",
    "Net Profit Margin": "net_profit_margin_pct",
    "Operating Margin": "operating_profit_margin_pct",
    "Revenue CAGR 5Y": "revenue_cagr_5yr",
    "PAT CAGR 5Y": "pat_cagr_5yr",
}


median_values = []

for label, column in kpi_columns.items():

    value = year_df[column].median()

    median_values.append(
        {
            "Metric": label,
            "Median": value,
        }
    )


median_df = pd.DataFrame(median_values)

median_df = median_df.dropna(
    subset=["Median"]
)


if not median_df.empty:

    fig = px.bar(
        median_df,
        x="Metric",
        y="Median",
        text="Median",
        title=(
            f"{selected_sector}: Median Financial KPIs"
        ),
    )

    fig.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside",
    )

    fig.update_layout(
        height=450,
        yaxis_title="Median Value",
        xaxis_title="",
        margin=dict(
            l=50,
            r=30,
            t=60,
            b=80,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

else:
    st.info(
        "No KPI data available for the selected sector."
    )


# ------------------------------------------------------------
# Company table
# ------------------------------------------------------------

st.subheader("Companies in Selected Sector")


table_columns = [
    "company_id",
    "company_name",
    "sub_sector",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "net_profit_margin_pct",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "market_cap_crore",
]


table_columns = [
    column
    for column in table_columns
    if column in year_df.columns
]


company_table = year_df[
    table_columns
].copy()


company_table = company_table.sort_values(
    "return_on_equity_pct",
    ascending=False,
    na_position="last",
)


st.dataframe(
    company_table,
    use_container_width=True,
    hide_index=True,
)
