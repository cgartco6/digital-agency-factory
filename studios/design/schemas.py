from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HEX_LEN = (4, 7)


class DesignBrief(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    product: str = Field(min_length=1, max_length=120)
    surface: str = Field(default="web", pattern="^(web|mobile|desktop|hybrid)$")
    primary_color: str = Field(default="#4F46E5")
    mood: str = Field(default="modern", min_length=2, max_length=40)

    @field_validator("primary_color")
    @classmethod
    def _hex(cls, v: str) -> str:
        if not (v.startswith("#") and len(v) in _HEX_LEN):
            raise ValueError("primary_color must be a hex string like #RRGGBB")
        return v.upper()


class ColorToken(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    value: str


class TypographyScale(BaseModel):
    model_config = ConfigDict(extra="forbid")
    family: str
    sizes: List[int]
    line_height: float


class ComponentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    states: List[str]
    notes: str


class DesignSystem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product: str
    surface: str
    colors: List[ColorToken]
    typography: TypographyScale
    spacing_unit: int
    components: List[ComponentSpec]
    generated_by: str

    @field_validator("spacing_unit")
    @classmethod
    def _positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("spacing_unit must be positive")
        return v
