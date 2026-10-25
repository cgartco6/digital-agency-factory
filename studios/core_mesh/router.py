from __future__ import annotations

from fastapi import APIRouter, HTTPException

from studios.common.base import StudioError

from .engine import CoreMeshEngine
from .schemas import LaunchPackage, MeshRequest, MeshStatus

router = APIRouter(prefix="/studios/mesh", tags=["core-mesh"])
_engine = CoreMeshEngine()


@router.post("/build", response_model=LaunchPackage)
async def build(req: MeshRequest) -> LaunchPackage:
    try:
        return await _engine.build(req)
    except StudioError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/status", response_model=MeshStatus)
async def status() -> MeshStatus:
    info = _engine.llm.as_dict()
    return MeshStatus(
        ok=True,
        studio_count=3,
        llm_provider=info["provider"],
        llm_model=info["model"],
        offline_mode=info["offline_mode"],
    )
