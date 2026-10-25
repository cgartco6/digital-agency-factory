"""Concurrent swarm executor. Spawns parallel agent instances — no queueing."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Iterable, List

from studios.common.llm_client import LLMClient

from .agents import BuildAgent, QAAgent, RewriteAgent, TestResult
from .state import BuildStatus, ModuleRecord
from .tracker import BuildTracker


class Swarm:
    def __init__(
        self,
        tracker: BuildTracker,
        workspace: Path,
        concurrency: int = 8,
        coverage_gate: float = 95.0,
        max_heal_attempts: int = 3,
    ) -> None:
        self.tracker = tracker
        self.workspace = Path(workspace)
        self.coverage_gate = coverage_gate
        self.max_heal_attempts = max_heal_attempts
        self._sem = asyncio.Semaphore(concurrency)
        self.llm = LLMClient()
        self.builder = BuildAgent(tracker, self.llm, self.workspace)
        self.qa = QAAgent(tracker, self.workspace)
        self.rewriter = RewriteAgent(tracker, self.llm, self.workspace)

    async def process(self, module: ModuleRecord) -> ModuleRecord:
        async with self._sem:
            try:
                await self.builder.run(module)
                for attempt in range(1, self.max_heal_attempts + 1):
                    result: TestResult = await self.qa.run(module)
                    self.tracker.record_test_result(
                        module.module_id,
                        coverage=result.coverage,
                        assertions=result.assertions,
                        passed=result.passed,
                        failed=result.failed,
                        error=None if result.ok else result.raw[-500:],
                    )
                    self.tracker.log(
                        f"QA run {attempt}: {result.passed} passed / "
                        f"{result.failed} failed / {result.coverage:.2f}% coverage",
                        agent=self.qa.name,
                        module_id=module.module_id,
                    )
                    if result.ok and result.coverage >= self.coverage_gate:
                        self.tracker.set_status(module.module_id, BuildStatus.LOCKED)
                        self.tracker.log(
                            f"🔒 {module.module_id} LOCKED at "
                            f"{result.coverage:.2f}% coverage.",
                            agent="orchestrator",
                            module_id=module.module_id,
                        )
                        break
                    if attempt == self.max_heal_attempts:
                        self.tracker.set_status(
                            module.module_id, BuildStatus.FAILED, error=result.raw[-500:]
                        )
                        self.tracker.log(
                            f"❌ {module.module_id} exhausted heal attempts.",
                            agent="orchestrator",
                            level="ERROR",
                            module_id=module.module_id,
                        )
                        break
                    await self.rewriter.run(module, result)
            except Exception as exc:  # noqa: BLE001
                self.tracker.set_status(
                    module.module_id, BuildStatus.FAILED, error=str(exc)
                )
                self.tracker.log(
                    f"Agent exception on {module.module_id}: {exc}",
                    agent="orchestrator",
                    level="ERROR",
                    module_id=module.module_id,
                )
        updated = self.tracker.get_module(module.module_id)
        assert updated is not None
        return updated

    async def run_all(self, modules: Iterable[ModuleRecord]) -> List[ModuleRecord]:
        return await asyncio.gather(*(self.process(m) for m in modules))
