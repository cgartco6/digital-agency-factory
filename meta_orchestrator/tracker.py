"""SQLite-backed build-tracking matrix — thread-safe, live-queryable."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import List, Optional

from .state import (
    BuildManifest,
    BuildStatus,
    LogEntry,
    ModuleRecord,
    _now,
)


class BuildTracker:
    """Single source of truth for swarm state. Safe for concurrent agents."""

    def __init__(self, db_path: str | Path = "./.factory/state.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    # ---------------- internals ----------------
    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS modules (
                    module_id TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    test_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    coverage REAL DEFAULT 0,
                    assertions INTEGER DEFAULT 0,
                    passed INTEGER DEFAULT 0,
                    failed INTEGER DEFAULT 0,
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    level TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    module_id TEXT,
                    message TEXT NOT NULL
                );
                """
            )

    # ---------------- module CRUD ----------------
    def register(self, module: ModuleRecord) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO modules
                   (module_id,path,test_path,status,coverage,assertions,
                    passed,failed,attempts,last_error,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    module.module_id,
                    module.path,
                    module.test_path,
                    module.status.value,
                    module.coverage,
                    module.assertions,
                    module.passed,
                    module.failed,
                    module.attempts,
                    module.last_error,
                    module.updated_at,
                ),
            )

    def set_status(
        self, module_id: str, status: BuildStatus, error: Optional[str] = None
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE modules SET status=?, last_error=?, updated_at=? WHERE module_id=?",
                (status.value, error, _now(), module_id),
            )

    def record_test_result(
        self,
        module_id: str,
        coverage: float,
        assertions: int,
        passed: int,
        failed: int,
        error: Optional[str] = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """UPDATE modules
                   SET coverage=?, assertions=?, passed=?, failed=?,
                       attempts = attempts + 1, last_error=?, updated_at=?
                   WHERE module_id=?""",
                (coverage, assertions, passed, failed, error, _now(), module_id),
            )

    def get_module(self, module_id: str) -> Optional[ModuleRecord]:
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM modules WHERE module_id=?", (module_id,)
            ).fetchone()
        return self._row_to_module(row) if row else None

    def all_modules(self) -> List[ModuleRecord]:
        with self._lock, self._conn() as conn:
            rows = conn.execute("SELECT * FROM modules ORDER BY module_id").fetchall()
        return [self._row_to_module(r) for r in rows]

    @staticmethod
    def _row_to_module(row: sqlite3.Row) -> ModuleRecord:
        return ModuleRecord(
            module_id=row["module_id"],
            path=row["path"],
            test_path=row["test_path"],
            status=BuildStatus(row["status"]),
            coverage=row["coverage"],
            assertions=row["assertions"],
            passed=row["passed"],
            failed=row["failed"],
            attempts=row["attempts"],
            last_error=row["last_error"],
            updated_at=row["updated_at"],
        )

    # ---------------- logging ----------------
    def log(
        self,
        message: str,
        agent: str = "orchestrator",
        level: str = "INFO",
        module_id: Optional[str] = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO logs (ts,level,agent,module_id,message) VALUES (?,?,?,?,?)",
                (_now(), level, agent, module_id, message),
            )

    def recent_logs(self, limit: int = 200) -> List[LogEntry]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            LogEntry(
                ts=r["ts"],
                level=r["level"],
                agent=r["agent"],
                module_id=r["module_id"],
                message=r["message"],
            )
            for r in rows
        ]

    # ---------------- certification ----------------
    def to_manifest(self, project: str, version: str) -> BuildManifest:
        return BuildManifest(project=project, version=version, modules=self.all_modules())

    def is_fully_locked(self, coverage_gate: float = 95.0) -> bool:
        modules = self.all_modules()
        if not modules:
            return False
        return all(
            m.status == BuildStatus.LOCKED and m.coverage >= coverage_gate and m.failed == 0
            for m in modules
        )
