#!/usr/bin/env python3
"""Quick helper to clear the `jobs` table in the SQLite DB used by the app.

Usage:
    python testing/scripts/clear_jobs_table.py

Optionally set JOB_DB_PATH env var to point to a different DB file.
"""
from pathlib import Path
import os
import sqlite3
import sys

DB_PATH = Path(os.getenv("JOB_DB_PATH", "data/jobs.db"))
if not DB_PATH.exists():
    print(f"DB not found at {DB_PATH!s}. Nothing to clear.")
    sys.exit(0)

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()
# check table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")
if cur.fetchone() is None:
    print("No 'jobs' table found. Nothing to clear.")
    conn.close()
    sys.exit(0)

cur.execute("SELECT COUNT(*) FROM jobs")
before = cur.fetchone()[0]
cur.execute("DELETE FROM jobs")
conn.commit()
cur.execute("SELECT COUNT(*) FROM jobs")
after = cur.fetchone()[0]
conn.close()
print(f"Deleted {before - after} rows. Now {after} rows remain.")
