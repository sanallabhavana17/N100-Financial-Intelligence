import streamlit as st

from src.dashboard.style import configure_page, apply_styles


configure_page()
apply_styles()

st.title("Home")
st.write(
    "Welcome to the N100 Financial Intelligence dashboard."
)

st.info(
    "Sprint 4 dashboard screens will be implemented here."
)
