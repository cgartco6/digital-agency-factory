
### `command_center/app.py`
```python
"""Digital Agency Factory — Live Command Center.

Reads the Meta-Orchestrator's SQLite tracking matrix and renders:
  • System Module Build Matrix (Pending / In Process / Validating / Healing / Locked)
  • Real-Time Action Log (live agent feed)
  • Master Test Suite Matrix + Deployment Certification Banner
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from meta_orchestrator.orchestrator import MetaOrchestrator  # noqa: E402
from meta_orchestrator.state import BuildStatus  # noqa: E402

st.set_page_config(
    page_title="Digital Agency Factory — Command Center",
    page_icon="🏭",
    layout="wide",
)

STATUS_ICON = {
    BuildStatus.PENDING.value:    "⚪ Pending",
    BuildStatus.IN_PROCESS.value: "🟡 In Process",
    BuildStatus.VALIDATING.value: "🔵 Validating",
    BuildStatus.HEALING.value:    "🟠 Healing",
    BuildStatus.LOCKED.value:     "🟢 Locked",
    BuildStatus.FAILED.value:     "🔴 Failed",
}

AUTO_REFRESH = os.getenv("COMMAND_CENTER_REFRESH", "3")


@st.cache_resource
def _orchestrator() -> MetaOrchestrator:
    return MetaOrchestrator()


def _render_header() -> None:
    st.markdown(
        """
        <h1 style='margin-bottom:0;'>🏭 Digital Agency Factory</h1>
        <p style='color:#64748b;margin-top:0;'>
        Autonomous Software Factory — Meta-Orchestrator Command Center
        </p>
        """,
        unsafe_allow_html=True,
    )


def _render_matrix(snapshot: dict) -> None:
    st.subheader("System Module Build Matrix")
    modules = snapshot["modules"]
    if not modules:
        st.info("No modules registered yet. Run the swarm to populate the matrix.")
        return
    rows = []
    for m in modules:
        rows.append(
            {
                "Module": m["module_id"],
                "Path": m["path"],
                "Status": STATUS_ICON.get(m["status"], m["status"]),
                "Coverage %": m["coverage"],
                "Passed": m["passed"],
                "Failed": m["failed"],
                "Attempts": m["attempts"],
                "Updated": m["updated_at"][11:19],
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_log(snapshot: dict) -> None:
    st.subheader("Real-Time Action Log")
    logs = snapshot["logs"][:60]
    if not logs:
        st.info("Awaiting agent activity…")
        return
    lines = []
    for entry in logs:
        mid = f"[{entry['module_id']}] " if entry["module_id"] else ""
        lines.append(
            f"{entry['ts'][11:19]}  {entry['level']:<5} "
            f"<{entry['agent']}>  {mid}{entry['message']}"
        )
    st.code("\n".join(lines), language="log")


def _render_certification(snapshot: dict) -> None:
    st.subheader("Master Test Suite Matrix")
    modules = snapshot["modules"]
    if modules:
        total_assertions = sum(m["assertions"] for m in modules)
        total_failed = sum(m["failed"] for m in modules)
        avg_coverage = (
            sum(m["coverage"] for m in modules) / len(modules) if modules else 0.0
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Assertions", total_assertions)
        c2.metric(
            "Failing Assertions",
            total_failed,
            delta=None if total_failed == 0 else -total_failed,
        )
        c3.metric("Avg Coverage", f"{avg_coverage:.2f}%")

    st.markdown("---")
    if snapshot["ready_for_deployment"]:
        st.markdown(
            """
            <div style='background:#065f46;color:#ecfdf5;padding:22px;
                        border-radius:12px;text-align:center;font-size:22px;
                        font-weight:700;letter-spacing:0.5px;'>
              ✅ READY FOR LIVE DEPLOYMENT — ALL MODULES LOCKED
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style='background:#7f1d1d;color:#fee2e2;padding:22px;
                        border-radius:12px;text-align:center;font-size:22px;
                        font-weight:700;letter-spacing:0.5px;'>
              ⛔ DEPLOYMENT GATE NOT SATISFIED — HEAL LOOP REQUIRED
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    _render_header()
    orchestrator = _orchestrator()

    with st.sidebar:
        st.header("⚙️ Orchestrator Controls")
        auto = st.toggle("Auto-refresh", value=True)
        st.caption(f"Refresh interval: {AUTO_REFRESH}s")

        if st.button("▶️ Run Full Swarm Build", use_container_width=True):
            with st.spinner("Swarm executing — Build → QA → Heal loop…"):
                orchestrator.execute_sync()
            st.success("Swarm run complete.")

        if st.button("♻️ Reset Matrix", use_container_width=True):
            orchestrator.register_modules()
            st.warning("Matrix reset to PENDING.")

        st.markdown("---")
        st.caption(
            "All AI calls route to cloud APIs (OpenAI / Anthropic / Replicate). "
            "The host machine never loads a local GPU model."
        )
