"""State models for the Meta-Orchestrator build matrix (Pydantic v2)."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BuildStatus(str, Enum):
    PENDING = "Pending"
    IN_PROCESS = "In Process"
    VALIDATING = "Validating"
    HEALING = "Healing"
    LOCKED = "Locked"
    FAILED = "Failed"


class ModuleRecord(BaseModel):
    module_id: str
    path: str
    test_path: str
    status: BuildStatus = BuildStatus.PENDING
    coverage: float = 0.0
    assertions: int = 0
    passed: int = 0
    failed: int = 0
    attempts: int = 0
    last_error: Optional[str] = None
    updated_at: str = Field(default_factory=_now)

    @property
    def is_certified(self) -> bool:
        return (
            self.status == BuildStatus.LOCKED
            and self.coverage >= 95.0
            and self.failed == 0
        )


class LogEntry(BaseModel):
    ts: str = Field(default_factory=_now)
    level: str = "INFO"
    agent: str = "orchestrator"
    module_id: Optional[str] = None
    message: str


class BuildManifest(BaseModel):
    project: str
    version: str
    modules: List[ModuleRecord]
