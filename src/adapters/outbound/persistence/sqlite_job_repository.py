from __future__ import annotations

import sqlite3
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from src.domain.entities.Job import Job
from src.ports.output.job_repository import JobRepositoryPort


class SQLiteJobRepository(JobRepositoryPort):
    """Simple SQLite-backed repository adapter.

    Uses `INSERT ... ON CONFLICT(id) DO UPDATE` for upserts.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        self._conn.row_factory = sqlite3.Row
        self._ensure_table()

    def _ensure_table(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                description TEXT,
                location TEXT,
                source TEXT,
                embedding TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()
        # Ensure new columns exist for schema migrations (non-destructive)
        cur.execute("PRAGMA table_info(jobs)")
        existing_cols = {row[1] for row in cur.fetchall()}
        if "description" not in existing_cols:
            cur.execute("ALTER TABLE jobs ADD COLUMN description TEXT")
        if "embedding" not in existing_cols:
            cur.execute("ALTER TABLE jobs ADD COLUMN embedding TEXT")
        self._conn.commit()

    def upsert(self, job: Job) -> None:
        sql = """
        INSERT INTO jobs (id, title, company, location, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            company=excluded.company,
            location=excluded.location,
            source=excluded.source,
            updated_at=CURRENT_TIMESTAMP
        """
        params = (job.id, job.title, job.company, job.location, job.source)
        # extended columns: description and embedding may be present
        if getattr(job, "description", None) is not None or getattr(job, "embedding", None) is not None:
            sql = """
            INSERT INTO jobs (id, title, company, description, location, source, embedding, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                company=excluded.company,
                description=excluded.description,
                location=excluded.location,
                source=excluded.source,
                embedding=excluded.embedding,
                updated_at=CURRENT_TIMESTAMP
            """
            embedding_json = json.dumps(list(job.embedding)) if getattr(job, "embedding", None) is not None else None
            params = (job.id, job.title, job.company, getattr(job, "description", None), job.location, job.source, embedding_json)

        self._conn.execute(sql, params)
        self._conn.commit()

    def upsert_many(self, jobs: Sequence[Job]) -> None:
        sql = """
        INSERT INTO jobs (id, title, company, description, location, source, embedding, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            company=excluded.company,
            description=excluded.description,
            location=excluded.location,
            source=excluded.source,
            embedding=excluded.embedding,
            updated_at=CURRENT_TIMESTAMP
        """
        params = []
        for j in jobs:
            embedding_json = json.dumps(list(j.embedding)) if getattr(j, "embedding", None) is not None else None
            params.append((j.id, j.title, j.company, getattr(j, "description", None), j.location, j.source, embedding_json))
        self._conn.executemany(sql, params)
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def count(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM jobs")
        row = cur.fetchone()
        return int(row[0]) if row is not None else 0

    def find_all(self) -> list[Job]:
        return self.find_page(offset=0, limit=max(self.count(), 1) if self.count() > 0 else 0)

    def count_with_embeddings(self) -> int:
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) FROM jobs
            WHERE embedding IS NOT NULL AND TRIM(embedding) != ''
            """
        )
        row = cur.fetchone()
        return int(row[0]) if row is not None else 0

    def find_page(self, *, offset: int, limit: int) -> list[Job]:
        if limit < 1:
            return []
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT id, title, company, description, location, source, embedding
            FROM jobs
            ORDER BY updated_at DESC, title ASC, id ASC
            LIMIT ? OFFSET ?
            """,
            (limit, max(offset, 0)),
        )
        return [self._row_to_job(row) for row in cur.fetchall()]

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        embedding_raw = row["embedding"]
        embedding = None
        if embedding_raw:
            parsed = json.loads(embedding_raw)
            embedding = tuple(float(value) for value in parsed)

        description = row["description"]
        if not description:
            description = ""

        return Job(
            id=row["id"],
            title=row["title"],
            company=row["company"],
            description=description,
            location=row["location"],
            source=row["source"],
            embedding=embedding,
        )
