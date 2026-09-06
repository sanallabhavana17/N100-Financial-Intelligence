import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.dashboard.utils.db import (
    get_companies,
    get_ratios,
    get_pl,
    get_pros_cons,
)


st.title("Company Profile")
st.caption("Detailed financial profile for Nifty 100 companies")


# ============================================================
# LOAD COMPANIES
# ============================================================

companies = get_companies()

if companies.empty:
    st.error("Company data is unavailable.")
    st.stop()


# ============================================================
# COMPANY SEARCH
# ============================================================

search_data = companies.copy()

search_data["search_label"] = (
    search_data["company_name"].fillna("").astype(str)
    + " ("
    + search_data["company_id"].fillna("").astype(str)
    + ")"
)

selected_label = st.selectbox(
    "Search / Select Company",
    search_data["search_label"].tolist(),
    index=0,
)

selected_rows = search_data[
    search_data["search_label"] == selected_label
]

if selected_rows.empty:
    st.warning("Ticker not found — please try another.")
    st.stop()

selected_row = selected_rows.iloc[0]

ticker = selected_row["company_id"]
company_name = selected_row["company_name"]


# ============================================================
# COMPANY INFORMATION
# ============================================================

st.divider()

st.header(company_name)

info1, info2, info3, info4 = st.columns(4)

with info1:
    st.markdown("**NSE Ticker**")
    st.write(ticker if pd.notna(ticker) else "N/A")

with info2:
    st.markdown("**Sector**")
    sector = selected_row.get("sector")
    st.write(sector if pd.notna(sector) and sector else "N/A")

with info3:
    st.markdown("**Sub-Sector**")
    sub_sector = selected_row.get("sub_sector")
    st.write(
        sub_sector
        if pd.notna(sub_sector) and sub_sector
        else "N/A"
    )

with info4:
    st.markdown("**Market Cap Category**")
    market_cap_category = selected_row.get("market_cap_category")
    st.write(
        market_cap_category
        if pd.notna(market_cap_category) and market_cap_category
        else "N/A"
    )


about = selected_row.get("about_company")

if pd.notna(about) and about:
    st.markdown("### About the Company")
    st.write(about)


# ============================================================
# LOAD FINANCIAL DATA
# ============================================================

ratios = get_ratios(ticker)
pl = get_pl(ticker)
pros_cons = get_pros_cons(ticker)


# ============================================================
# DATA COVERAGE
# ============================================================

available_years = 0

if not pl.empty and "year" in pl.columns:
    available_years = (
        pd.to_numeric(
            pl["year"],
            errors="coerce"
        )
        .dropna()
        .nunique()
    )

if available_years == 0:
    st.warning(
        "Historical financial data is unavailable for this company. "
        "Unavailable values are shown as N/A."
    )
elif available_years < 10:
    st.info(
        f"Historical financial data is available for "
        f"{available_years} year(s). "
        "Some 10-year metrics may be unavailable."
    )


# ============================================================
# LATEST FINANCIAL YEAR
# ============================================================

latest_ratio = pd.DataFrame()

if not ratios.empty and "year" in ratios.columns:

    ratios = ratios.copy()

    ratios["year"] = pd.to_numeric(
        ratios["year"],
        errors="coerce"
    )

    valid_ratios = ratios.dropna(
        subset=["year"]
    )

    if not valid_ratios.empty:

        latest_year = int(
            valid_ratios["year"].max()
        )

        latest_ratio = valid_ratios[
            valid_ratios["year"] == latest_year
        ].tail(1)


# ============================================================
# SAFE VALUE HELPERS
# ============================================================

def get_value(df, column):

    if df.empty or column not in df.columns:
        return None

    value = df.iloc[0][column]

    if pd.isna(value):
        return None

    try:
        return float(value)

    except (TypeError, ValueError):
        return None


def percent_value(value):

    if value is None:
        return "N/A"

    return f"{value:.2f}%"


def number_value(value):

    if value is None:
        return "N/A"

    return f"{value:.2f}"


# ============================================================
# FINANCIAL KPIs
# ============================================================

roe = get_value(
    latest_ratio,
    "return_on_equity_pct"
)

roce = get_value(
    latest_ratio,
    "return_on_capital_employed_pct"
)

npm = get_value(
    latest_ratio,
    "net_profit_margin_pct"
)

de = get_value(
    latest_ratio,
    "debt_to_equity"
)

revenue_cagr5 = get_value(
    latest_ratio,
    "revenue_cagr_5yr"
)

fcf = get_value(
    latest_ratio,
    "free_cash_flow_cr"
)


# ============================================================
# SIX KPI CARDS
# ============================================================

st.subheader("Key Financial Indicators")

k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.metric(
        "ROE",
        percent_value(roe)
    )

with k2:
    st.metric(
        "ROCE",
        percent_value(roce)
    )

with k3:
    st.metric(
        "Net Profit Margin",
        percent_value(npm)
    )

with k4:
    st.metric(
        "Debt / Equity",
        number_value(de)
    )

with k5:
    st.metric(
        "Revenue CAGR 5Y",
        percent_value(revenue_cagr5)
    )

with k6:

    fcf_text = (
        f"₹{fcf:,.2f} Cr"
        if fcf is not None
        else "N/A"
    )

    st.metric(
        "Latest FCF",
        fcf_text
    )


if latest_ratio.empty:
    st.info(
        "Financial ratio data is unavailable for this company."
    )


# ============================================================
# REVENUE / NET PROFIT HISTORY
# ============================================================

st.divider()

st.subheader(
    "10-Year Revenue & Net Profit"
)

if not pl.empty:

    chart_df = pl.copy()

    chart_df["year"] = pd.to_numeric(
        chart_df["year"],
        errors="coerce"
    )

    chart_df["sales"] = pd.to_numeric(
        chart_df["sales"],
        errors="coerce"
    )

    chart_df["net_profit"] = pd.to_numeric(
        chart_df["net_profit"],
        errors="coerce"
    )

    chart_df = (
        chart_df
        .dropna(subset=["year"])
        .sort_values("year")
        .tail(10)
    )

    if not chart_df.empty:

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=chart_df["year"],
                y=chart_df["sales"],
                name="Revenue",
            )
        )

        fig.add_trace(
            go.Bar(
                x=chart_df["year"],
                y=chart_df["net_profit"],
                name="Net Profit",
            )
        )

        fig.update_layout(
            barmode="group",
            xaxis_title="Year",
            yaxis_title="₹ Crore",
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    else:

        st.info(
            "Revenue and profit history unavailable."
        )

else:

    st.info(
        "Profit and loss data unavailable."
    )


# ============================================================
# ROE / ROCE DUAL-AXIS
# ============================================================

st.divider()

st.subheader(
    "ROE vs ROCE Trend"
)

if not ratios.empty:

    trend_df = ratios.copy()

    trend_df["year"] = pd.to_numeric(
        trend_df["year"],
        errors="coerce"
    )

    trend_df["roe"] = pd.to_numeric(
        trend_df["return_on_equity_pct"],
        errors="coerce"
    )

    trend_df["roce"] = pd.to_numeric(
        trend_df["return_on_capital_employed_pct"],
        errors="coerce"
    )

    trend_df = (
        trend_df
        .dropna(subset=["year"])
        .sort_values("year")
        .tail(10)
    )

    if not trend_df.empty:

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=trend_df["year"],
                y=trend_df["roe"],
                mode="lines+markers",
                name="ROE",
                connectgaps=False,
            )
        )

        fig.add_trace(
            go.Scatter(
                x=trend_df["year"],
                y=trend_df["roce"],
                mode="lines+markers",
                name="ROCE",
                yaxis="y2",
                connectgaps=False,
            )
        )

        fig.update_layout(
            xaxis=dict(
                title="Year"
            ),
            yaxis=dict(
                title="ROE (%)"
            ),
            yaxis2=dict(
                title="ROCE (%)",
                overlaying="y",
                side="right",
            ),
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    else:

        st.info(
            "ROE / ROCE history unavailable."
        )

else:

    st.info(
        "Ratio history unavailable."
    )


# ============================================================
# PROS & CONS
# ============================================================

st.divider()

st.subheader("Pros & Cons")

if not pros_cons.empty:

    pros = (
        pros_cons["pros"]
        .dropna()
        .astype(str)
        .tolist()
        if "pros" in pros_cons.columns
        else []
    )

    cons = (
        pros_cons["cons"]
        .dropna()
        .astype(str)
        .tolist()
        if "cons" in pros_cons.columns
        else []
    )

    left, right = st.columns(2)

    with left:

        st.markdown("### ✅ Pros")

        if pros:

            for item in pros:
                st.markdown(
                    f"- {item}"
                )

        else:

            st.info(
                "No pros available."
            )

    with right:

        st.markdown("### ⚠️ Cons")

        if cons:

            for item in cons:
                st.markdown(
                    f"- {item}"
                )

        else:

            st.info(
                "No cons available."
            )

else:

    st.info(
        "Pros and cons information is not available "
        "for this company."
    )


# ============================================================
# EXTERNAL PROFILES
# ============================================================

st.divider()

link1, link2, link3 = st.columns(3)

with link1:

    website = selected_row.get("website")

    if pd.notna(website) and website:

        st.link_button(
            "Company Website",
            website,
        )

with link2:

    nse = selected_row.get("nse_profile")

    if pd.notna(nse) and nse:

        st.link_button(
            "NSE Profile",
            nse,
        )

with link3:

    bse = selected_row.get("bse_profile")

    if pd.notna(bse) and bse:

        st.link_button(
            "BSE Profile",
            bse,
        )