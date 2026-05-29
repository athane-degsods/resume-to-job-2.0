from __future__ import annotations

from collections.abc import Sequence

from src.adapters.inbound.file_upload.dataframe_job_parser import DataFrameJobParser
from src.domain.entities.Job import Job


class ApiJobParser:
	"""Convert API JSON payloads into Job entities."""

	def __init__(self) -> None:
		self._dataframe_parser = DataFrameJobParser()

	def to_records(self, payload: object) -> list[dict[str, object]]:
		if isinstance(payload, list):
			if not payload or isinstance(payload[0], dict):
				return [dict(record) for record in payload]

		if isinstance(payload, dict):
			for key in ("jobs", "data", "items", "results"):
				value = payload.get(key)
				if isinstance(value, list):
					# map provider-specific fields into our normalized record shape
					raw = self.to_records(value)
					mapped: list[dict[str, object]] = []
					for rec in raw:
						if not isinstance(rec, dict):
							continue
						m: dict[str, object] = {}
						# provider: arbeitnow uses 'slug' and 'company_name'
						m["id"] = rec.get("slug") or rec.get("id") or rec.get("url")
						m["title"] = rec.get("title")
						m["company"] = rec.get("company_name") or rec.get("company")
						m["description"] = rec.get("description") or rec.get("summary") or None
						m["location"] = rec.get("location") or rec.get("remote")
						m["source"] = rec.get("source") or "api"
						# keep original payload for reference
						m["raw"] = rec
						mapped.append(m)
					return mapped

		raise ValueError("API payload must be a list of job records")

	def to_jobs(self, payload: object) -> list[Job]:
		# Use the tolerant conversion that returns jobs and per-record errors.
		jobs, errors = self._dataframe_parser.to_jobs_with_errors_from_records(self.to_records(payload))
		if errors:
			# attach errors information to a ValueError so callers can surface them.
			raise ValueError({"message": "Some records were invalid", "errors": errors})
		return jobs

	def to_jobs_with_errors(self, payload: object) -> tuple[list[Job], list[dict]]:
		return self._dataframe_parser.to_jobs_with_errors_from_records(self.to_records(payload))

	def chunk_jobs(self, jobs: Sequence[Job], batch_size: int = 200) -> list[list[Job]]:
		return self._dataframe_parser.chunk_jobs(jobs, batch_size=batch_size)
