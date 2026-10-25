"""HTTP surface for the Meta-Orchestrator tracking matrix."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .orchestrator import MetaOrchestrator

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


def _get() -> MetaOrchestrator:
    return MetaOrchestrator()


@router.get("/status")
async def status() -> dict:
    return _get().status_snapshot()


@router.post("/run")
async def run_factory() -> dict:
    try:
        return await _get().execute()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "service": "meta-orchestrator"}
