from __future__ import annotations

import time
from collections.abc import Sequence

from src.adapters.outbound.logging.structured_logging import get_logger, log_event
from src.domain.entities.Job import Job
from src.domain.entities.Recommendation import ResumeRecommendation
from src.domain.entities.Resume import Resume
from src.ports.output.resume_recommendation_service import ResumeRecommendationServicePort

logger = get_logger(__name__)


class RecommendJobsWithAIUseCase:
	"""Score a resume with an LLM using pre-filtered cosine match candidates."""

	def __init__(self, recommendation_service: ResumeRecommendationServicePort) -> None:
		self._recommendation_service = recommendation_service

	def execute(self, resume: Resume, candidate_jobs: Sequence[Job]) -> dict[str, object]:
		started = time.perf_counter()
		log_event(
			logger,
			"recommend_jobs_with_ai.started",
			resume_file=resume.file_name,
			candidate_count=len(candidate_jobs),
		)

		if not resume.text.strip():
			log_event(logger, "recommend_jobs_with_ai.failed", reason="empty_resume_text")
			return {"ok": False, "message": "Resume text is empty. Upload a readable PDF first."}

		if not candidate_jobs:
			log_event(logger, "recommend_jobs_with_ai.failed", reason="no_candidates")
			return {
				"ok": False,
				"message": "No filtered jobs to analyze. Run Find Matches first.",
			}

		try:
			ai_started = time.perf_counter()
			recommendation = self._recommendation_service.recommend(resume, candidate_jobs)
			log_event(
				logger,
				"recommend_jobs_with_ai.provider_completed",
				ai_duration_ms=round((time.perf_counter() - ai_started) * 1000, 2),
				resume_score=recommendation.resume_score,
				recommendation_count=len(recommendation.top_jobs),
			)
		except ValueError as exc:
			log_event(
				logger,
				"recommend_jobs_with_ai.failed",
				reason="provider_error",
				error=str(exc),
				duration_ms=round((time.perf_counter() - started) * 1000, 2),
			)
			return {"ok": False, "message": str(exc)}

		log_event(
			logger,
			"recommend_jobs_with_ai.completed",
			ok=True,
			candidate_count=len(candidate_jobs),
			resume_score=recommendation.resume_score,
			recommendation_count=len(recommendation.top_jobs),
			duration_ms=round((time.perf_counter() - started) * 1000, 2),
		)
		return {
			"ok": True,
			"recommendation": recommendation,
			"candidate_count": len(candidate_jobs),
		}
