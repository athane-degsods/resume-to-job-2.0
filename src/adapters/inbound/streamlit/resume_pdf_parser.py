from __future__ import annotations

from io import BytesIO

try:
	from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency during editing
	PdfReader = None  # type: ignore

from src.ports.output.embedding_service import EmbeddingServicePort
from src.domain.entities.Resume import Resume


def extract_text_from_pdf(pdf_file: BytesIO) -> str:
	"""Extract text from an uploaded PDF file-like object."""
	if PdfReader is None:
		raise RuntimeError("pypdf is not installed. Install dependencies to enable PDF extraction.")

	reader = PdfReader(pdf_file)
	parts: list[str] = []
	for page in reader.pages:
		text = page.extract_text() or ""
		text = text.strip()
		if text:
			parts.append(text)
	return "\n\n".join(parts)


def parse_resume_pdf(
	uploaded_pdf: BytesIO,
	embedding_service: EmbeddingServicePort | None = None,
) -> Resume:
	"""Convert an uploaded PDF into a Resume domain entity.

	If an embedding service is provided, the extracted text is embedded and the
	vector is stored on the returned resume object.
	"""
	text = extract_text_from_pdf(uploaded_pdf)
	embedding = None
	if embedding_service is not None and text.strip():
		vectors = embedding_service.embed_texts([text])
		if vectors:
			embedding = tuple(vectors[0])
	return Resume(file_name=getattr(uploaded_pdf, "name", "resume.pdf"), text=text, embedding=embedding)
