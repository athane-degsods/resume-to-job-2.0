# Observability and offline evaluation

Lightweight MLOps-style signals for resume-to-job **2.0** — no Prometheus or MLflow required.

## Runtime logging (monitoring)

Use cases emit **JSON lines** to stdout:

| Event | When |
|-------|------|
| `ingest_jobs_batch.started` / `.completed` | Job ingest + embedding |
| `match_jobs_to_resume.started` / `.completed` | Cosine ranking |
| `recommend_jobs_with_ai.started` / `.completed` | AI recommendations |

Each line includes `duration_ms` and step-specific fields (`top_job_id`, `candidate_count`, etc.).

**Streamlit:** logging is enabled from `app.py` on startup.

**Level:** set `LOG_LEVEL=DEBUG` (default `INFO`).

**Docker (later):** `docker logs <container>` will show the same JSON lines.

Example:

```json
{"timestamp": "...", "level": "INFO", "event": "match_jobs_to_resume.completed", "fields": {"top_k": 5, "top_job_id": "JOB-002", "top_score": 0.61, "duration_ms": 12.4}}
```

Implementation: `src/adapters/outbound/logging/structured_logging.py`

## Offline evaluation (quality checks)

Script runs the pipeline without the UI and writes a JSON report under `testing/output/`.

```bash
# Match + ingest only (no API key)
python testing/scripts/pipeline_eval.py

# Include AI step when keys are set
set GEMINI_API_KEY=your-key
python testing/scripts/pipeline_eval.py --run-ai
```

Options:

- `--top-k` — cosine shortlist size (default 5)
- `--expected-top-job-id` — checks whether that id appears in the shortlist (default `JOB-002` for the sample resume)
- `--jobs-csv` / `--resume-txt` — alternate fixtures

Reports look like `testing/output/pipeline_eval_20260101T120000Z.json` with steps `ingest`, `match`, `ai`, and timings.

## How this fits your report

| Concern | Mechanism |
|---------|-----------|
| **Operations / MLOps** | Structured logs on every pipeline step |
| **Quality / evaluation** | `pipeline_eval.py` + saved JSON artifacts |
| **Future 2.1** | Export logs to a file, Dashboard KPIs, or MLflow — optional |

## Sample data

- `testing/sample_data/sample_jobs.csv` — jobs with descriptions (required for embeddings)
- `testing/sample_data/sample_resume.txt` — ML-focused resume aligned with `JOB-002` (ML Engineer, Nova AI)
