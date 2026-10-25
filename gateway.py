"""Master FastAPI gateway — mounts every studio + the Meta-Orchestrator."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from meta_orchestrator.api import router as orchestrator_router
from studios.branding.router import router as branding_router
from studios.core_mesh.router import router as mesh_router
from studios.design.router import router as design_router
from studios.marketing.router import router as marketing_router

load_dotenv()

app = FastAPI(
    title="Digital Agency Factory",
    version="1.0.0",
    description="Autonomous, cloud-routed Digital Agency. CPU-only host safe.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orchestrator_router)
app.include_router(branding_router)
app.include_router(design_router)
app.include_router(marketing_router)
app.include_router(mesh_router)


@app.get("/")
async def root() -> dict:
    return {
        "service": "Digital Agency Factory",
        "version": "1.0.0",
        "studios": ["branding", "design", "marketing", "core_mesh"],
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("gateway:app", host="0.0.0.0", port=8000, reload=True)
