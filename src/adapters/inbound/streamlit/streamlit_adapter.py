from __future__ import annotations

import os

import pandas as pd

from src.adapters.inbound.api_provider.api_client import fetch_jobs
from src.adapters.inbound.api_provider.api_job_parser import ApiJobParser
from src.adapters.inbound.file_upload.dataframe_job_parser import DataFrameJobParser
from src.adapters.outbound.embedding.sentence_transformers_adapter import (
    SentenceTransformersEmbeddingAdapter,
)
from src.application.use_cases.ingest_jobs_batch import IngestJobsBatchUseCase
from src.domain.entities.Job import Job
from src.ports.output.job_repository import JobRepositoryPort
from pathlib import Path
from src.adapters.outbound.persistence.sqlite_job_repository import SQLiteJobRepository


class FakeJobRepository(JobRepositoryPort):
    """Tiny in-memory repository for demos and tests."""

    def __init__(self) -> None:
        self._store: dict[str, Job] = {}
        self.batches: list[list[Job]] = []

    def upsert(self, job: Job) -> None:
        self.upsert_many([job])

    def upsert_many(self, jobs: list[Job]) -> None:
        self.batches.append(list(jobs))
        for job in jobs:
            self._store[job.id] = job


def run_demo() -> None:
    """Run a small demo from the command line."""
    db_path = Path("data/jobs.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    repo = SQLiteJobRepository(db_path)
    parser = DataFrameJobParser()
    dataframe = pd.DataFrame(
        [
            {
                "id": "JOB-001",
                "title": "Data Scientist",
                "company": "Acme Analytics",
                "description": "Analyze product usage data and build forecasting models.",
                "location": "Remote",
                "source": "demo",
            },
            {
                "id": "JOB-002",
                "title": "ML Engineer",
                "company": "Nova AI",
                "description": "Build training pipelines and deploy ranking models.",
                "location": "New York",
                "source": "demo",
            },
        ]
    )
    embedding_service = SentenceTransformersEmbeddingAdapter()
    jobs = parser.to_jobs(dataframe)
    usecase = IngestJobsBatchUseCase(repository=repo, batch_size=200, embedding_service=embedding_service)
    result = usecase.execute(jobs)
    print(result)


# Optional Streamlit integration helper.
# To use inside your Streamlit page, import `streamlit_app` and call it from the page script.
def streamlit_app():
    import streamlit as st

    st.title("Ingest Jobs (demo)")
    st.caption("Data route: CSV upload or API endpoint -> parser -> list[Job] -> batches of 200 -> repository")

    source = st.radio("Choose the ingestion source", ["CSV upload", "API endpoint"], horizontal=True)

    parser = DataFrameJobParser()
    api_parser = ApiJobParser()
    db_path = Path(os.getenv("JOB_DB_PATH", "data/jobs.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    repo = SQLiteJobRepository(db_path)
    embedding_service = SentenceTransformersEmbeddingAdapter()
    usecase = IngestJobsBatchUseCase(repository=repo, batch_size=200, embedding_service=embedding_service)

    if "loaded_jobs" not in st.session_state:
        st.session_state.loaded_jobs = []
    if "loaded_preview" not in st.session_state:
        st.session_state.loaded_preview = None
    if "loaded_source" not in st.session_state:
        st.session_state.loaded_source = None
    if "loaded_errors" not in st.session_state:
        st.session_state.loaded_errors = []

    if source == "CSV upload":
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file is None:
            st.info("Upload a CSV to convert it into jobs and ingest it in batches of 200.")
        else:
            dataframe = pd.read_csv(uploaded_file)
            jobs, errors = parser.to_jobs_with_errors_from_dataframe(dataframe)

            st.session_state.loaded_jobs = jobs
            st.session_state.loaded_preview = dataframe
            st.session_state.loaded_source = "CSV upload"
            st.session_state.loaded_errors = errors

            st.markdown("### Type transitions")
            st.write(f"1. Uploaded file -> `{type(uploaded_file).__name__}`")
            st.write(f"2. Parsed table -> `{type(dataframe).__name__}`")
            st.write(f"3. Domain objects -> `{type(jobs).__name__}`")
            st.write(f"4. Batch size -> `200` jobs")
            if errors:
                st.warning(f"Discarded {len(errors)} row(s) missing required fields, including description.")
                st.table(pd.DataFrame(errors))
    else:
        endpoint = st.text_input("API endpoint", placeholder="https://example.com/api/jobs")
        api_key = st.text_input(
            "API key",
            value=os.getenv("JOB_API_KEY", ""),
            type="password",
            help="Leave blank if the key is already set in your environment.",
        )

        if not endpoint:
            st.info("Enter an API endpoint to import jobs.")
        elif st.button("Fetch API data"):
            payload = fetch_jobs(endpoint=endpoint, api_key=api_key or None)
            records = api_parser.to_records(payload)
            jobs, errors = api_parser.to_jobs_with_errors(payload)
            st.session_state.loaded_jobs = jobs
            st.session_state.loaded_preview = pd.DataFrame(records)
            st.session_state.loaded_source = "API endpoint"
            st.session_state.loaded_errors = errors

            st.markdown("### Type transitions")
            st.write("1. Endpoint input -> `str`")
            st.write(f"2. Provider response -> `{type(payload).__name__}`")
            st.write(f"3. Parsed records -> `{type(records).__name__}`")
            st.write(f"4. Domain objects -> `{type(jobs).__name__}`")
            st.write(f"5. Batch size -> `200` jobs")
            if errors:
                st.warning(f"Discarded {len(errors)} row(s) missing required fields, including description.")
                st.table(pd.DataFrame(errors))

    jobs = st.session_state.loaded_jobs
    preview = st.session_state.loaded_preview

    if jobs:
        st.success(f"Loaded {len(jobs)} jobs from {st.session_state.loaded_source}.")
        if preview is not None:
            st.dataframe(preview, use_container_width=True)

    if st.button("Ingest"):
        if not jobs:
            st.warning("No jobs were loaded yet.")
            return

        result = usecase.execute(jobs)
        st.json(result)
        try:
            st.write(f"Total rows in DB: {repo.count()}")
        except Exception:
            st.write("Ingested (count unavailable)")


if __name__ == "__main__":
    run_demo()
