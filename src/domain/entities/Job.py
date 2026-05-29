from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Job:
	"""Core job entity.

	This keeps the business meaning of a job record, without any database logic.
	"""

	id: str
	title: str
	company: str
	description: str
	location: str | None = None
	source: str | None = None
	embedding: tuple[float, ...] | None = None
