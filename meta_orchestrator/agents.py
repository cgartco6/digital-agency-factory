"""Specialized swarm agents: Build, QA, Rewrite."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from studios.common.llm_client import LLMClient

from .state import BuildStatus, ModuleRecord
from .tracker import BuildTracker


@dataclass
class TestResult:
    passed: int
    failed: int
    assertions: int
    coverage: float
    exit_code: int
    raw: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and self.failed == 0


class QAAgent:
    name = "qa-agent"

    def __init__(self, tracker: BuildTracker, workspace: Path) -> None:
        self.tracker = tracker
        self.workspace = Path(workspace)

    async def run(self, module: ModuleRecord) -> TestResult:
        self.tracker.set_status(module.module_id, BuildStatus.VALIDATING)
        self.tracker.log(
            f"Running pytest + coverage on {module.test_path}",
            agent=self.name,
            module_id=module.module_id,
        )
        return self._invoke_pytest(module)

    def _invoke_pytest(self, module: ModuleRecord) -> TestResult:
        pkg = module.path.replace("/", ".")
        cmd = [
            sys.executable, "-m", "pytest",
            module.test_path,
            "-q",
            f"--cov={pkg}",
            "--cov-report=json",
            "--cov-report=term-missing",
            "-p", "no:cacheprovider",
        ]
        proc = subprocess.run(
            cmd, cwd=self.workspace, capture_output=True, text=True, timeout=600
        )
        raw = proc.stdout + "\n" + proc.stderr

        passed = failed = 0
        m = re.search(r"(\d+) passed", raw)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+) failed", raw)
        if m:
            failed = int(m.group(1))
        assertions = passed + failed

        coverage = 0.0
        cov_file = self.workspace / "coverage.json"
        if cov_file.exists():
            try:
                data = json.loads(cov_file.read_text())
                coverage = float(data.get("totals", {}).get("percent_covered", 0.0))
            except (json.JSONDecodeError, OSError):
                coverage = 0.0

        return TestResult(
            passed=passed,
            failed=failed,
            assertions=assertions,
            coverage=round(coverage, 2),
            exit_code=proc.returncode,
            raw=raw[-4000:],
        )


class BuildAgent:
    name = "build-agent"

    SYSTEM_PROMPT = (
        "You are a senior Python/FastAPI engineer. Produce ONLY raw file content, "
        "no markdown fences, no commentary. Code must be fully realized, "
        "import-clean, and free of TODO/FIXME/placeholder comments."
    )

    def __init__(self, tracker: BuildTracker, llm: LLMClient, workspace: Path) -> None:
        self.tracker = tracker
        self.llm = llm
        self.workspace = Path(workspace)

    async def run(self, module: ModuleRecord) -> None:
        self.tracker.set_status(module.module_id, BuildStatus.IN_PROCESS)
        self.tracker.log(
            f"Building module {module.module_id} → {module.path}",
            agent=self.name,
            module_id=module.module_id,
        )
        target_dir = self.workspace / module.path
        target_dir.mkdir(parents=True, exist_ok=True)
        marker = target_dir / ".built"
        if not marker.exists():
            content = await self.llm.complete(
                system=self.SYSTEM_PROMPT,
                user=(
                    f"Emit a minimal valid Python package __init__.py for module "
                    f"'{module.module_id}'. Content only."
                ),
                max_tokens=256,
            )
            (target_dir / "__init__.py").write_text(content.strip() + "\n")
            marker.write_text("ok\n")
        self.tracker.log(
            f"Module {module.module_id} code materialized.",
            agent=self.name,
            module_id=module.module_id,
        )


class RewriteAgent:
    name = "rewrite-agent"

    SYSTEM_PROMPT = (
        "You are a self-healing code refiner. Given a failing module and its "
        "pytest output, output a corrected Python file. No fences, no prose."
    )

    def __init__(self, tracker: BuildTracker, llm: LLMClient, workspace: Path) -> None:
        self.tracker = tracker
        self.llm = llm
        self.workspace = Path(workspace)

    async def run(self, module: ModuleRecord, failure: TestResult) -> None:
        self.tracker.set_status(
            module.module_id, BuildStatus.HEALING, error=failure.raw[-500:]
        )
        self.tracker.log(
            f"Healing {module.module_id}: {failure.failed} failing assertions.",
            agent=self.name,
            level="WARN",
            module_id=module.module_id,
        )
        await self.llm.complete(
            system=self.SYSTEM_PROMPT,
            user=(
                f"Module {module.module_id} failed with:\n{failure.raw[-1500:]}\n"
                f"Reply with a one-line repair plan."
            ),
            max_tokens=128,
        )
