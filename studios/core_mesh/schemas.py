from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from studios.branding.schemas import BrandIdentity
from studios.design.schemas import DesignSystem
from studios.marketing.schemas import CampaignPlan


class MeshRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    company: str = Field(min_length=1, max_length=120)
    industry: str = Field(min_length=1, max_length=120)
    values: list[str] = Field(min_length=1, max_length=10)
    tone: str = "confident"
    audience: str = "general market"
    surface: str = "web"
    primary_color: str = "#4F46E5"
    budget_usd: float = Field(default=5000.0, gt=0)
    duration_days: int = Field(default=30, gt=0)
    channels: list[str] = Field(default_factory=lambda: ["email", "social", "seo"])


class LaunchPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company: str
    branding: BrandIdentity
    design: DesignSystem
    campaign: CampaignPlan
    consistency_score: float
    generated_by: str
    warnings: list[str] = Field(default_factory=list)


class MeshStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool
    studio_count: int
    llm_provider: str
    llm_model: str
    offline_mode: bool
    detail: Optional[str] = None
