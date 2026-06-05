from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from src.adapters.inbound.file_upload.dataframe_job_parser import DataFrameJobParser
from src.adapters.outbound.embedding.sentence_transformers_adapter import (
	SentenceTransformersEmbeddingAdapter,
)
from src.adapters.outbound.llm.openai_compatible_adapter import OpenAICompatibleRecommendationAdapter
from src.adapters.outbound.logging.structured_logging import configure_logging, log_event, get_logger
from src.adapters.outbound.persistence.sqlite_job_repository import SQLiteJobRepository
from src.application.use_cases.ingest_jobs_batch import IngestJobsBatchUseCase
from src.application.use_cases.match_jobs_to_resume import MatchJobsToResumeUseCase, RankedJobMatch
from src.application.use_cases.recommend_jobs_with_ai import RecommendJobsWithAIUseCase
from src.domain.entities.Resume import Resume

logger = get_logger(__name__)

DEFAULT_JOBS_CSV = ROOT / "testing" / "sample_data" / "sample_jobs.csv"
DEFAULT_RESUME_TXT = ROOT / "testing" / "sample_data" / "sample_resume.txt"
DEFAULT_OUTPUT_DIR = ROOT / "testing" / "output"


def _ranked_matches_to_json(matches: list[RankedJobMatch]) -> list[dict[str, object]]:
	return [
		{
			"rank": index + 1,
			"job_id": match.job.id,
			"title": match.job.title,
			"company": match.job.company,
			"cosine_score": round(match.score, 4),
		}
		for index, match in enumerate(matches)
	]


def _recommendation_to_json(result: dict[str, object]) -> dict[str, object] | None:
	recommendation = result.get("recommendation")
	if recommendation is None:
		return None
	return {
		"resume_score": recommendation.resume_score,
		"resume_feedback": recommendation.resume_feedback,
		"top_jobs": [
			{
				"job_id": job.job_id,
				"title": job.title,
				"company": job.company,
				"fit_score": job.fit_score,
				"rationale": job.rationale,
			}
			for job in recommendation.top_jobs
		],
	}


def run_eval(
	*,
	jobs_csv: Path,
	resume_txt: Path,
	db_path: Path,
	output_dir: Path,
	top_k: int,
	run_ai: bool,
	expected_top_job_id: str | None,
) -> Path:
	configure_logging()
	started = time.perf_counter()
	output_dir.mkdir(parents=True, exist_ok=True)

	if db_path.exists():
		db_path.unlink()

	report: dict[str, object] = {
		"run_at": datetime.now(timezone.utc).isoformat(),
		"jobs_csv": str(jobs_csv),
		"resume_txt": str(resume_txt),
		"db_path": str(db_path),
		"top_k": top_k,
		"steps": {},
	}

	# Ingest
	df = pd.read_csv(jobs_csv)
	parser = DataFrameJobParser()
	jobs = parser.to_jobs(df)
	repo = SQLiteJobRepository(db_path)
	embedding_service = SentenceTransformersEmbeddingAdapter()
	ingest_use_case = IngestJobsBatchUseCase(
		repository=repo,
		batch_size=200,
		embedding_service=embedding_service,
	)
	ingest_result = ingest_use_case.execute(jobs)
	report["steps"]["ingest"] = ingest_result

	# Resume embedding
	resume_text = resume_txt.read_text(encoding="utf-8")
	vectors = embedding_service.embed_texts([resume_text])
	resume = Resume(
		file_name=resume_txt.name,
		text=resume_text,
		embedding=tuple(vectors[0]) if vectors else None,
	)
	report["steps"]["resume"] = {
		"file_name": resume.file_name,
		"text_length": len(resume_text),
		"has_embedding": resume.embedding is not None,
	}

	# Match
	match_use_case = MatchJobsToResumeUseCase(repository=repo)
	match_result = match_use_case.execute(resume, top_k=top_k)
	matches = match_result.get("matches", [])
	match_rows = _ranked_matches_to_json(
		[m for m in matches if isinstance(m, RankedJobMatch)]
	)
	report["steps"]["match"] = {
		"ok": match_result.get("ok"),
		"message": match_result.get("message"),
		"scored_count": match_result.get("scored_count"),
		"matches": match_rows,
	}
	if expected_top_job_id and match_rows:
		report["steps"]["match"]["expected_top_job_id"] = expected_top_job_id
		report["steps"]["match"]["expected_in_top_k"] = any(
			row["job_id"] == expected_top_job_id for row in match_rows
		)
		report["steps"]["match"]["expected_rank"] = next(
			(row["rank"] for row in match_rows if row["job_id"] == expected_top_job_id),
			None,
		)

	# AI (optional)
	ai_report: dict[str, object] = {"skipped": True, "reason": "disabled"}
	if run_ai:
		api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
		if not api_key:
			ai_report = {"skipped": True, "reason": "no_api_key"}
		elif not match_rows:
			ai_report = {"skipped": True, "reason": "no_filtered_matches"}
		else:
			candidate_jobs = [m.job for m in matches if isinstance(m, RankedJobMatch)]
			ai_service = OpenAICompatibleRecommendationAdapter()
			ai_use_case = RecommendJobsWithAIUseCase(recommendation_service=ai_service)
			ai_result = ai_use_case.execute(resume, candidate_jobs)
			ai_report = {
				"skipped": False,
				"ok": ai_result.get("ok"),
				"message": ai_result.get("message"),
				"candidate_count": ai_result.get("candidate_count"),
				"recommendation": _recommendation_to_json(ai_result),
			}
	report["steps"]["ai"] = ai_report

	report["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)

	timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
	output_path = output_dir / f"pipeline_eval_{timestamp}.json"
	output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

	log_event(logger, "pipeline_eval.saved", output_path=str(output_path), duration_ms=report["duration_ms"])
	repo.close()
	return output_path


def main() -> None:
	parser = argparse.ArgumentParser(description="Offline pipeline evaluation for resume-to-job 2.0")
	parser.add_argument("--jobs-csv", type=Path, default=DEFAULT_JOBS_CSV)
	parser.add_argument("--resume-txt", type=Path, default=DEFAULT_RESUME_TXT)
	parser.add_argument("--db-path", type=Path, default=ROOT / "testing" / "output" / "eval.db")
	parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
	parser.add_argument("--top-k", type=int, default=5)
	parser.add_argument("--run-ai", action="store_true", help="Call AI provider (requires API key in env)")
	parser.add_argument(
		"--expected-top-job-id",
		default="JOB-002",
		help="Job id expected near top rank for the sample resume (ML Engineer at Nova AI)",
	)
	args = parser.parse_args()

	output_path = run_eval(
		jobs_csv=args.jobs_csv,
		resume_txt=args.resume_txt,
		db_path=args.db_path,
		output_dir=args.output_dir,
		top_k=args.top_k,
		run_ai=args.run_ai,
		expected_top_job_id=args.expected_top_job_id,
	)
	print(f"Evaluation report written to: {output_path}")


if __name__ == "__main__":
	main()
