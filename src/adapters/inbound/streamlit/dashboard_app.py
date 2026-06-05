from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.adapters.outbound.persistence.sqlite_job_repository import SQLiteJobRepository
from src.application.use_cases.get_job_dashboard import (
	DEFAULT_PAGE_SIZE,
	GetJobDashboardUseCase,
)
from src.domain.entities.Job import Job


def _load_repository() -> SQLiteJobRepository:
	db_path = Path(os.getenv("JOB_DB_PATH", "data/jobs.db"))
	db_path.parent.mkdir(parents=True, exist_ok=True)
	return SQLiteJobRepository(db_path)


def _truncate(text: str, max_len: int = 120) -> str:
	clean = " ".join(text.split())
	if len(clean) <= max_len:
		return clean
	return clean[: max_len - 3] + "..."


def _jobs_to_rows(jobs: tuple[Job, ...]) -> list[dict[str, object]]:
	rows: list[dict[str, object]] = []
	for index, job in enumerate(jobs):
		rows.append(
			{
				"#": index + 1,
				"id": job.id,
				"title": job.title,
				"company": job.company,
				"location": job.location or "",
				"source": job.source or "",
				"embedding": "Yes" if job.embedding is not None else "No",
				"description": _truncate(job.description),
			}
		)
	return rows


def streamlit_app() -> None:
	st.title("Dashboard")
	st.caption("Pipeline overview and paginated job catalog from SQLite")

	if "dashboard_page" not in st.session_state:
		st.session_state.dashboard_page = 1

	repo = _load_repository()
	use_case = GetJobDashboardUseCase(repository=repo)

	header_col, refresh_col = st.columns([4, 1])
	with refresh_col:
		if st.button("Refresh", use_container_width=True):
			st.session_state.dashboard_page = 1
			st.rerun()

	stats = use_case.get_stats()
	m1, m2, m3 = st.columns(3)
	m1.metric("Total jobs", stats.total_jobs)
	m2.metric("With embeddings", stats.jobs_with_embeddings)
	m3.metric("Missing embeddings", stats.jobs_without_embeddings)

	with header_col:
		db_path = os.getenv("JOB_DB_PATH", "data/jobs.db")
		st.caption(f"Database: `{db_path}`")

	if stats.total_jobs == 0:
		st.warning("No jobs in the database yet. Ingest jobs on the Data Ingestion page.")
		repo.close()
		return

	page_data = use_case.get_page(st.session_state.dashboard_page, page_size=DEFAULT_PAGE_SIZE)
	st.session_state.dashboard_page = page_data.page

	st.markdown("### Jobs")
	st.caption(
		f"Showing page **{page_data.page}** of **{page_data.total_pages}** "
		f"({page_data.page_size} jobs per page, {page_data.total_jobs} total)"
	)

	st.dataframe(
		pd.DataFrame(_jobs_to_rows(page_data.jobs)),
		use_container_width=True,
		hide_index=True,
	)

	nav_prev, nav_info, nav_next = st.columns([1, 2, 1])
	with nav_prev:
		if st.button(
			"Previous page",
			disabled=page_data.page <= 1,
			use_container_width=True,
			key="dashboard_prev",
		):
			st.session_state.dashboard_page = page_data.page - 1
			st.rerun()
	with nav_info:
		st.write(f"Page {page_data.page} / {page_data.total_pages}")
	with nav_next:
		if st.button(
			"Next page",
			disabled=page_data.page >= page_data.total_pages,
			use_container_width=True,
			key="dashboard_next",
		):
			st.session_state.dashboard_page = page_data.page + 1
			st.rerun()

	repo.close()
