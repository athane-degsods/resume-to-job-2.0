import streamlit as st

from src.adapters.inbound.streamlit.resume_pdf_parser import parse_resume_pdf
from src.adapters.outbound.embedding.sentence_transformers_adapter import (
	SentenceTransformersEmbeddingAdapter,
)


def streamlit_app() -> None:
	"""Inbound adapter for the Job Matching page.

	This adapter listens to the user's interaction and only delegates PDF
	parsing to a dedicated inbound adapter.
	"""
	st.title("Job Matching")
	st.caption("Upload a resume PDF to extract text and start matching")

	uploaded_pdf = st.file_uploader("Upload PDF resume", type=["pdf"])
	embedding_service = SentenceTransformersEmbeddingAdapter()

	if uploaded_pdf is None:
		st.info("Upload a PDF resume to continue.")
	else:
		try:
			resume = parse_resume_pdf(uploaded_pdf, embedding_service=embedding_service)
		except Exception as exc:
			st.error(f"Could not extract text from the PDF: {exc}")
			return

		st.session_state.resume = resume
		st.success(f"Uploaded: {resume.file_name}")
		st.write("The PDF was parsed into a Resume domain entity.")
		st.text_area("Extracted resume text", value=resume.text, height=300)
		if resume.embedding is not None:
			st.write(f"Embedding size: {len(resume.embedding)}")
