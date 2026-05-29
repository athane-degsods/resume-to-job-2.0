#!/usr/bin/env python3
"""Check whether stored jobs have embeddings for their descriptions.

Usage:
    python testing/scripts/check_job_embeddings.py

Optional environment variable:
    JOB_DB_PATH   SQLite database path (default: data/jobs.db)
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("JOB_DB_PATH", "data/jobs.db"))


def main() -> int:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, title, description, embedding
        FROM jobs
        ORDER BY created_at DESC, id ASC
        """
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("No jobs found in the database.")
        return 0

    embedded = 0
    missing = 0

    print(f"Checked {len(rows)} job(s) in {DB_PATH}")
    for row in rows:
        description = row["description"]
        embedding = row["embedding"]
        has_description = bool(description and str(description).strip())
        has_embedding = bool(embedding and str(embedding).strip())

        if has_description and has_embedding:
            embedded += 1
            status = "embedded"
        elif has_description:
            missing += 1
            status = "missing embedding"
        else:
            status = "missing description"

        print(
            json.dumps(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "status": status,
                },
                ensure_ascii=False,
            )
        )

    print(f"Summary: {embedded} embedded, {missing} missing embedding")
    return 0 if missing == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
