from pathlib import Path
import sys

import streamlit as st


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PAGES_DIR = PROJECT_ROOT / "pages"

# Make the project root importable so pages can use:
# from src.dashboard.utils.db import ...
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# PAGE DEFINITIONS
# ============================================================

pages = {
    "Dashboard": [
        st.Page(
            str(PAGES_DIR / "01_home.py"),
            title="Home",
            icon="🏠",
        ),
        st.Page(
            str(PAGES_DIR / "02_profile.py"),
            title="Company Profile",
            icon="🏢",
        ),
        st.Page(
            str(PAGES_DIR / "03_screener.py"),
            title="Screener",
            icon="🔎",
        ),
        st.Page(
            str(PAGES_DIR / "04_peers.py"),
            title="Peer Analysis",
            icon="👥",
        ),
        st.Page(
            str(PAGES_DIR / "05_trends.py"),
            title="Trend Analysis",
            icon="📈",
        ),
        st.Page(
            str(PAGES_DIR / "06_sectors.py"),
            title="Sector Analysis",
            icon="📊",
        ),
        st.Page(
            str(PAGES_DIR / "07_capital.py"),
            title="Capital Allocation",
            icon="💰",
        ),
        st.Page(
            str(PAGES_DIR / "08_reports.py"),
            title="Annual Reports",
            icon="📄",
        ),
    ]
}


# ============================================================
# NAVIGATION
# ============================================================

pg = st.navigation(pages)


# ============================================================
# SIDEBAR BRANDING
# ============================================================

with st.sidebar:
    st.markdown("## 📊 Nifty 100 Analytics")
    st.caption("Financial Intelligence Dashboard")
    st.divider()
    st.caption("Sprint 4 • Dashboard & Valuation")
    st.caption("92 Nifty 100 Companies")


# ============================================================
# RUN SELECTED PAGE
# ============================================================

pg.run()
