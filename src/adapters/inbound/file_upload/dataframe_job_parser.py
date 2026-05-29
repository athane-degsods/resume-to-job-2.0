from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from src.domain.entities.Job import Job


class DataFrameJobParser:
	"""Convert a pandas DataFrame into Job entities."""

	required_columns = ("id", "title", "company", "description")

    # Normalize column names
	def normalize(self, dataframe: pd.DataFrame) -> pd.DataFrame:
		normalized = dataframe.copy()
		normalized.columns = [str(column).strip().lower() for column in normalized.columns]
		return normalized

    # Convert DataFrame rows into dicts, ensuring required columns are present.
	def to_records(self, dataframe: pd.DataFrame) -> list[dict[str, object]]:
		normalized = self.normalize(dataframe)
		missing = [column for column in self.required_columns if column not in normalized.columns]
		if missing:
			raise ValueError(f"Missing required columns: {', '.join(missing)}")
		return normalized.to_dict(orient="records")

    # Convert records into Job entities, applying basic validation and coercion.
	def to_jobs(self, dataframe: pd.DataFrame) -> list[Job]:
		return self.to_jobs_from_records(self.to_records(dataframe))

	def to_jobs_from_records(self, records: Sequence[dict[str, object]]) -> list[Job]:
		jobs: list[Job] = []
		for record in records:
			job_id = self._text(record.get("id"))
			title = self._text(record.get("title"))
			company = self._text(record.get("company"))
			description = self._text(record.get("description"))
			if not job_id or not title or not company or not description:
				raise ValueError("Each job row must include id, title, company, and description")

			jobs.append(
				Job(
					id=job_id,
					title=title,
					company=company,
					description=description,
					location=self._optional_text(record.get("location")),
					source=self._optional_text(record.get("source")),
				)
			)

		return jobs

	def to_jobs_with_errors_from_records(self, records: Sequence[dict[str, object]]) -> tuple[list[Job], list[dict]]:
		"""Convert records to jobs, collecting per-record errors instead of raising.

		Returns (jobs, errors) where errors is a list of dicts with keys:
		- index: int, position in input
		- missing: list[str], missing required fields
		- record: the original record
		"""
		jobs: list[Job] = []
		errors: list[dict] = []
		for idx, record in enumerate(records):
			job_id = self._text(record.get("id"))
			title = self._text(record.get("title"))
			company = self._text(record.get("company"))
			description = self._text(record.get("description"))
			missing: list[str] = []
			if not job_id:
				missing.append("id")
			if not title:
				missing.append("title")
			if not company:
				missing.append("company")
			if not description:
				missing.append("description")
			if missing:
				errors.append({"index": idx, "missing": missing, "record": record})
				continue
			jobs.append(
				Job(
					id=job_id,
					title=title,
					company=company,
					description=description,
					location=self._optional_text(record.get("location")),
					source=self._optional_text(record.get("source")),
				)
			)
		return jobs, errors

	def to_jobs_with_errors_from_dataframe(self, dataframe: pd.DataFrame) -> tuple[list[Job], list[dict]]:
		return self.to_jobs_with_errors_from_records(self.to_records(dataframe))

	def chunk_jobs(self, jobs: Sequence[Job], batch_size: int = 200) -> list[list[Job]]:
		return [list(jobs[index : index + batch_size]) for index in range(0, len(jobs), batch_size)]

	@staticmethod
	def _text(value: object) -> str:
		if value is None or pd.isna(value):
			return ""
		return str(value).strip()

	@staticmethod
	def _optional_text(value: object) -> str | None:
		text = DataFrameJobParser._text(value)
		return text or None
