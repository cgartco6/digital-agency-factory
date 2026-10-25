"""Core Mesh — fans out to every studio and reconciles the outputs."""
from __future__ import annotations

from studios.branding.engine import BrandingEngine
from studios.branding.schemas import BrandBrief
from studios.common.llm_client import LLMClient
from studios.design.engine import DesignEngine
from studios.design.schemas import DesignBrief
from studios.marketing.engine import MarketingEngine
from studios.marketing.schemas import CampaignBrief

from .schemas import LaunchPackage, MeshRequest


class CoreMeshEngine:
    def __init__(self, llm: LLMClient | None = None) -> None:
        shared = llm or LLMClient()
        self.llm = shared
        self.branding = BrandingEngine(shared)
        self.design = DesignEngine(shared)
        self.marketing = MarketingEngine(shared)

    async def build(self, req: MeshRequest) -> LaunchPackage:
        brand_brief = BrandBrief(
            company=req.company,
            industry=req.industry,
            values=req.values,
            tone=req.tone,
            audience=req.audience,
        )
        branding = await self.branding.generate(brand_brief)

        design_brief = DesignBrief(
            product=req.company,
            surface=req.surface,
            primary_color=req.primary_color,
        )
        design = await self.design.generate(design_brief)

        campaign_brief = CampaignBrief(
            product=req.company,
            objective="awareness",
            budget_usd=req.budget_usd,
            duration_days=req.duration_days,
            channels=req.channels,
        )
        campaign = await self.marketing.generate(campaign_brief)

        score, warnings = self._consistency(branding, design, campaign)
        return LaunchPackage(
            company=req.company,
            branding=branding,
            design=design,
            campaign=campaign,
            consistency_score=score,
            generated_by=f"{self.llm.provider}:{self.llm.model}",
            warnings=warnings,
        )

    @staticmethod
    def _consistency(branding, design, campaign) -> tuple[float, list[str]]:
        warnings: list[str] = []
        checks = 0
        passed = 0

        checks += 1
        primaries = {c.value.upper() for c in design.colors if c.name == "primary"}
        brand_palette = {p.upper() for p in branding.palette}
        if primaries & brand_palette:
            passed += 1
        else:
            warnings.append("Design primary not present in brand palette.")

        checks += 1
        if campaign.product == branding.company:
            passed += 1
        else:
            warnings.append("Campaign product name does not match brand company.")

        checks += 1
        allocated = sum(a.budget_usd for a in campaign.allocations)
        if abs(allocated - campaign.total_budget_usd) < 0.5:
            passed += 1
        else:
            warnings.append("Campaign budget not fully allocated.")

        checks += 1
        if branding.personas:
            passed += 1
        else:
            warnings.append("No personas generated.")

        score = round((passed / checks) * 100.0, 2)
        return score, warnings
