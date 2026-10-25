from __future__ import annotations

import json

from studios.common.base import StudioError
from studios.common.llm_client import LLMClient

from .schemas import CampaignBrief, CampaignPlan, ChannelAllocation

_REQUIRED_KEYS = {"allocations", "milestones"}

_SYSTEM = (
    "You are a growth marketing lead. Return VALID JSON only matching: "
    "{allocations:[{channel,budget_usd,expected_reach,kpi}], "
    "milestones:{week_1:str,...}}. No prose."
)

_REACH_PER_DOLLAR = {
    "email": 12.0,
    "seo": 25.0,
    "social": 18.0,
    "paid_search": 5.0,
    "paid_social": 6.0,
    "content": 15.0,
    "influencer": 8.0,
    "pr": 3.0,
}


class MarketingEngine:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    async def generate(self, brief: CampaignBrief) -> CampaignPlan:
        prompt = (
            f"Product: {brief.product}\nObjective: {brief.objective}\n"
            f"Budget USD: {brief.budget_usd}\nDuration days: {brief.duration_days}\n"
            f"Channels: {', '.join(brief.channels)}\n"
            "Produce the campaign plan JSON."
        )
        raw = await self.llm.complete(_SYSTEM, prompt, max_tokens=1200)
        data = self._parse(raw, brief)
        return self._coerce(data, brief)

    def _parse(self, raw: str, brief: CampaignBrief) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return self._synthesize(brief)
        if (
            not isinstance(data, dict)
            or not _REQUIRED_KEYS.issubset(data.keys())
            or not data.get("allocations")
        ):
            return self._synthesize(brief)
        return data

    def _synthesize(self, brief: CampaignBrief) -> dict:
        n = len(brief.channels)
        per_channel = round(brief.budget_usd / n, 2)
        allocations = []
        for i, ch in enumerate(brief.channels):
            budget = per_channel
            if i == n - 1:
                budget = round(brief.budget_usd - per_channel * (n - 1), 2)
            allocations.append(
                {
                    "channel": ch,
                    "budget_usd": budget,
                    "expected_reach": int(budget * _REACH_PER_DOLLAR.get(ch, 10.0)),
                    "kpi": "CPA" if ch.startswith("paid") else "Engagement rate",
                }
            )
        weeks = max(1, brief.duration_days // 7)
        milestones = {
            f"week_{i + 1}": (
                "Launch + baseline" if i == 0
                else "Optimize + scale" if i < weeks - 1
                else "Wrap + report"
            )
            for i in range(weeks)
        }
        return {"allocations": allocations, "milestones": milestones}

    def _coerce(self, data: dict, brief: CampaignBrief) -> CampaignPlan:
        try:
            return CampaignPlan(
                product=brief.product,
                objective=brief.objective,
                duration_days=brief.duration_days,
                total_budget_usd=brief.budget_usd,
                allocations=[ChannelAllocation(**a) for a in data["allocations"]],
                milestones=data.get("milestones", {}),
                generated_by=f"{self.llm.provider}:{self.llm.model}",
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise StudioError(
                f"Marketing generation produced invalid payload: {exc}"
            ) from exc
