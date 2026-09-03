import streamlit as st


def configure_page() -> None:
    """Apply common Streamlit page configuration."""
    st.set_page_config(
        page_title="N100 Financial Intelligence",
        page_icon="??",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def apply_styles() -> None:
    """Apply shared dashboard styling."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        [data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 10px;
            padding: 12px;
        }

        .dashboard-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }

        .dashboard-subtitle {
            color: #666;
            margin-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
