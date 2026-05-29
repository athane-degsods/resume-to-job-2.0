from src.adapters.inbound.streamlit.streamlit_adapter import streamlit_app

# Delegate the page UI to the Streamlit adapter helper which
# parses uploads into DataFrame -> Job entities -> batches -> repository.
streamlit_app()
