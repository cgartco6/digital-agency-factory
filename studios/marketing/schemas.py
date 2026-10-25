from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CampaignBrief(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    product: str = Field(min_length=1, max_length=120)
    objective: str = Field(default="awareness")
    budget_usd: float = Field(gt=0, le=10_000_000)
    duration_days: int = Field(gt=0, le=730)
    channels: List[str] = Field(min_length=1, max_length=10)

    @field_validator("channels")
    @classmethod
    def _normalize(cls, v: List[str]) -> List[str]:
        out = [c.strip().lower() for c in v if c.strip()]
        if not out:
            raise ValueError("at least one channel required")
        return sorted(set(out))


class ChannelAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    channel: str
    budget_usd: float
    expected_reach: int
    kpi: str


class CampaignPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product: str
    objective: str
    duration_days: int
    total_budget_usd: float
    allocations: List[ChannelAllocation]
    milestones: Dict[str, str]
    generated_by: str

    @field_validator("allocations")
    @classmethod
    def _sum_matches(
        cls, v: List[ChannelAllocation], info
    ) -> List[ChannelAllocation]:
        total = info.data.get("total_budget_usd")
        if total is not None:
            allocated = round(sum(a.budget_usd for a in v), 2)
            if abs(allocated - total) > 0.5:
                raise ValueError(
                    f"allocations sum {allocated} != total_budget_usd {total}"
                )
        return v
