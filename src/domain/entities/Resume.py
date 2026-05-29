from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Resume:
	"""Core resume entity.

	This stores the uploaded resume as extracted text, its embedding, and its
	original file name.
	"""

	file_name: str
	text: str
	embedding: tuple[float, ...] | None = None
