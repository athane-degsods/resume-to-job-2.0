from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any


class JsonLogFormatter(logging.Formatter):
	"""Emit one JSON object per log line for pipelines and containers."""

	def format(self, record: logging.LogRecord) -> str:
		payload: dict[str, Any] = {
			"timestamp": datetime.now(timezone.utc).isoformat(),
			"level": record.levelname,
			"logger": record.name,
			"message": record.getMessage(),
		}
		event = getattr(record, "event", None)
		if event:
			payload["event"] = event
		fields = getattr(record, "fields", None)
		if isinstance(fields, dict):
			payload["fields"] = fields
		if record.exc_info:
			payload["exception"] = self.formatException(record.exc_info)
		return json.dumps(payload, ensure_ascii=False)


def configure_logging(*, level: str | None = None) -> None:
	"""Configure root logger once (stdout JSON lines)."""
	resolved = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
	root = logging.getLogger()
	if getattr(root, "_resume_to_job_configured", False):
		return

	root.setLevel(resolved)
	handler = logging.StreamHandler(sys.stdout)
	handler.setFormatter(JsonLogFormatter())
	root.handlers.clear()
	root.addHandler(handler)
	root._resume_to_job_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
	configure_logging()
	return logging.getLogger(name)


def log_event(
	logger: logging.Logger,
	event: str,
	*,
	level: int = logging.INFO,
	**fields: Any,
) -> None:
	logger.log(level, event, extra={"event": event, "fields": fields})
