import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.dashboard.data_loader import load_db, get_companies
from src.dashboard.style import configure_page, apply_styles


configure_page()
apply_styles()


def format_number(value, decimals=2):
    if value is None or pd.isna(value):
        return "N/A"

    try:
        return f"{float(value):,.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)

def format_percentage(value):
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.2f}%"


st.title("Company Profile")
st.caption(
    "Explore financial performance, profitability, leverage and valuation."
)


companies = get_companies()

if companies.empty:
    st.error("No companies were found in the database.")
    st.stop()


company_names = companies["company_name"].dropna().tolist()

selected_company = st.selectbox(
    "Search / Select Company",
    company_names,
)

company = companies[
    companies["company_name"] == selected_company
].iloc[0]

company_id = company["id"]


st.divider()

st.subheader(selected_company)

about = load_db(
    """
    SELECT about_company
    FROM companies
    WHERE id = ?
    """,
    (company_id,),
)

if not about.empty and pd.notna(about.iloc[0]["about_company"]):
    st.write(about.iloc[0]["about_company"])


link_col1, link_col2, link_col3 = st.columns(3)

with link_col1:
    website = company["website"]
    if pd.notna(website) and str(website).strip():
        st.markdown(f"**Company Website:** {website}")

with link_col2:
    nse = company["nse_profile"]
    if pd.notna(nse) and str(nse).strip():
        st.markdown(f"**NSE Profile:** {nse}")

with link_col3:
    bse = company["bse_profile"]
    if pd.notna(bse) and str(bse).strip():
        st.markdown(f"**BSE Profile:** {bse}")


financials = load_db(
    """
    SELECT
        p.year,
        p.sales,
        p.operating_profit,
        p.opm_percentage,
        p.net_profit,
        p.eps,
        b.borrowings,
        r.return_on_equity_pct,
        r.return_on_capital_employed_pct,
        r.debt_to_equity,
        r.free_cash_flow_cr,
        r.composite_quality_score,
        m.market_cap_crore,
        m.pe_ratio,
        m.pb_ratio,
        m.ev_ebitda
    FROM profitandloss p

    LEFT JOIN balancesheet b
        ON p.company_id = b.company_id
        AND p.year = b.year

    LEFT JOIN financial_ratios r
        ON p.company_id = r.company_id
        AND p.year = r.year

    LEFT JOIN market_cap m
        ON p.company_id = m.company_id
        AND p.year = m.year

    WHERE p.company_id = ?

    ORDER BY p.year
    """,
    (company_id,),
)


if financials.empty:
    st.warning("No financial history is available for this company.")
    st.stop()


financials["year"] = pd.to_numeric(
    financials["year"],
    errors="coerce",
)

financials = financials.sort_values("year")

latest = financials.iloc[-1]


st.subheader("Latest Financial Snapshot")

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric("Sales", format_number(latest["sales"]))

with k2:
    st.metric("Net Profit", format_number(latest["net_profit"]))

with k3:
    st.metric(
        "ROE",
        format_percentage(latest["return_on_equity_pct"]),
    )

with k4:
    st.metric(
        "Debt / Equity",
        format_number(latest["debt_to_equity"]),
    )


k5, k6, k7, k8 = st.columns(4)

with k5:
    st.metric("EPS", format_number(latest["eps"]))

with k6:
    st.metric(
        "Market Cap",
        format_number(latest["market_cap_crore"]),
    )

with k7:
    st.metric("P/E", format_number(latest["pe_ratio"]))

with k8:
    st.metric(
        "Quality Score",
        format_number(latest["composite_quality_score"]),
    )


chart_data = financials.tail(10).copy()


st.subheader("10-Year Sales & Net Profit")

fig = go.Figure()

fig.add_trace(
    go.Bar(
        x=chart_data["year"],
        y=chart_data["sales"],
        name="Sales",
    )
)

fig.add_trace(
    go.Bar(
        x=chart_data["year"],
        y=chart_data["net_profit"],
        name="Net Profit",
    )
)

fig.update_layout(
    barmode="group",
    xaxis_title="Year",
    yaxis_title="Amount",
    height=450,
    hovermode="x unified",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


st.subheader("EPS Trend")

eps_fig = go.Figure()

eps_fig.add_trace(
    go.Bar(
        x=chart_data["year"],
        y=chart_data["eps"],
        name="EPS",
    )
)

eps_fig.update_layout(
    xaxis_title="Year",
    yaxis_title="EPS",
    height=400,
    hovermode="x unified",
)

st.plotly_chart(
    eps_fig,
    use_container_width=True,
)


left, right = st.columns(2)

with left:
    st.subheader("Profitability Trend")

    profitability_fig = go.Figure()

    profitability_fig.add_trace(
        go.Scatter(
            x=chart_data["year"],
            y=chart_data["return_on_equity_pct"],
            mode="lines+markers",
            name="ROE",
        )
    )

    profitability_fig.add_trace(
        go.Scatter(
            x=chart_data["year"],
            y=chart_data["return_on_capital_employed_pct"],
            mode="lines+markers",
            name="ROCE",
        )
    )

    profitability_fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Percentage",
        height=400,
        hovermode="x unified",
    )

    st.plotly_chart(
        profitability_fig,
        use_container_width=True,
    )


with right:
    st.subheader("Debt-to-Equity Trend")

    debt_fig = go.Figure()

    debt_fig.add_trace(
        go.Scatter(
            x=chart_data["year"],
            y=chart_data["debt_to_equity"],
            mode="lines+markers",
            name="Debt / Equity",
        )
    )

    debt_fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Debt / Equity",
        height=400,
        hovermode="x unified",
    )

    st.plotly_chart(
        debt_fig,
        use_container_width=True,
    )


st.subheader("Valuation History")

valuation = financials[
    [
        "year",
        "market_cap_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
    ]
].tail(10)

st.dataframe(
    valuation,
    use_container_width=True,
    hide_index=True,
)


st.subheader("Financial History")

display_columns = [
    "year",
    "sales",
    "operating_profit",
    "opm_percentage",
    "net_profit",
    "eps",
    "borrowings",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
]

available_columns = [
    column
    for column in display_columns
    if column in financials.columns
]

st.dataframe(
    financials[available_columns].tail(10),
    use_container_width=True,
    hide_index=True,
)
