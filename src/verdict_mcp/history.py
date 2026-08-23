"""Failure history store (SQLite).

Answers the question agents misdiagnose most: is this failure a regression
I just introduced, or was it already broken? Also persists run summaries and
full failure detail so `explain_failure` works after `verify` returns.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .schema import FailureDetail, HistoryEntry

_SCHEMA = """
CREATE TABLE IF NOT EXISTS failures (
    fingerprint TEXT NOT NULL,
    check_id    TEXT NOT NULL,
    first_seen  REAL NOT NULL,
    last_seen   REAL NOT NULL,
    times_seen  INTEGER NOT NULL DEFAULT 1,
    first_seen_commit TEXT,
    PRIMARY KEY (fingerprint)
);
CREATE TABLE IF NOT EXISTS details (
    run_id      TEXT NOT NULL,
    check_id    TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    payload     TEXT NOT NULL,
    PRIMARY KEY (run_id, check_id)
);
CREATE TABLE IF NOT EXISTS runs (
    run_id   TEXT PRIMARY KEY,
    ts       REAL NOT NULL,
    summary  TEXT NOT NULL
);
"""


class HistoryStore:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(root / "history.db")
        self.db.executescript(_SCHEMA)

    def seen_before(self, fingerprint: str) -> bool:
        row = self.db.execute(
            "SELECT 1 FROM failures WHERE fingerprint = ?", (fingerprint,)
        ).fetchone()
        return row is not None

    def record_failure(self, fingerprint: str, check_id: str, commit: str | None) -> None:
        now = time.time()
        self.db.execute(
            """INSERT INTO failures (fingerprint, check_id, first_seen, last_seen, times_seen, first_seen_commit)
               VALUES (?, ?, ?, ?, 1, ?)
               ON CONFLICT(fingerprint) DO UPDATE SET last_seen = ?, times_seen = times_seen + 1""",
            (fingerprint, check_id, now, now, commit, now),
        )
        self.db.commit()

    def record_detail(self, run_id: str, detail: FailureDetail) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO details (run_id, check_id, fingerprint, payload) VALUES (?, ?, ?, ?)",
            (run_id, detail.check_id, detail.fingerprint, detail.model_dump_json()),
        )
        self.db.commit()

    def record_run(self, run_id: str, summary_json: str) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO runs (run_id, ts, summary) VALUES (?, ?, ?)",
            (run_id, time.time(), summary_json),
        )
        self.db.commit()

    def get_detail(self, check_id: str, run_id: str | None = None) -> FailureDetail | None:
        if run_id:
            row = self.db.execute(
                "SELECT payload FROM details WHERE run_id = ? AND check_id = ?", (run_id, check_id)
            ).fetchone()
        else:
            row = self.db.execute(
                "SELECT payload FROM details WHERE check_id = ? ORDER BY rowid DESC LIMIT 1",
                (check_id,),
            ).fetchone()
        return FailureDetail(**json.loads(row[0])) if row else None

    def get_history(self, fingerprint: str) -> HistoryEntry | None:
        row = self.db.execute(
            "SELECT fingerprint, check_id, first_seen, last_seen, times_seen, first_seen_commit "
            "FROM failures WHERE fingerprint = ?",
            (fingerprint,),
        ).fetchone()
        if not row:
            return None
        fmt = lambda ts: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
        return HistoryEntry(
            fingerprint=row[0],
            check_id=row[1],
            first_seen=fmt(row[2]),
            last_seen=fmt(row[3]),
            times_seen=row[4],
            first_seen_commit=row[5],
        )
