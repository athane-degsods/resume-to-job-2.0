from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from src.domain.entities.Job import Job
from src.domain.entities.Recommendation import ResumeRecommendation
from src.domain.entities.Resume import Resume


class ResumeRecommendationServicePort(Protocol):
	"""Contract for LLM-backed resume scoring and job recommendations."""

	def recommend(self, resume: Resume, candidate_jobs: Sequence[Job]) -> ResumeRecommendation:
		"""Score the resume and pick top applications from the given job list."""
		raise NotImplementedError
