import streamlit as st


def configure_page() -> None:
    """Compatibility hook for pages using the shared dashboard style.

    Page configuration is handled once by src/dashboard/app.py
    because the dashboard uses Streamlit's multipage navigation.
    """
    return None


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
