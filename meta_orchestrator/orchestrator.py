"""The Mind — reads the blueprint, registers modules, spawns the swarm."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import List

from .state import BuildStatus, ModuleRecord
from .swarm import Swarm
from .tracker import BuildTracker


class MetaOrchestrator:
    def __init__(
        self,
        blueprint_path: str | Path = "./blueprint.json",
        db_path: str | Path | None = None,
        workspace: str | Path | None = None,
    ) -> None:
        self.blueprint_path = Path(blueprint_path)
        self.db_path = Path(
            db_path or os.getenv("ORCHESTRATOR_DB", "./.factory/state.db")
        )
        self.workspace = Path(
            workspace or os.getenv("ORCHESTRATOR_WORKSPACE", "./generated_workspace")
        )
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.tracker = BuildTracker(self.db_path)
        self.coverage_gate = float(os.getenv("COVERAGE_GATE", "95.0"))
        self.concurrency = int(os.getenv("ORCHESTRATOR_CONCURRENCY", "8"))
        self.max_heal_attempts = int(os.getenv("ORCHESTRATOR_MAX_HEAL_ATTEMPTS", "3"))

    def load_blueprint(self) -> dict:
        if not self.blueprint_path.exists():
            raise FileNotFoundError(f"Blueprint missing: {self.blueprint_path}")
        return json.loads(self.blueprint_path.read_text())

    def register_modules(self) -> List[ModuleRecord]:
        blueprint = self.load_blueprint()
        records: List[ModuleRecord] = []
        for raw in blueprint.get("modules", []):
            record = ModuleRecord(
                module_id=raw["module_id"],
                path=raw["path"],
                test_path=raw.get("test_path", f"{raw['path']}/tests"),
                status=BuildStatus.PENDING,
            )
            self.tracker.register(record)
            self.tracker.log(
                f"Registered module '{record.module_id}' at {record.path}",
                agent="orchestrator",
                module_id=record.module_id,
            )
            records.append(record)
        return records

    async def execute(self) -> dict:
        self.tracker.log(
            "🚀 Meta-Orchestrator online. Mapping dependencies.", agent="orchestrator"
        )
        modules = self.register_modules()
        swarm = Swarm(
            tracker=self.tracker,
            workspace=self.workspace,
            concurrency=self.concurrency,
            coverage_gate=self.coverage_gate,
            max_heal_attempts=self.max_heal_attempts,
        )
        await swarm.run_all(modules)
        blueprint = self.load_blueprint()
        manifest = self.tracker.to_manifest(
            project=blueprint.get("project", "Digital Agency Factory"),
            version=blueprint.get("version", "1.0.0"),
        )
        ready = self.tracker.is_fully_locked(self.coverage_gate)
        self.tracker.log(
            "✅ FACTORY READY FOR LIVE DEPLOYMENT" if ready
            else "⛔ Deployment gate NOT satisfied — heal loop required.",
            agent="orchestrator",
            level="INFO" if ready else "ERROR",
        )
        return {"manifest": manifest.model_dump(), "ready_for_deployment": ready}

    def execute_sync(self) -> dict:
        return asyncio.run(self.execute())

    def status_snapshot(self) -> dict:
        modules = self.tracker.all_modules()
        return {
            "modules": [m.model_dump() for m in modules],
            "logs": [entry.model_dump() for entry in self.tracker.recent_logs(200)],
            "ready_for_deployment": self.tracker.is_fully_locked(self.coverage_gate),
        }
