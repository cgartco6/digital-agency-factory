"""Branding engine — cloud LLM driven, CPU-only host safe."""
from __future__ import annotations

import hashlib
import json

from studios.common.base import StudioError
from studios.common.llm_client import LLMClient

from .schemas import BrandBrief, BrandIdentity, BrandVoice, Persona

_REQUIRED_KEYS = {"tagline", "mission", "positioning", "voice", "personas", "palette"}

_SYSTEM = (
    "You are a world-class brand strategist. Respond with VALID JSON only, "
    "matching this schema: {company, tagline, mission, positioning, voice:"
    "{descriptors:[],do:[],dont:[]}, personas:[{name,role,pain_points:[],"
    "motivators:[]}], palette:['#RRGGBB',...]}. No prose, no fences."
)


class BrandingEngine:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    async def generate(self, brief: BrandBrief) -> BrandIdentity:
        prompt = (
            f"Company: {brief.company}\nIndustry: {brief.industry}\n"
            f"Values: {', '.join(brief.values)}\nTone: {brief.tone}\n"
            f"Audience: {brief.audience}\n"
            "Produce the complete brand identity JSON now."
        )
        raw = await self.llm.complete(_SYSTEM, prompt, max_tokens=1500)
        data = self._parse(raw, brief)
        return self._coerce(data, brief)

    def _parse(self, raw: str, brief: BrandBrief) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return self._synthesize(brief)
        if not isinstance(data, dict) or not _REQUIRED_KEYS.issubset(data.keys()):
            return self._synthesize(brief)
        return data

    def _synthesize(self, brief: BrandBrief) -> dict:
        seed = int(hashlib.sha256(brief.company.encode()).hexdigest(), 16)
        palette = [f"#{((seed >> (i * 8)) & 0xFFFFFF):06X}" for i in range(1, 5)]
        return {
            "company": brief.company,
            "tagline": f"{brief.company}: {brief.values[0]} at scale.",
            "mission": (
                f"To empower {brief.audience} in {brief.industry} through "
                f"{', '.join(brief.values)}."
            ),
            "positioning": f"The {brief.tone} choice for {brief.audience}.",
            "voice": {
                "descriptors": [brief.tone, "clear", "human"],
                "do": ["Lead with outcomes", "Be concrete", "Respect the reader"],
                "dont": ["Use jargon", "Overpromise", "Sound robotic"],
            },
            "personas": [
                {
                    "name": "Primary Buyer",
                    "role": f"{brief.industry} decision-maker",
                    "pain_points": ["Fragmented tooling", "Slow time-to-value"],
                    "motivators": ["ROI", "Reliability", "Speed"],
                }
            ],
            "palette": palette,
        }

    def _coerce(self, data: dict, brief: BrandBrief) -> BrandIdentity:
        try:
            return BrandIdentity(
                company=data.get("company", brief.company),
                tagline=data["tagline"],
                mission=data["mission"],
                positioning=data["positioning"],
                voice=BrandVoice(**data["voice"]),
                personas=[Persona(**p) for p in data["personas"]],
                palette=data["palette"],
                generated_by=f"{self.llm.provider}:{self.llm.model}",
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise StudioError(
                f"Branding generation produced invalid payload: {exc}"
            ) from exc
