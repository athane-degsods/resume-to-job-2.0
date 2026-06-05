from __future__ import annotations

import time
from dataclasses import dataclass

from src.adapters.outbound.logging.structured_logging import get_logger, log_event
from src.domain.entities.Job import Job
from src.domain.entities.Resume import Resume
from src.domain.services.similarity import cosine_similarity
from src.ports.output.job_repository import JobRepositoryPort

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RankedJobMatch:
	job: Job
	score: float


class MatchJobsToResumeUseCase:
	"""Rank stored jobs by cosine similarity to a resume embedding."""

	def __init__(self, repository: JobRepositoryPort) -> None:
		self._repo = repository

	def execute(self, resume: Resume, *, top_k: int = 10) -> dict[str, object]:
		started = time.perf_counter()
		log_event(logger, "match_jobs_to_resume.started", top_k=top_k, resume_file=resume.file_name)

		if resume.embedding is None:
			log_event(logger, "match_jobs_to_resume.failed", reason="missing_resume_embedding")
			return {"ok": False, "message": "Resume has no embedding. Re-upload after fixing PDF extraction."}

		if top_k < 1:
			log_event(logger, "match_jobs_to_resume.failed", reason="invalid_top_k", top_k=top_k)
			return {"ok": False, "message": "top_k must be at least 1."}

		jobs = self._repo.find_all()
		scored: list[RankedJobMatch] = []
		skipped_no_embedding = 0

		for job in jobs:
			if job.embedding is None:
				skipped_no_embedding += 1
				continue
			try:
				score = cosine_similarity(resume.embedding, job.embedding)
			except (TypeError, ValueError):
				skipped_no_embedding += 1
				continue
			scored.append(RankedJobMatch(job=job, score=score))

		scored.sort(key=lambda match: match.score, reverse=True)
		matches = scored[:top_k]

		result: dict[str, object] = {
			"ok": True,
			"matches": matches,
			"scored_count": len(scored),
			"skipped_no_embedding": skipped_no_embedding,
			"total_jobs": len(jobs),
		}
		if not scored:
			result["message"] = (
				"No jobs with embeddings found. Ingest jobs on the Data Ingestion page first."
			)
			log_event(
				logger,
				"match_jobs_to_resume.completed",
				ok=False,
				total_jobs=len(jobs),
				skipped_no_embedding=skipped_no_embedding,
				duration_ms=round((time.perf_counter() - started) * 1000, 2),
			)
			return result

		top_match = matches[0] if matches else None
		log_event(
			logger,
			"match_jobs_to_resume.completed",
			ok=True,
			top_k=top_k,
			match_count=len(matches),
			scored_count=len(scored),
			skipped_no_embedding=skipped_no_embedding,
			top_job_id=top_match.job.id if top_match else None,
			top_score=round(top_match.score, 4) if top_match else None,
			duration_ms=round((time.perf_counter() - started) * 1000, 2),
		)
		return result
