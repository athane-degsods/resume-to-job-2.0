from __future__ import annotations

import json
import os
import re
from collections.abc import Sequence

import requests

from src.domain.entities.Job import Job
from src.domain.entities.Recommendation import RecommendedJob, ResumeRecommendation
from src.domain.entities.Resume import Resume
from src.ports.output.resume_recommendation_service import ResumeRecommendationServicePort

_MAX_DESCRIPTION_CHARS = 600
_MAX_RESUME_CHARS = 12_000


class OpenAICompatibleRecommendationAdapter(ResumeRecommendationServicePort):
	"""Call an OpenAI-compatible chat completions API for resume scoring."""

	def __init__(
		self,
		*,
		api_base: str | None = None,
		api_key: str | None = None,
		model: str | None = None,
		timeout_seconds: int = 90,
	) -> None:
		base = (api_base or os.getenv("AI_API_BASE") or "https://api.openai.com/v1").rstrip("/")
		self._chat_url = f"{base}/chat/completions"
		self._api_key = (
			api_key
			or os.getenv("AI_API_KEY")
			or os.getenv("GEMINI_API_KEY")
			or os.getenv("OPENAI_API_KEY")
		)
		self._model = model or os.getenv("AI_MODEL") or "gpt-4o-mini"
		self._timeout_seconds = timeout_seconds
		self._is_gemini = "generativelanguage.googleapis.com" in self._chat_url

	def recommend(self, resume: Resume, candidate_jobs: Sequence[Job]) -> ResumeRecommendation:
		if not self._api_key:
			raise ValueError("AI API key is missing. Set AI_API_KEY or OPENAI_API_KEY.")
		if not candidate_jobs:
			raise ValueError("At least one candidate job is required for AI recommendations.")

		payload = self._build_request_body(resume, candidate_jobs)
		try:
			response = requests.post(
				self._chat_url,
				headers={
					"Authorization": f"Bearer {self._api_key}",
					"Content-Type": "application/json",
				},
				json=payload,
				timeout=self._timeout_seconds,
			)
			response.raise_for_status()
		except requests.HTTPError as exc:
			detail = exc.response.text.strip() if exc.response is not None else str(exc)
			status = exc.response.status_code if exc.response is not None else "unknown"
			message = f"AI API request failed ({status}): {detail}"
			if status == 500 and self._is_gemini:
				message += (
					" Gemini often returns 500 for structured-output quirks, oversized prompts, "
					"or transient outages. Retry in a moment; if it persists, try model "
					"gemini-2.0-flash and a shorter resume."
				)
			raise ValueError(message) from exc
		except requests.RequestException as exc:
			raise ValueError(f"AI API request failed: {exc}") from exc
		content = self._extract_message_content(response.json())
		parsed = _parse_json_content(content)
		target_job_count = min(3, len(candidate_jobs))
		return _to_recommendation(parsed, candidate_jobs, target_job_count=target_job_count)

	def _build_request_body(self, resume: Resume, candidate_jobs: Sequence[Job]) -> dict[str, object]:
		target_job_count = min(3, len(candidate_jobs))
		resume_text = resume.text.strip()[:_MAX_RESUME_CHARS]
		jobs_payload = [
			{
				"job_id": job.id,
				"title": job.title,
				"company": job.company,
				"location": job.location,
				"description": (job.description or "")[:_MAX_DESCRIPTION_CHARS],
			}
			for job in candidate_jobs
		]

		job_count_rule = (
			f"exactly {target_job_count} job(s)"
			if target_job_count == len(candidate_jobs)
			else f"up to {target_job_count} jobs (only pick from the list provided)"
		)
		user_prompt = (
			f"Evaluate the resume and recommend {job_count_rule} from the candidate list.\n"
			"The candidate list is already pre-filtered by relevance — only use those job ids.\n"
			"Respond with JSON only, no markdown, using this schema:\n"
			"{\n"
			'  "resume_score": <number 0-100>,\n'
			'  "resume_feedback": "<short paragraph on resume strengths and gaps>",\n'
			'  "top_jobs": [\n'
			"    {\n"
			'      "job_id": "<id from candidate list>",\n'
			'      "fit_score": <number 0-100>,\n'
			'      "rationale": "<why this job fits the resume>"\n'
			"    }\n"
			"  ]\n"
			"}\n"
			"Rules:\n"
			"- resume_score measures overall resume quality and market readiness.\n"
			f"- top_jobs must contain at most {target_job_count} entries and only use ids from the candidate list.\n"
			"- If fewer than 3 candidates are provided, recommend only those available.\n"
			"- Order top_jobs from best fit to weakest fit.\n\n"
			f"Resume:\n{resume_text}\n\n"
			f"Candidate jobs:\n{json.dumps(jobs_payload, ensure_ascii=False)}"
		)

		body: dict[str, object] = {
			"model": self._model,
			"temperature": 0.2,
			"messages": [
				{
					"role": "system",
					"content": (
						"You are an expert career coach. "
						"Return strict JSON only and never invent job ids outside the candidate list."
					),
				},
				{"role": "user", "content": user_prompt},
			],
		}
		# Gemini's OpenAI-compat layer often 500s on response_format; prompt-only JSON works better.
		if not self._is_gemini:
			body["response_format"] = {"type": "json_object"}
		else:
			body["max_tokens"] = 4096
		return body

	def _extract_message_content(self, response_json: object) -> str:
		if not isinstance(response_json, dict):
			raise ValueError("Unexpected AI API response format.")
		choices = response_json.get("choices")
		if not isinstance(choices, list) or not choices:
			raise ValueError("AI API returned no choices.")
		first = choices[0]
		if not isinstance(first, dict):
			raise ValueError("AI API choice payload is invalid.")
		message = first.get("message")
		if not isinstance(message, dict):
			raise ValueError("AI API message payload is invalid.")
		content = message.get("content")
		if not isinstance(content, str) or not content.strip():
			raise ValueError("AI API returned empty content.")
		return content.strip()


def _parse_json_content(content: str) -> dict[str, object]:
	text = content.strip()
	fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
	if fence_match:
		text = fence_match.group(1).strip()
	parsed = json.loads(text)
	if not isinstance(parsed, dict):
		raise ValueError("AI response JSON must be an object.")
	return parsed


def _to_recommendation(
	parsed: dict[str, object],
	candidate_jobs: Sequence[Job],
	*,
	target_job_count: int,
) -> ResumeRecommendation:
	jobs_by_id = {job.id: job for job in candidate_jobs}

	try:
		resume_score = float(parsed["resume_score"])
		resume_feedback = str(parsed["resume_feedback"]).strip()
		raw_top_jobs = parsed["top_jobs"]
	except (KeyError, TypeError, ValueError) as exc:
		raise ValueError("AI response is missing required fields.") from exc

	if not resume_feedback:
		raise ValueError("AI response did not include resume_feedback.")

	top_jobs: list[RecommendedJob] = []
	if not isinstance(raw_top_jobs, list):
		raise ValueError("AI response top_jobs must be a list.")

	for item in raw_top_jobs:
		if len(top_jobs) >= target_job_count:
			break
		if not isinstance(item, dict):
			continue
		job_id = str(item.get("job_id", "")).strip()
		job = jobs_by_id.get(job_id)
		if job is None:
			continue
		try:
			fit_score = float(item["fit_score"])
			rationale = str(item["rationale"]).strip()
		except (KeyError, TypeError, ValueError):
			continue
		if not rationale:
			continue
		top_jobs.append(
			RecommendedJob(
				job_id=job.id,
				title=job.title,
				company=job.company,
				fit_score=fit_score,
				rationale=rationale,
			)
		)

	if not top_jobs:
		raise ValueError(
			f"AI did not return valid job recommendations from the {len(candidate_jobs)} candidate(s)."
		)

	return ResumeRecommendation(
		resume_score=resume_score,
		resume_feedback=resume_feedback,
		top_jobs=tuple(top_jobs),
	)
