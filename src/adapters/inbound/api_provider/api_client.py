from __future__ import annotations

import os
from urllib.parse import urljoin

import requests

_LIST_KEYS = ("data", "jobs", "items", "results")


def _request_json(url: str, api_key: str | None, header_name: str) -> object:
	headers: dict[str, str] = {}
	if api_key:
		headers[header_name] = api_key
	response = requests.get(url, headers=headers, timeout=60)
	response.raise_for_status()
	return response.json()


def _extract_list_payload(payload: object) -> list[object]:
	if isinstance(payload, list):
		return list(payload)
	if isinstance(payload, dict):
		for key in _LIST_KEYS:
			value = payload.get(key)
			if isinstance(value, list):
				return list(value)
	raise ValueError("API payload must contain a list of job records (e.g. under 'data').")


def _next_page_url(payload: object, current_url: str) -> str | None:
	if not isinstance(payload, dict):
		return None

	links = payload.get("links")
	if isinstance(links, dict):
		for key in ("next", "next_page"):
			candidate = links.get(key)
			if isinstance(candidate, str) and candidate.strip():
				return _resolve_url(current_url, candidate.strip())

	meta = payload.get("meta")
	if isinstance(meta, dict):
		for key in ("next", "next_page_url", "next_url"):
			candidate = meta.get(key)
			if isinstance(candidate, str) and candidate.strip():
				return _resolve_url(current_url, candidate.strip())

	return None


def _resolve_url(current_url: str, next_ref: str) -> str:
	if next_ref.startswith("http://") or next_ref.startswith("https://"):
		return next_ref
	return urljoin(current_url, next_ref)


def fetch_jobs(
	endpoint: str,
	api_key: str | None = None,
	header_name: str = "X-API-Key",
	*,
	max_jobs: int | None = None,
) -> tuple[object, int]:
	"""Fetch job JSON from an API endpoint.

	When ``max_jobs`` is set, follows pagination (e.g. Arbeitnow ``links.next``)
	until enough records are collected or there is no next page.

	Returns ``(payload, pages_fetched)`` where ``payload`` is shaped for ``ApiJobParser``
	(merged ``{"data": [...]}`` when paginating).
	"""
	resolved_api_key = api_key or os.getenv("JOB_API_KEY")

	if max_jobs is not None and max_jobs < 1:
		raise ValueError("max_jobs must be at least 1.")

	if max_jobs is None:
		return _request_json(endpoint, resolved_api_key, header_name), 1

	merged: list[object] = []
	url: str | None = endpoint
	pages_fetched = 0

	while url and len(merged) < max_jobs:
		payload = _request_json(url, resolved_api_key, header_name)
		pages_fetched += 1
		merged.extend(_extract_list_payload(payload))
		if len(merged) >= max_jobs:
			break
		url = _next_page_url(payload, url)

	return {"data": merged[:max_jobs]}, pages_fetched
