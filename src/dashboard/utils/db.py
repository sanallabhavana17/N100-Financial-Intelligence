import sqlite3
from pathlib import Path
import streamlit as st
import pandas as pd

DB_PATH = Path(__file__).resolve().parents[3] / "data" / "nifty100.db"


def _read_sql(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_companies():
    return _read_sql("""
        SELECT
            c.id AS company_id,
            c.company_name,
            c.about_company,
            c.website,
            c.nse_profile,
            c.bse_profile,
            c.book_value,
            c.roce_percentage,
            c.roe_percentage,
            s.broad_sector AS sector,
            s.sub_sector,
            s.index_weight_pct,
            s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s
            ON c.id = s.company_id
        ORDER BY c.company_name
    """)


@st.cache_data(ttl=600)
def get_ratios(ticker, year=None):
    if year is None:
        return _read_sql("""
            SELECT *
            FROM financial_ratios
            WHERE company_id = ?
            ORDER BY year
        """, (ticker,))

    return _read_sql("""
        SELECT *
        FROM financial_ratios
        WHERE company_id = ? AND year = ?
        ORDER BY year
    """, (ticker, year))


@st.cache_data(ttl=600)
def get_pl(ticker):
    return _read_sql("""
        SELECT *
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY year
    """, (ticker,))


@st.cache_data(ttl=600)
def get_bs(ticker):
    return _read_sql("""
        SELECT *
        FROM balancesheet
        WHERE company_id = ?
        ORDER BY year
    """, (ticker,))


@st.cache_data(ttl=600)
def get_cf(ticker):
    return _read_sql("""
        SELECT *
        FROM cashflow
        WHERE company_id = ?
        ORDER BY year
    """, (ticker,))


@st.cache_data(ttl=600)
def get_sectors():
    return _read_sql("""
        SELECT
            company_id,
            broad_sector,
            sub_sector,
            index_weight_pct,
            market_cap_category
        FROM sectors
        ORDER BY broad_sector, sub_sector, company_id
    """)


@st.cache_data(ttl=600)
def get_peers(group_name):
    return _read_sql("""
        SELECT
            pg.peer_group_name,
            pg.company_id,
            c.company_name,
            pg.is_benchmark,
            s.broad_sector AS sector,
            s.sub_sector
        FROM peer_groups pg
        LEFT JOIN companies c
            ON pg.company_id = c.id
        LEFT JOIN sectors s
            ON pg.company_id = s.company_id
        WHERE pg.peer_group_name = ?
        ORDER BY pg.is_benchmark DESC, c.company_name
    """, (group_name,))


@st.cache_data(ttl=600)
def get_valuation(ticker):
    return _read_sql("""
        SELECT
            company_id,
            year,
            market_cap_crore,
            enterprise_value_crore,
            pe_ratio,
            pb_ratio,
            ev_ebitda,
            dividend_yield_pct
        FROM market_cap
        WHERE company_id = ?
        ORDER BY year
    """, (ticker,))


@st.cache_data(ttl=600)
def get_documents(ticker):
    return _read_sql("""
        SELECT
            company_id,
            year,
            annual_report
        FROM documents
        WHERE company_id = ?
        ORDER BY year DESC
    """, (ticker,))


@st.cache_data(ttl=600)
def get_pros_cons(ticker):
    return _read_sql("""
        SELECT
            company_id,
            pros,
            cons
        FROM prosandcons
        WHERE company_id = ?
    """, (ticker,))


@st.cache_data(ttl=600)
def get_stock_prices(ticker):
    return _read_sql("""
        SELECT *
        FROM stock_prices
        WHERE company_id = ?
        ORDER BY date
    """, (ticker,))


@st.cache_data(ttl=600)
def get_peer_percentiles(ticker, group_name=None, year=None):
    if group_name is not None and year is not None:
        return _read_sql("""
            SELECT *
            FROM peer_percentiles
            WHERE company_id = ?
              AND peer_group_name = ?
              AND year = ?
            ORDER BY metric
        """, (ticker, group_name, year))

    if group_name is not None:
        return _read_sql("""
            SELECT *
            FROM peer_percentiles
            WHERE company_id = ?
              AND peer_group_name = ?
            ORDER BY year, metric
        """, (ticker, group_name))

    return _read_sql("""
        SELECT *
        FROM peer_percentiles
        WHERE company_id = ?
        ORDER BY year, peer_group_name, metric
    """, (ticker,))


@st.cache_data(ttl=600)
def get_analysis(ticker):
    return _read_sql("""
        SELECT *
        FROM analysis
        WHERE company_id = ?
    """, (ticker,))


@st.cache_data(ttl=600)
def get_years():
    return _read_sql("""
        SELECT DISTINCT year
        FROM financial_ratios
        WHERE year IS NOT NULL
        ORDER BY year
    """)


@st.cache_data(ttl=600)
def get_peer_group_names():
    return _read_sql("""
        SELECT DISTINCT peer_group_name
        FROM peer_groups
        ORDER BY peer_group_name
    """)["peer_group_name"].tolist()


def clear_cache():
    st.cache_data.clear()
@st.cache_data(ttl=600)
def get_peer_group_percentiles(group_name, year=None):
    if year is None:
        return _read_sql("""
            SELECT
                company_id,
                peer_group_name,
                metric,
                value,
                percentile_rank,
                year
            FROM peer_percentiles
            WHERE peer_group_name = ?
            ORDER BY year, company_id, metric
        """, (group_name,))

    return _read_sql("""
        SELECT
            company_id,
            peer_group_name,
            metric,
            value,
            percentile_rank,
            year
        FROM peer_percentiles
        WHERE peer_group_name = ?
          AND year = ?
        ORDER BY company_id, metric
    """, (group_name, year))