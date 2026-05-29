from __future__ import annotations

import os

import requests


def fetch_jobs(endpoint: str, api_key: str | None = None, header_name: str = "X-API-Key") -> object:
	"""Fetch a JSON payload from an API endpoint using an API key header."""
	resolved_api_key = api_key or os.getenv("JOB_API_KEY")
	headers = {}
	if resolved_api_key:
		headers[header_name] = resolved_api_key

	response = requests.get(endpoint, headers=headers, timeout=30)
	response.raise_for_status()
	return response.json()
