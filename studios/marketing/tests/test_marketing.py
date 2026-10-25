from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from studios.common.base import StudioError
from studios.common.llm_client import LLMClient
from studios.marketing.engine import MarketingEngine
from studios.marketing.router import router as marketing_router
from studios.marketing.schemas import CampaignBrief


class _FakeValidLLM:
    provider = "test"
    model = "test-valid"

    async def complete(self, *_a, **_kw) -> str:
        return json.dumps(
            {
                "allocations": [
                    {
                        "channel": "email",
                        "budget_usd": 500.0,
                        "expected_reach": 1000,
                        "kpi": "Engagement",
                    },
                    {
                        "channel": "seo",
                        "budget_usd": 500.0,
                        "expected_reach": 2000,
                        "kpi": "Engagement",
                    },
                ],
                "milestones": {"week_1": "launch"},
            }
        )


class _FakeInvalidLLM:
    provider = "test"
    model = "test-invalid"

    async def complete(self, *_a, **_kw) -> str:
        return "definitely not json"


def test_channels_normalized_and_deduped() -> None:
    b = CampaignBrief(
        product="X",
        budget_usd=1000,
        duration_days=30,
        channels=["Email", "email", "SOCIAL"],
    )
    assert b.channels == ["email", "social"]


def test_zero_budget_rejected() -> None:
    with pytest.raises(ValueError):
        CampaignBrief(product="X", budget_usd=0, duration_days=30, channels=["email"])


@pytest.mark.asyncio
async def test_allocations_sum_to_budget() -> None:
    engine = MarketingEngine(llm=LLMClient(api_key=None))
    brief = CampaignBrief(
        product="Northwind",
        budget_usd=1000.0,
        duration_days=30,
        channels=["email", "social", "seo"],
    )
    plan = await engine.generate(brief)
    assert abs(sum(a.budget_usd for a in plan.allocations) - 1000.0) < 0.5
    assert plan.milestones
    assert plan.allocations[0].expected_reach > 0


@pytest.mark.asyncio
async def test_marketing_parses_valid_llm_json() -> None:
    engine = MarketingEngine(llm=_FakeValidLLM())
    brief = CampaignBrief(
        product="Northwind", budget_usd=1000.0, duration_days=30,
        channels=["email", "seo"],
    )
    plan = await engine.generate(brief)
    assert len(plan.allocations) == 2
    assert plan.milestones == {"week_1": "launch"}


@pytest.mark.asyncio
async def test_marketing_parses_invalid_llm_json_falls_back() -> None:
    engine = MarketingEngine(llm=_FakeInvalidLLM())
    brief = CampaignBrief(
        product="Northwind", budget_usd=500.0, duration_days=28,
        channels=["email"],
    )
    plan = await engine.generate(brief)
    assert plan.milestones


@pytest.mark.asyncio
async def test_marketing_raises_on_malformed_payload(monkeypatch) -> None:
    engine = MarketingEngine(llm=LLMClient(api_key=None))
    monkeypatch.setattr(engine, "_parse", lambda _raw, _brief: {"bogus": 1})
    with pytest.raises(StudioError):
        await engine.generate(
            CampaignBrief(
                product="X", budget_usd=1000, duration_days=30, channels=["email"]
            )
        )


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(marketing_router)
    return TestClient(app)


def test_router_generate_success() -> None:
    client = _client()
    resp = client.post(
        "/studios/marketing/generate",
        json={
            "product": "Acme",
            "budget_usd": 500,
            "duration_days": 30,
            "channels": ["email"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["product"] == "Acme"


def test_router_generate_validation_error() -> None:
    client = _client()
    resp = client.post(
        "/studios/marketing/generate",
        json={"product": "Acme", "budget_usd": 0, "duration_days": 30, "channels": []},
    )
    assert resp.status_code == 422


def test_router_generate_studio_error(monkeypatch) -> None:
    from studios.marketing import router as marketing_router_module

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

    monkeypatch.setattr(marketing_router_module, "_engine", _BoomEngine())
    client = _client()
    resp = client.post(
        "/studios/marketing/generate",
        json={
            "product": "Acme",
            "budget_usd": 500,
            "duration_days": 30,
            "channels": ["email"],
        },
    )
    assert resp.status_code == 422


def test_router_health() -> None:
    client = _client()
    resp = client.get("/studios/marketing/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
