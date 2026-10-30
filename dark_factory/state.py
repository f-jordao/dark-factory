import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


class State:
    """Durable claims prevent concurrent processes from repeating a review."""

    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), timeout=30, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                key TEXT PRIMARY KEY, repo TEXT NOT NULL, number INTEGER NOT NULL,
                head TEXT NOT NULL, base TEXT NOT NULL, policy TEXT NOT NULL,
                status TEXT NOT NULL, owner TEXT, lease_until REAL NOT NULL DEFAULT 0,
                result TEXT, review_id INTEGER, error TEXT, updated_at REAL NOT NULL
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS pull_requests (
                repo TEXT NOT NULL, number INTEGER NOT NULL, head TEXT NOT NULL,
                base TEXT NOT NULL, state TEXT NOT NULL, reason TEXT NOT NULL,
                updated_at REAL NOT NULL, PRIMARY KEY (repo, number)
            )
        """)

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        else:
            self.db.execute("COMMIT")

    def get(self, key):
        row = self.db.execute("SELECT * FROM reviews WHERE key = ?", (key,)).fetchone()
        return dict(row) if row else None

    def observe(self, snapshot, reason):
        self.db.execute(
            "INSERT INTO pull_requests (repo,number,head,base,state,reason,updated_at) "
            "VALUES (?,?,?,?,?,?,?) ON CONFLICT(repo,number) DO UPDATE SET "
            "head=excluded.head,base=excluded.base,state=excluded.state,"
            "reason=excluded.reason,updated_at=excluded.updated_at",
            (snapshot.repo, snapshot.number, snapshot.head, snapshot.base,
             snapshot.state, reason, time.time()),
        )

    def active_prs(self, repo):
        return [
            row["number"] for row in self.db.execute(
                "SELECT number FROM pull_requests WHERE repo=? AND state='open'", (repo,)
            )
        ]

    def observations(self):
        return [
            dict(row) for row in self.db.execute(
                "SELECT * FROM pull_requests ORDER BY updated_at DESC"
            )
        ]

    def claim_review(self, key, snapshot, policy, retry=False):
        now, owner = time.time(), uuid.uuid4().hex
        with self.transaction():
            row = self.get(key)
            if row:
                recoverable = row["status"] == "failed" or (
                    row["status"] == "running" and row["lease_until"] < now
                )
                if not (row["status"] == "blocked" or (retry and recoverable)):
                    return None
                self.db.execute(
                    "UPDATE reviews SET status='running', owner=?, lease_until=?, "
                    "error=NULL, updated_at=? WHERE key=?",
                    (owner, now + policy.timeout_seconds + 600, now, key),
                )
            else:
                self.db.execute(
                    "INSERT INTO reviews "
                    "(key,repo,number,head,base,policy,status,owner,lease_until,updated_at) "
                    "VALUES (?,?,?,?,?,?,'running',?,?,?)",
                    (key, snapshot.repo, snapshot.number, snapshot.head, snapshot.base,
                     policy.digest, owner, now + policy.timeout_seconds + 600, now),
                )
        return owner

    def finish_review(self, key, owner, result=None, error=None, started=True):
        status = "reviewed" if result is not None else ("failed" if started else "blocked")
        changed = self.db.execute(
            "UPDATE reviews SET status=?,result=?,error=?,owner=NULL,lease_until=0,"
            "updated_at=? WHERE key=? AND owner=? AND status='running'",
            (status, json.dumps(result) if result is not None else None, error,
             time.time(), key, owner),
        ).rowcount
        if changed != 1:
            raise RuntimeError("Review claim was lost")

    def claim_publication(self, key):
        now, owner = time.time(), uuid.uuid4().hex
        with self.transaction():
            row = self.get(key)
            if not row or not (
                row["status"] == "reviewed"
                or (row["status"] == "publishing" and row["lease_until"] < now)
            ):
                return None
            self.db.execute(
                "UPDATE reviews SET status='publishing',owner=?,lease_until=?,"
                "updated_at=? WHERE key=?",
                (owner, now + 600, now, key),
            )
        return owner

    def finish_publication(self, key, owner, review_id=None, stale=False, error=None):
        status = "stale" if stale else ("published" if review_id is not None else "reviewed")
        changed = self.db.execute(
            "UPDATE reviews SET status=?,review_id=?,error=?,owner=NULL,lease_until=0,"
            "updated_at=? WHERE key=? AND owner=? AND status='publishing'",
            (status, review_id, error, time.time(), key, owner),
        ).rowcount
        if changed != 1:
            raise RuntimeError("Publication claim was lost")

    def list(self):
        return [
            dict(row) for row in self.db.execute(
                "SELECT key,repo,number,head,base,status,review_id,error,updated_at "
                "FROM reviews ORDER BY updated_at DESC"
            )
        ]

    def close(self):
        self.db.close()
