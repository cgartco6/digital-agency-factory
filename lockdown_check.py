#!/usr/bin/env python3
"""MASTER LOCKDOWN GUARD.

Runs the full test suite across every module, parses coverage, and HALTS
deployment entirely if ANY module fails tests or drops below the gate (95%).

Exit codes:
    0  → all modules certified
    1  → coverage below gate
    2  → test failures
    3  → structural / collection failure
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent
BLUEPRINT = ROOT / "blueprint.json"
COVERAGE_GATE = float(os.getenv("COVERAGE_GATE", "95.0"))


def _load_modules() -> List[dict]:
    if not BLUEPRINT.exists():
        print(f"[lockdown] FATAL: blueprint missing at {BLUEPRINT}")
        sys.exit(3)
    return json.loads(BLUEPRINT.read_text()).get("modules", [])


def _run_pytest(module: dict) -> Tuple[int, float, int, int, str]:
    pkg = module["path"].replace("/", ".")
    test_path = module["test_path"]
    cov_json = ROOT / f".coverage_{module['module_id']}.json"
    cmd = [
        sys.executable, "-m", "pytest", test_path,
        "-q",
        f"--cov={pkg}",
        f"--cov-report=json:{cov_json}",
        "--cov-report=term-missing",
        "-p", "no:cacheprovider",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    raw = proc.stdout + "\n" + proc.stderr

    passed = failed = 0
    for line in raw.splitlines():
        if " passed" in line:
            tokens = line.replace(",", " ").split()
            for i, tok in enumerate(tokens):
                if tok == "passed":
                    try:
                        passed = int(tokens[i - 1])
                    except (ValueError, IndexError):
                        pass
                if tok == "failed":
                    try:
                        failed = int(tokens[i - 1])
                    except (ValueError, IndexError):
                        pass

    coverage = 0.0
    if cov_json.exists():
        try:
            data = json.loads(cov_json.read_text())
            coverage = float(data.get("totals", {}).get("percent_covered", 0.0))
            cov_json.unlink()
        except (json.JSONDecodeError, OSError):
            coverage = 0.0

    return proc.returncode, round(coverage, 2), passed, failed, raw


def main() -> int:
    print("=" * 74)
    print("  MASTER LOCKDOWN GUARD — Digital Agency Factory")
    print(f"  Coverage gate: {COVERAGE_GATE}%")
    print("=" * 74)

    modules = _load_modules()
    if not modules:
        print("[lockdown] FATAL: no modules declared in blueprint.")
        return 3

    failures: List[str] = []
    coverage_failures: List[str] = []
    structural_failures: List[str] = []

    for module in modules:
        mid = module["module_id"]
        print(f"\n▶ [{mid}] running tests at {module['test_path']}")
        code, coverage, passed, failed, raw = _run_pytest(module)

        status = "PASS" if code == 0 else "FAIL"
        print(f"  ↳ {status}  passed={passed} failed={failed} coverage={coverage}%")

        if code == 5:
            structural_failures.append(f"{mid}: no tests collected")
            print("  ↳ no tests collected")
            continue
        if code != 0 or failed > 0:
            failures.append(f"{mid}: {failed} failing assertions")
            print(raw[-1500:])
        if coverage < COVERAGE_GATE:
            coverage_failures.append(f"{mid}: {coverage}% < {COVERAGE_GATE}%")

    print("\n" + "=" * 74)
    if failures or coverage_failures or structural_failures:
        print("  ⛔ DEPLOYMENT PIPELINE HALTED")
        for label, items in (
            ("Test failures", failures),
            ("Coverage gate breaches", coverage_failures),
            ("Structural failures", structural_failures),
        ):
            if items:
                print(f"  - {label}:")
                for item in items:
                    print(f"      • {item}")
        print("=" * 74)
        if structural_failures:
            return 3
        if failures:
            return 2
        return 1

    print("  ✅ ALL MODULES LOCKED — 100% TEST PASS, COVERAGE GATE SATISFIED")
    print("  🚀 READY FOR LIVE DEPLOYMENT")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
