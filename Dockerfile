# resume-to-job-2.0 — container image for local / institutional deployment demos
FROM python:3.11-slim

ARG APP_VERSION=2.0
ENV APP_VERSION=${APP_VERSION}
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV JOB_DB_PATH=/app/data/jobs.db

WORKDIR /app

# System deps for sentence-transformers / wheels
RUN apt-get update \
	&& apt-get install -y --no-install-recommends build-essential \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model so runtime does not depend on Hugging Face network
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

RUN mkdir -p /app/data

EXPOSE 8501

LABEL org.opencontainers.image.title="resume-to-job" \
	org.opencontainers.image.version="${APP_VERSION}"

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
	CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
