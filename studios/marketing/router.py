from __future__ import annotations

from fastapi import APIRouter, HTTPException

from studios.common.base import StudioError

from .engine import MarketingEngine
from .schemas import CampaignBrief, CampaignPlan

router = APIRouter(prefix="/studios/marketing", tags=["marketing"])
_engine = MarketingEngine()


@router.post("/generate", response_model=CampaignPlan)
async def generate(brief: CampaignBrief) -> CampaignPlan:
    try:
        return await _engine.generate(brief)
    except StudioError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "studio": "marketing", "llm": _engine.llm.as_dict()}
