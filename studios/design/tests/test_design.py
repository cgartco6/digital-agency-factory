from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from studios.common.base import StudioError
from studios.common.llm_client import LLMClient
from studios.design.engine import DesignEngine
from studios.design.router import router as design_router
from studios.design.schemas import DesignBrief


class _FakeValidLLM:
    provider = "test"
    model = "test-valid"

    async def complete(self, *_a, **_kw) -> str:
        return json.dumps(
            {
                "colors": [{"name": "primary", "value": "#112233"}],
                "typography": {"family": "Inter", "sizes": [14, 16], "line_height": 1.5},
                "spacing_unit": 8,
                "components": [{"name": "Button", "states": ["default"], "notes": "ok"}],
            }
        )


class _FakeInvalidLLM:
    provider = "test"
    model = "test-invalid"

    async def complete(self, *_a, **_kw) -> str:
        return "definitely not json"


def test_brief_validates_hex() -> None:
    with pytest.raises(ValueError):
        DesignBrief(product="X", primary_color="blue")


def test_brief_uppercases_color() -> None:
    b = DesignBrief(product="X", primary_color="#abc")
    assert b.primary_color == "#ABC"


def test_invalid_surface_rejected() -> None:
    with pytest.raises(ValueError):
        DesignBrief(product="X", surface="vr")


@pytest.mark.asyncio
async def test_design_offline_generation() -> None:
    engine = DesignEngine(llm=LLMClient(api_key=None))
    system = await engine.generate(DesignBrief(product="Northwind Portal"))
    assert system.spacing_unit == 8
    assert any(c.name == "primary" for c in system.colors)
    assert system.typography.sizes == sorted(system.typography.sizes)
    assert all(c.states for c in system.components)


@pytest.mark.asyncio
async def test_design_parses_valid_llm_json() -> None:
    engine = DesignEngine(llm=_FakeValidLLM())
    system = await engine.generate(DesignBrief(product="Northwind Portal"))
    assert system.spacing_unit == 8
    assert system.typography.family == "Inter"


@pytest.mark.asyncio
async def test_design_parses_invalid_llm_json_falls_back() -> None:
    engine = DesignEngine(llm=_FakeInvalidLLM())
    system = await engine.generate(DesignBrief(product="Northwind Portal"))
    assert system.spacing_unit == 8  # from synthesis


@pytest.mark.asyncio
async def test_design_raises_on_malformed_payload(monkeypatch) -> None:
    engine = DesignEngine(llm=LLMClient(api_key=None))
    monkeypatch.setattr(engine, "_parse", lambda _raw, _brief: {"bogus": 1})
    with pytest.raises(StudioError):
        await engine.generate(DesignBrief(product="X"))


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(design_router)
    return TestClient(app)


def test_router_generate_success() -> None:
    client = _client()
    resp = client.post("/studios/design/generate", json={"product": "Northwind"})
    assert resp.status_code == 200
    assert resp.json()["product"] == "Northwind"


def test_router_generate_validation_error() -> None:
    client = _client()
    resp = client.post(
        "/studios/design/generate", json={"product": "X", "primary_color": "bad"}
    )
    assert resp.status_code == 422


def test_router_generate_studio_error(monkeypatch) -> None:
    from studios.design import router as design_router_module

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

    monkeypatch.setattr(design_router_module, "_engine", _BoomEngine())
    client = _client()
    resp = client.post("/studios/design/generate", json={"product": "Northwind"})
    assert resp.status_code == 422


def test_router_health() -> None:
    client = _client()
    resp = client.get("/studios/design/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
