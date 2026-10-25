from __future__ import annotations

from fastapi import APIRouter, HTTPException

from studios.common.base import StudioError

from .engine import DesignEngine
from .schemas import DesignBrief, DesignSystem

router = APIRouter(prefix="/studios/design", tags=["design"])
_engine = DesignEngine()


@router.post("/generate", response_model=DesignSystem)
async def generate(brief: DesignBrief) -> DesignSystem:
    try:
        return await _engine.generate(brief)
    except StudioError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "studio": "design", "llm": _engine.llm.as_dict()}
