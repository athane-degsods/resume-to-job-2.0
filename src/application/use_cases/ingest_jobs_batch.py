from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import replace

from src.adapters.outbound.logging.structured_logging import get_logger, log_event
from src.domain.entities.Job import Job
from src.ports.output.embedding_service import EmbeddingServicePort
from src.ports.output.job_repository import JobRepositoryPort

logger = get_logger(__name__)


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
		started = time.perf_counter()
		input_count = len(jobs)
		log_event(
			logger,
			"ingest_jobs_batch.started",
			input_count=input_count,
			batch_size=self._batch_size,
			embeddings_enabled=self._embedding_service is not None,
		)

		unique_jobs = list({job.id: job for job in jobs}.values())
		if self._embedding_service is not None and unique_jobs:
			embed_started = time.perf_counter()
			texts = [job.description for job in unique_jobs]
			embeddings = self._embedding_service.embed_texts(texts)
			unique_jobs = [
				replace(job, embedding=tuple(float(value) for value in embedding))
				for job, embedding in zip(unique_jobs, embeddings)
			]
			log_event(
				logger,
				"ingest_jobs_batch.embeddings_built",
				job_count=len(unique_jobs),
				duration_ms=round((time.perf_counter() - embed_started) * 1000, 2),
			)

		batches = [
			unique_jobs[index : index + self._batch_size]
			for index in range(0, len(unique_jobs), self._batch_size)
		]

		for batch in batches:
			self._repo.upsert_many(batch)

		result: dict[str, object] = {
			"ok": True,
			"count": len(unique_jobs),
			"batch_size": self._batch_size,
			"batches": len(batches),
		}
		log_event(
			logger,
			"ingest_jobs_batch.completed",
			ok=True,
			input_count=input_count,
			unique_count=len(unique_jobs),
			batches=len(batches),
			duration_ms=round((time.perf_counter() - started) * 1000, 2),
		)
		return result
