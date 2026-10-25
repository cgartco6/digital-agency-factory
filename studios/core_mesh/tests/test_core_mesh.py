from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from studios.branding.engine import BrandingEngine
from studios.branding.schemas import BrandBrief
from studios.common.base import StudioError
from studios.common.llm_client import LLMClient
from studios.core_mesh.engine import CoreMeshEngine
from studios.core_mesh.router import router as mesh_router
from studios.core_mesh.schemas import MeshRequest


@pytest.mark.asyncio
async def test_mesh_returns_full_launch_package() -> None:
    engine = CoreMeshEngine(llm=LLMClient(api_key=None))
    req = MeshRequest(
        company="Northwind",
        industry="Logistics",
        values=["reliability"],
        primary_color="#112233",
        budget_usd=900.0,
        duration_days=14,
        channels=["email", "seo"],
    )
    pkg = await engine.build(req)
    assert pkg.company == "Northwind"
    assert pkg.branding.tagline
    assert pkg.design.spacing_unit > 0
    assert abs(sum(a.budget_usd for a in pkg.campaign.allocations) - 900.0) < 0.5


@pytest.mark.asyncio
async def test_consistency_score_is_percentage() -> None:
    engine = CoreMeshEngine(llm=LLMClient(api_key=None))
    req = MeshRequest(company="Acme", industry="SaaS", values=["clarity"])
    pkg = await engine.build(req)
    assert 0.0 <= pkg.consistency_score <= 100.0


@pytest.mark.asyncio
async def test_warnings_recorded_when_primary_mismatch() -> None:
    engine = CoreMeshEngine(llm=LLMClient(api_key=None))
    req = MeshRequest(
        company="Acme",
        industry="SaaS",
        values=["clarity"],
        primary_color="#ABCDEF",
    )
    pkg = await engine.build(req)
    assert any("palette" in w.lower() for w in pkg.warnings)


@pytest.mark.asyncio
async def test_consistency_when_primary_matches_brand_palette() -> None:
    llm = LLMClient(api_key=None)
    branding = BrandingEngine(llm=llm)
    brand = await branding.generate(
        BrandBrief(company="Acme", industry="SaaS", values=["clarity"])
    )
    matched_color = brand.palette[0]

    mesh = CoreMeshEngine(llm=llm)
    req = MeshRequest(
        company="Acme",
        industry="SaaS",
        values=["clarity"],
        primary_color=matched_color,
    )
    pkg = await mesh.build(req)
    assert pkg.consistency_score == 100.0
    assert not any("palette" in w.lower() for w in pkg.warnings)


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(mesh_router)
    return TestClient(app)


def test_router_build_success() -> None:
    client = _client()
    resp = client.post(
        "/studios/mesh/build",
        json={"company": "Acme", "industry": "SaaS", "values": ["clarity"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["company"] == "Acme"
    assert data["branding"]["company"] == "Acme"


def test_router_build_validation_error() -> None:
    client = _client()
    resp = client.post(
        "/studios/mesh/build",
        json={"company": "Acme", "industry": "SaaS", "values": []},
    )
    assert resp.status_code == 422


def test_router_build_studio_error(monkeypatch) -> None:
    from studios.core_mesh import router as mesh_router_module

    class _BoomEngine:
        async def build(self, _req):
            raise StudioError("boom")

        class _LLM:
            provider = "test"
            model = "test"

            @staticmethod
            def as_dict():
                return {"provider": "test", "model": "test", "offline_mode": True}

        llm = _LLM()

    monkeypatch.setattr(mesh_router_module, "_engine", _BoomEngine())
    client = _client()
    resp = client.post(
        "/studios/mesh/build",
        json={"company": "Acme", "industry": "SaaS", "values": ["clarity"]},
    )
    assert resp.status_code == 422


def test_router_status() -> None:
    client = _client()
    resp = client.get("/studios/mesh/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["studio_count"] == 3
