from __future__ import annotations

import math
from dataclasses import dataclass

from src.domain.entities.Job import Job
from src.ports.output.job_repository import JobRepositoryPort

DEFAULT_PAGE_SIZE = 10


@dataclass(frozen=True, slots=True)
class JobDashboardStats:
	total_jobs: int
	jobs_with_embeddings: int

	@property
	def jobs_without_embeddings(self) -> int:
		return self.total_jobs - self.jobs_with_embeddings


@dataclass(frozen=True, slots=True)
class JobDashboardPage:
	jobs: tuple[Job, ...]
	page: int
	page_size: int
	total_jobs: int

	@property
	def total_pages(self) -> int:
		if self.total_jobs == 0:
			return 1
		return max(1, math.ceil(self.total_jobs / self.page_size))


class GetJobDashboardUseCase:
	"""Read-only dashboard queries over persisted jobs."""

	def __init__(self, repository: JobRepositoryPort) -> None:
		self._repo = repository

	def get_stats(self) -> JobDashboardStats:
		total = self._repo.count()
		with_embeddings = self._repo.count_with_embeddings()
		return JobDashboardStats(total_jobs=total, jobs_with_embeddings=with_embeddings)

	def get_page(self, page: int, *, page_size: int = DEFAULT_PAGE_SIZE) -> JobDashboardPage:
		if page_size < 1:
			raise ValueError("page_size must be at least 1.")
		total = self._repo.count()
		total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
		safe_page = min(max(page, 1), total_pages)
		offset = (safe_page - 1) * page_size
		jobs = self._repo.find_page(offset=offset, limit=page_size)
		return JobDashboardPage(
			jobs=tuple(jobs),
			page=safe_page,
			page_size=page_size,
			total_jobs=total,
		)
