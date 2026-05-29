from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from src.domain.entities.Job import Job
from src.ports.output.embedding_service import EmbeddingServicePort
from src.ports.output.job_repository import JobRepositoryPort


class IngestJobsBatchUseCase:
	"""Ingest a batch of jobs in chunks of 200."""

	def __init__(
		self,
		repository: JobRepositoryPort,
		batch_size: int = 200,
		embedding_service: EmbeddingServicePort | None = None,
	) -> None:
		self._repo = repository
		self._batch_size = batch_size
		self._embedding_service = embedding_service

	def execute(self, jobs: Sequence[Job]) -> dict[str, object]:
		unique_jobs = list({job.id: job for job in jobs}.values())
		if self._embedding_service is not None and unique_jobs:
			texts = [job.description for job in unique_jobs]
			embeddings = self._embedding_service.embed_texts(texts)
			unique_jobs = [
				replace(job, embedding=tuple(float(value) for value in embedding))
				for job, embedding in zip(unique_jobs, embeddings)
			]
		batches = [
			unique_jobs[index : index + self._batch_size]
			for index in range(0, len(unique_jobs), self._batch_size)
		]

		for batch in batches:
			self._repo.upsert_many(batch)

		return {
			"ok": True,
			"count": len(unique_jobs),
			"batch_size": self._batch_size,
			"batches": len(batches),
		}
