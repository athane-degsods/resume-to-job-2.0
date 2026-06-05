from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RecommendedJob:
	"""A job the AI recommends the candidate apply to."""

	job_id: str
	title: str
	company: str
	fit_score: float
	rationale: str


@dataclass(frozen=True, slots=True)
class ResumeRecommendation:
	"""AI assessment of a resume and top job picks."""

	resume_score: float
	resume_feedback: str
	top_jobs: tuple[RecommendedJob, ...]
