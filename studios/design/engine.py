from __future__ import annotations

import json

from studios.common.base import StudioError
from studios.common.llm_client import LLMClient

from .schemas import (
    ColorToken,
    ComponentSpec,
    DesignBrief,
    DesignSystem,
    TypographyScale,
)

_REQUIRED_KEYS = {"colors", "typography", "spacing_unit", "components"}

_SYSTEM = (
    "You are a senior product designer. Return VALID JSON only matching: "
    "{colors:[{name,value}], typography:{family,sizes:[],line_height}, "
    "spacing_unit:int, components:[{name,states:[],notes}]}. No prose."
)


class DesignEngine:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    async def generate(self, brief: DesignBrief) -> DesignSystem:
        prompt = (
            f"Product: {brief.product}\nSurface: {brief.surface}\n"
            f"Primary color: {brief.primary_color}\nMood: {brief.mood}\n"
            "Produce the design system JSON."
        )
        raw = await self.llm.complete(_SYSTEM, prompt, max_tokens=1200)
        data = self._parse(raw, brief)
        return self._coerce(data, brief)

    def _parse(self, raw: str, brief: DesignBrief) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return self._synthesize(brief)
        if not isinstance(data, dict) or not _REQUIRED_KEYS.issubset(data.keys()):
            return self._synthesize(brief)
        return data

    def _synthesize(self, brief: DesignBrief) -> dict:
        return {
            "colors": [
                {"name": "primary", "value": brief.primary_color},
                {"name": "surface", "value": "#FFFFFF"},
                {"name": "text", "value": "#0F172A"},
                {"name": "muted", "value": "#64748B"},
            ],
            "typography": {
                "family": "Inter",
                "sizes": [12, 14, 16, 20, 24, 32, 48],
                "line_height": 1.5,
            },
            "spacing_unit": 8,
            "components": [
                {
                    "name": "Button",
                    "states": ["default", "hover", "active", "disabled"],
                    "notes": "48px min target",
                },
                {"name": "Card", "states": ["default", "elevated"], "notes": "16px radius"},
                {"name": "Input", "states": ["default", "focus", "error"], "notes": "1px border"},
            ],
        }

    def _coerce(self, data: dict, brief: DesignBrief) -> DesignSystem:
        try:
            return DesignSystem(
                product=brief.product,
                surface=brief.surface,
                colors=[ColorToken(**c) for c in data["colors"]],
                typography=TypographyScale(**data["typography"]),
                spacing_unit=int(data["spacing_unit"]),
                components=[ComponentSpec(**c) for c in data["components"]],
                generated_by=f"{self.llm.provider}:{self.llm.model}",
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise StudioError(
                f"Design generation produced invalid payload: {exc}"
            ) from exc
