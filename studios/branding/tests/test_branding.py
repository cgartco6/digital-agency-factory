from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from studios.branding.engine import BrandingEngine
from studios.branding.router import router as branding_router
from studios.branding.schemas import BrandBrief, BrandIdentity, BrandVoice
from studios.common.base import StudioError
from studios.common.llm_client import LLMClient


# ---------------- fixtures ----------------
@pytest.fixture()
def brief() -> BrandBrief:
    return BrandBrief(
        company="Northwind",
        industry="Logistics",
        values=["reliability", "speed"],
        tone="confident",
        audience="mid-market shippers",
    )


@pytest.fixture()
def offline_engine() -> BrandingEngine:
    return BrandingEngine(llm=LLMClient(api_key=None))


class _FakeValidLLM:
    provider = "test"
    model = "test-valid"

    async def complete(self, *_a, **_kw) -> str:
        return json.dumps(
            {
                "tagline": "t",
                "mission": "m",
                "positioning": "p",
                "voice": {"descriptors": ["x"], "do": ["a"], "dont": ["b"]},
                "personas": [
                    {"name": "A", "role": "B", "pain_points": [], "motivators": []}
                ],
                "palette": ["#112233"],
            }
        )


class _FakeInvalidLLM:
    provider = "test"
    model = "test-invalid"

    async def complete(self, *_a, **_kw) -> str:
        return "definitely not json"


# ---------------- schema tests ----------------
def test_brief_rejects_empty_values() -> None:
    with pytest.raises(ValueError):
        BrandBrief(company="X", industry="Y", values=[])


def test_brief_deduplicates_values() -> None:
    b = BrandBrief(company="X", industry="Y", values=["a", "A", "b"])
    assert b.values == ["a", "b"]


def test_brand_identity_rejects_bad_palette() -> None:
    with pytest.raises(ValueError):
        BrandIdentity(
            company="X", tagline="t", mission="m", positioning="p",
            voice=BrandVoice(descriptors=["a"], do=["b"], dont=["c"]),
            personas=[], palette=["not-a-hex"], generated_by="test",
        )


# ---------------- engine tests ----------------
@pytest.mark.asyncio
async def test_engine_offline_generates_valid_identity(
    brief: BrandBrief, offline_engine: BrandingEngine
) -> None:
    identity = await offline_engine.generate(brief)
    assert identity.company == "Northwind"
    assert identity.tagline
    assert identity.palette and all(c.startswith("#") for c in identity.palette)
    assert identity.personas
    assert "clear" in identity.voice.descriptors


@pytest.mark.asyncio
async def test_engine_parses_valid_llm_json(brief: BrandBrief) -> None:
    engine = BrandingEngine(llm=_FakeValidLLM())
    identity = await engine.generate(brief)
    assert identity.tagline == "t"
    assert identity.palette == ["#112233"]


@pytest.mark.asyncio
async def test_engine_parses_invalid_llm_json_falls_back(brief: BrandBrief) -> None:
    engine = BrandingEngine(llm=_FakeInvalidLLM())
    identity = await engine.generate(brief)
    assert identity.tagline  # synthesized fallback


@pytest.mark.asyncio
async def test_engine_raises_studio_error_on_malformed_payload(
    brief: BrandBrief, offline_engine: BrandingEngine, monkeypatch
) -> None:
    monkeypatch.setattr(offline_engine, "_parse", lambda _raw, _brief: {"bogus": 1})
    with pytest.raises(StudioError):
        await offline_engine.generate(brief)


# ---------------- router tests ----------------
def _client() -> TestClient:
    app = FastAPI()
    app.include_router(branding_router)
    return TestClient(app)


def test_router_generate_success() -> None:
    client = _client()
    resp = client.post(
        "/studios/branding/generate",
        json={"company": "Acme", "industry": "SaaS", "values": ["clarity"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["company"] == "Acme"
    assert data["tagline"]


def test_router_generate_validation_error() -> None:
    client = _client()
    resp = client.post(
        "/studios/branding/generate",
        json={"company": "Acme", "industry": "SaaS", "values": []},
    )
    assert resp.status_code == 422


def test_router_generate_studio_error(monkeypatch) -> None:
    from studios.branding import router as branding_router_module

    class _BoomEngine:
        async def generate(self, _brief):
            raise StudioError("boom")

        class _LLM:
            provider = "test"
            model = "test"

            @staticmethod
            def as_dict():
                return {"provider": "test", "model": "test", "offline_mode": True}

        llm = _LLM()

    monkeypatch.setattr(branding_router_module, "_engine", _BoomEngine())
    client = _client()
    resp = client.post(
        "/studios/branding/generate",
        json={"company": "Acme", "industry": "SaaS", "values": ["clarity"]},
    )
    assert resp.status_code == 422


def test_router_health() -> None:
    client = _client()
    resp = client.get("/studios/branding/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
