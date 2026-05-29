from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from src.domain.entities.Job import Job


class JobRepositoryPort(Protocol):
	"""Contract for saving jobs.

	The domain/application layer depends on this interface, not on Prisma or SQL.
	"""

	def upsert(self, job: Job) -> None:
		"""Insert or update one job record."""
		raise NotImplementedError

	def upsert_many(self, jobs: Sequence[Job]) -> None:
		"""Insert or update a batch of job records."""
		raise NotImplementedError
