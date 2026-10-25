"""Pydantic v2 schemas for the Branding Studio."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BrandBrief(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    company: str = Field(min_length=1, max_length=120)
    industry: str = Field(min_length=1, max_length=120)
    values: List[str] = Field(min_length=1, max_length=10)
    tone: str = Field(default="confident", min_length=2, max_length=60)
    audience: str = Field(default="general market", min_length=2, max_length=200)

    @field_validator("values")
    @classmethod
    def _unique_values(cls, v: List[str]) -> List[str]:
        seen, out = set(), []
        for item in v:
            key = item.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(item.strip())
        if not out:
            raise ValueError("values must contain at least one non-empty entry")
        return out


class BrandVoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    descriptors: List[str]
    do: List[str]
    dont: List[str]


class Persona(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    role: str
    pain_points: List[str]
    motivators: List[str]


class BrandIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str
    tagline: str
    mission: str
    positioning: str
    voice: BrandVoice
    personas: List[Persona]
    palette: List[str]
    generated_by: str

    @field_validator("palette")
    @classmethod
    def _valid_hex(cls, v: List[str]) -> List[str]:
        for color in v:
            if not (color.startswith("#") and len(color) in (4, 7)):
                raise ValueError(f"invalid hex color: {color}")
        return v
