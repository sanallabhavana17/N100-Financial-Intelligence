import streamlit as st

from src.dashboard.data_loader import get_table_names
from src.dashboard.style import configure_page, apply_styles


configure_page()
apply_styles()


st.markdown(
    '<div class="dashboard-title">N100 Financial Intelligence</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="dashboard-subtitle">'
    'Financial analysis, screening, peer comparison and valuation'
    '</div>',
    unsafe_allow_html=True,
)

st.sidebar.title("N100 Financial Intelligence")
st.sidebar.caption("Sprint 4 Dashboard")

st.sidebar.divider()

st.sidebar.markdown("### Navigation")
st.sidebar.info(
    "Use the pages in the sidebar to explore the dashboard."
)

st.divider()

st.subheader("Dashboard Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Database Tables", len(get_table_names()))

with col2:
    st.metric("Data Source", "SQLite")

with col3:
    st.metric("Dashboard Status", "Sprint 4")

st.success(
    "Dashboard scaffold loaded successfully."
)

st.markdown(
    """
    ### Getting Started

    Select a dashboard screen from the sidebar.

    The dashboard will provide:

    - Company search and profiles
    - Financial KPIs
    - Historical charts
    - Profitability analysis
    - Leverage and efficiency analysis
    - Cash-flow analysis
    - Peer comparison
    - Valuation analysis
    """
)
