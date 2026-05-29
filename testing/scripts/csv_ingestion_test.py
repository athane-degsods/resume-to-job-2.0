from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

# ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.adapters.inbound.file_upload.dataframe_job_parser import DataFrameJobParser
from src.application.use_cases.ingest_jobs_batch import IngestJobsBatchUseCase
from src.adapters.outbound.persistence.sqlite_job_repository import SQLiteJobRepository


def main() -> None:
    sample_csv = Path(ROOT) / "testing" / "sample_data" / "sample_jobs.csv"
    assert sample_csv.exists(), f"sample csv not found: {sample_csv}"

    df = pd.read_csv(sample_csv)
    parser = DataFrameJobParser()
    jobs = parser.to_jobs(df)

    db_path = Path(ROOT) / "testing" / "test_sqlite.db"
    # clean up existing
    if db_path.exists():
        db_path.unlink()

    repo = SQLiteJobRepository(db_path)
    usecase = IngestJobsBatchUseCase(repository=repo, batch_size=200)

    result = usecase.execute(jobs)
    print("ingest result:", result)

    # verify rows in DB
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM jobs")
    count = cur.fetchone()[0]
    print("rows in db:", count)
    assert count == len(jobs)

    # cleanup: delete DB file to leave clear environment
    conn.close()
    repo.close()
    if db_path.exists():
        db_path.unlink()
    print("cleanup done")


if __name__ == "__main__":
    main()
