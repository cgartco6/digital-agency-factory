from __future__ import annotations

from fastapi import APIRouter, HTTPException

from studios.common.base import StudioError

from .engine import BrandingEngine
from .schemas import BrandBrief, BrandIdentity

router = APIRouter(prefix="/studios/branding", tags=["branding"])
_engine = BrandingEngine()


@router.post("/generate", response_model=BrandIdentity)
async def generate(brief: BrandBrief) -> BrandIdentity:
    try:
        return await _engine.generate(brief)
    except StudioError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "studio": "branding", "llm": _engine.llm.as_dict()}
