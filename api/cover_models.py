from enum import IntEnum
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional


AVAILABLE_FONTS = [
    "cormorant-garamond",
    "crimson-pro",
    "eb-garamond",
    "libertinus-serif",
    "libre-baskerville",
    "noto-sans",
    "noto-serif",
    "taviraj",
]


class CoverTemplate(IntEnum):
    CLASSIC = 1
    FULL_BLEED = 2


class CoverRequest(BaseModel):
    template: CoverTemplate = Field(..., description="1 = Classic, 2 = Full Bleed")
    title: str = Field(..., min_length=1, max_length=200)
    subtitle: Optional[str] = Field(default=None, max_length=300)
    color: str = Field(default="#2D6B5E", description="Hex color for background/back panel")
    page_count: Optional[int] = Field(default=None, ge=10, le=1000)
    spine_width_mm: Optional[float] = Field(default=None, ge=3, le=80)

    # Photo — either base64 or URL
    photo: Optional[str] = Field(default=None, description="Base64-encoded photo (JPEG or PNG)")
    photo_url: Optional[str] = Field(default=None, description="URL to photo (e.g. Supabase signed URL)")

    # Typography — title
    title_font: str = Field(default="cormorant-garamond", description="Font family for title")
    title_font_size: float = Field(default=30.0, ge=12, le=72, description="Title font size in pt")
    title_color: str = Field(default="#FFFFFF", description="Title text color (hex)")

    # Typography — subtitle
    subtitle_font: str = Field(default="noto-sans", description="Font family for subtitle")
    subtitle_font_size: float = Field(default=15.0, ge=8, le=48, description="Subtitle font size in pt")
    subtitle_color: str = Field(default="#FFFFFF", description="Subtitle text color (hex)")

    @field_validator("color", "title_color", "subtitle_color")
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        import re
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", v):
            raise ValueError(f"Must be a 6-digit hex color, e.g. '#2D6B5E', got '{v}'")
        return v.upper()

    @field_validator("title_font", "subtitle_font")
    @classmethod
    def validate_font(cls, v: str) -> str:
        if v not in AVAILABLE_FONTS:
            raise ValueError(f"Unknown font '{v}'. Available: {', '.join(AVAILABLE_FONTS)}")
        return v

    @model_validator(mode="after")
    def require_page_count_or_spine(self) -> "CoverRequest":
        if self.page_count is None and self.spine_width_mm is None:
            raise ValueError("Either page_count or spine_width_mm must be provided")
        return self

    @model_validator(mode="after")
    def require_photo_source(self) -> "CoverRequest":
        if not self.photo and not self.photo_url:
            raise ValueError("Either photo (base64) or photo_url must be provided")
        return self

    def get_spine_width_mm(self) -> float:
        if self.spine_width_mm is not None:
            return self.spine_width_mm
        return (self.page_count / 2) * 0.15 + 6


class CoverResponse(BaseModel):
    status: str = "ok"
    cover_pdf_url: str
    thumbnail_url: str
