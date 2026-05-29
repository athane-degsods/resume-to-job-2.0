from __future__ import annotations

from src.domain.entities.Job import Job
from src.ports.output.job_repository import JobRepositoryPort


class IngestJobUseCase:
	"""Minimal application use case to ingest a single job.

	Responsibilities:
	- perform light validation/coercion
	- call the repository port to persist the job
	"""

	def __init__(self, repository: JobRepositoryPort) -> None:
		self._repo = repository

	def execute(self, job: Job) -> dict[str, object]:
		if not job.id or not job.title or not job.company:
			return {"ok": False, "message": "Missing required job fields"}

		# Domain-level checks would go here (deduplication, normalization, etc.)
		self._repo.upsert(job)
		return {"ok": True, "message": f"Job {job.id} persisted"}
