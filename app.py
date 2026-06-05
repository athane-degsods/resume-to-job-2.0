import os

import streamlit as st

from src.adapters.outbound.logging.structured_logging import configure_logging

configure_logging()
APP_VERSION = os.getenv("APP_VERSION", "dev")

st.set_page_config(
	page_title="Resume to Job 2.0",
	page_icon="🎯",
	layout="wide",
)

st.title("Resume to Job 2.0")
st.caption(f"Version {APP_VERSION} · job ingestion, similarity matching, and AI recommendations")

st.markdown(
	"""
	### Workflow
	1. **Data Ingestion** — upload CSV or fetch jobs from an API; embeddings are stored in SQLite.
	2. **Dashboard** — review ingested jobs (10 per page) and pipeline counts.
	3. **Job Matching** — upload a resume PDF, run **Find Matches**, then **Get AI Recommendations** on those results.
	"""
)

st.info(
	"Run locally with `streamlit run app.py` or as a container — see [DEPLOYMENT.md](DEPLOYMENT.md)."
)
