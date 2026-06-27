from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from datetime import datetime


class BookInfo(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    subtitle: Optional[str] = None
    author: Optional[str] = None
    language: str = Field(default="az", max_length=10)
    brand: str = Field(default="memona", max_length=50)


class Margins(BaseModel):
    inside: float = Field(default=24, ge=5, le=50)
    outside: float = Field(default=20, ge=5, le=50)
    top: float = Field(default=20, ge=5, le=50)
    bottom: float = Field(default=22, ge=5, le=50)


class SupportedFont(str, Enum):
    NOTO_SERIF = "noto-serif"
    LIBRE_BASKERVILLE = "libre-baskerville"
    EB_GARAMOND = "eb-garamond"
    CORMORANT_GARAMOND = "cormorant-garamond"
    LIBERTINUS_SERIF = "libertinus-serif"
    TAVIRAJ = "taviraj"
    CRIMSON_PRO = "crimson-pro"



class PageSize(str, Enum):
    US_TRADE_8X10 = "8x10"
    US_TRADE_6X9 = "6x9"
    A4 = "A4"
    A5 = "A5"
    B5 = "B5"
    LETTER = "letter"
    CUSTOM = "custom"


PAGE_SIZE_PRESETS_MM: dict[str, tuple[float, float]] = {
    "8x10": (203.2, 254.0),
    "6x9": (152.4, 228.6),
    "A4": (210.0, 297.0),
    "A5": (148.0, 210.0),
    "B5": (176.0, 250.0),
    "letter": (215.9, 279.4),
}


class DividerStyle(str, Enum):
    SIMPLE_LINE = "simple-line"
    GRADUATED_DOTS = "graduated-dots"
    ORNAMENTAL_FLORAL = "ornamental-floral"
    LINE_WITH_HEART = "line-with-heart"
    LINE_WITH_DIAMOND = "line-with-diamond"
    LINE_WITH_EYES = "line-with-eyes"
    LINE_WITH_CIRCLES = "line-with-circles"
    ORNAMENTAL_FLAT = "ornamental-flat"


class StyleConfig(BaseModel):
    page_size: PageSize = Field(default=PageSize.B5)
    custom_width_mm: Optional[float] = Field(default=None, ge=100, le=400)
    custom_height_mm: Optional[float] = Field(default=None, ge=100, le=500)
    margins_mm: Margins = Field(default_factory=Margins)
    font_name: SupportedFont = Field(default=SupportedFont.LIBRE_BASKERVILLE)
    body_font_size: float = Field(default=11, ge=6, le=24)
    title_font_size: float = Field(default=21, ge=12, le=48)
    line_height: float = Field(default=1.55, ge=1.0, le=3.0)
    paragraph_spacing: float = Field(default=0.4, ge=0, le=2.0)
    show_page_numbers: bool = Field(default=True)
    qr_color: str = Field(default="#1A5C52")
    qr_logo_enabled: bool = Field(default=True)
    logo_color: str = Field(default="#184b52")

    # Story opener layout
    qr_code_size: float = Field(default=60, ge=20, le=200)
    qr_top_spacing: float = Field(default=10, ge=0, le=100)
    title_spacing: float = Field(default=35, ge=0, le=100)
    date_spacing: float = Field(default=10, ge=0, le=100)
    divider_spacing: float = Field(default=14, ge=0, le=100)
    story_top_spacing: float = Field(default=40, ge=0, le=100)
    divider_line_width: float = Field(default=0.5, ge=0.1, le=5.0)
    divider_style: DividerStyle = Field(default=DividerStyle.SIMPLE_LINE)

    # Image styling
    image_border_width: float = Field(default=0.5, ge=0, le=5.0)
    image_border_color: str = Field(default="#BFBFBF")
    image_border_padding: float = Field(default=4, ge=0, le=20)
    inline_photos_enabled: bool = Field(default=True)  # when False, landscape photos go to their own page/collage instead of inline on the QR/text page
    collage_image_gap: float = Field(default=1.0, ge=0, le=50)  # points — gap/divider between photos in a multi-photo collage
    full_page_image_margin: float = Field(default=0, ge=0, le=50)

    # Colors
    date_color: str = Field(default="#737373")
    divider_color: str = Field(default="#B3B3B3")
    page_number_color: str = Field(default="#666666")
    contributor_color: str = Field(default="#8C8C8C")
    body_text_color: str = Field(default="#000000")

    # Typography
    date_font_size: float = Field(default=10, ge=6, le=24)
    page_number_font_size: float = Field(default=9, ge=6, le=24)
    contributor_font_size: float = Field(default=11, ge=6, le=24)

    # Contributor layout
    contributor_spacing: float = Field(default=8, ge=0, le=100)

    # Padding
    min_page_count: int = Field(default=200, ge=1, le=2000)

    # Print cut margin (empty space added to outer edges for printhouse trimming)
    print_cut_margin: float = Field(default=0, ge=0, le=30)

    # Story reordering to reduce filler pages
    allow_reorder: bool = Field(default=False)
    allow_reorder_count: int = Field(default=0, ge=0)
    # allow_reorder_count=0 means search all remaining stories; N>0 means search only next N

    @field_validator("qr_color", "logo_color", "image_border_color", "date_color", "divider_color", "page_number_color", "contributor_color", "body_text_color")
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        import re
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", v):
            raise ValueError(f"Must be a 6-digit hex color, e.g. '#1A5C52', got '{v}'")
        return v.upper()

    @model_validator(mode="after")
    def validate_custom_page_size(self) -> "StyleConfig":
        if self.page_size == PageSize.CUSTOM:
            if self.custom_width_mm is None or self.custom_height_mm is None:
                raise ValueError(
                    "custom_width_mm and custom_height_mm are required when page_size is 'custom'"
                )
        return self

    def get_page_dimensions_mm(self) -> tuple[float, float]:
        if self.page_size == PageSize.CUSTOM:
            return (self.custom_width_mm, self.custom_height_mm)
        return PAGE_SIZE_PRESETS_MM[self.page_size.value]


class Story(BaseModel):
    title: str = Field(..., min_length=1, max_length=1000)
    body: str = Field(..., min_length=1)
    recorded_at: Optional[str] = None
    qr_target_url: str = Field(..., min_length=1)
    image_url: Optional[str] = None   # backwards-compat alias for image_urls[0]
    image_urls: List[str] = Field(default_factory=list)
    contributor: Optional[str] = None
    relation: Optional[str] = None

    @field_validator("image_urls")
    @classmethod
    def validate_image_urls(cls, v: List[str]) -> List[str]:
        filtered = [url.strip() for url in v if url and url.strip()]
        return filtered[:3]

    @model_validator(mode="after")
    def merge_image_fields(self) -> "Story":
        # Merge image_url (old field) into image_urls
        if self.image_url and self.image_url.strip() and self.image_url.strip() not in self.image_urls:
            self.image_urls = [self.image_url.strip()] + self.image_urls
        if len(self.image_urls) > 3:
            self.image_urls = self.image_urls[:3]
        # Keep image_url in sync with first entry for single-image backwards compat
        self.image_url = self.image_urls[0] if self.image_urls else None
        return self

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == "":
            return None
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            raise ValueError(f"Invalid datetime format: {v}")
        return v

    @field_validator("body")
    @classmethod
    def validate_body_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Story body cannot be empty or whitespace only")
        return v.strip()

    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Story title cannot be empty or whitespace only")
        return v.strip()


class OutputConfig(BaseModel):
    file_name: str = Field(default="memona-book.pdf")

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        if not v.endswith(".pdf"):
            raise ValueError("file_name must end with .pdf")
        import os
        basename = os.path.basename(v)
        if basename != v or ".." in v or "/" in v or "\\" in v:
            raise ValueError("file_name must be a simple filename without path separators")
        return basename


class BookRequest(BaseModel):
    book: BookInfo
    style: StyleConfig = Field(default_factory=StyleConfig)
    stories: list[Story] = Field(..., min_length=1)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @field_validator("stories")
    @classmethod
    def validate_stories_not_empty(cls, v: list[Story]) -> list[Story]:
        if len(v) == 0:
            raise ValueError("At least one story is required")
        return v


class GenerateResponse(BaseModel):
    status: str = "ok"
    file_name: str
    storage_path: str
    download_url: str
    page_count: int
    story_count: int


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    details: Optional[list[str]] = None
