from reportlab.lib.units import inch, mm

# ---------- Page dimensions ----------
PAGE_WIDTH = 8 * inch                       # Total page width (8 inches for 8×10 book format)
PAGE_HEIGHT = 10 * inch                     # Total page height (10 inches for 8×10 book format)

DEFAULT_MARGINS = {
    "inside": 24 * mm,                      # Inner margin (spine side, wider for binding)
    "outside": 20 * mm,                     # Outer margin (trim side)
    "top": 16 * mm,                         # Top margin
    "bottom": 18 * mm,                      # Bottom margin (extra room for page numbers)
}

FULL_PAGE_IMAGE_RATIO_TOLERANCE = 0.10

# ---------- Typography ----------
BODY_FONT_SIZE = 11                         # Default font size for story body text (pt)
TITLE_FONT_SIZE = 21                        # Default font size for story titles (pt)
DATE_FONT_SIZE = 10                         # Font size for the recorded date below title (pt)
PAGE_NUMBER_FONT_SIZE = 9                   # Font size for page numbers at bottom (pt)
LINE_HEIGHT_FACTOR = 1.55                   # Multiplier for line spacing (body_font_size × this)

# ---------- Story opener layout (QR + title + date + divider) ----------
QR_CODE_SIZE = 60                           # QR code width/height in points
QR_TOP_SPACING = 10                         # Space between top of content box and QR code (pt)
TITLE_SPACING = 35                          # Space between QR code and story title (pt)
DATE_SPACING = 10                           # Space between title and recorded date (pt)
DIVIDER_SPACING = 14                        # Space between date and horizontal divider line (pt)
STORY_TOP_SPACING = 40                      # Space between divider and start of body text (pt)
DIVIDER_LINE_WIDTH = 0.5                    # Thickness of the horizontal divider line (pt)
DIVIDER_STYLE = "simple-line"               # Default divider style (see DividerStyle enum)

# ---------- Image page styling ----------
IMAGE_BORDER_WIDTH = 0.5                    # Stroke width of the border around story images (pt)
IMAGE_BORDER_COLOR = (0.75, 0.75, 0.75)     # Light gray border color (RGB 0-1)
IMAGE_BORDER_PADDING = 4                    # Padding between image and its border frame (pt)

# ---------- Colors (RGB 0-1 tuples) ----------
DATE_COLOR = (0.45, 0.45, 0.45)             # Medium gray for recorded date text
DIVIDER_COLOR = (0.7, 0.7, 0.7)             # Light gray for horizontal divider lines
PAGE_NUMBER_COLOR = (0.4, 0.4, 0.4)         # Dark gray for page numbers

# ---------- Fonts ----------
# Sans font (always Noto Sans — used for UI elements: dates, page numbers, author)
FONT_SANS_REGULAR = "NotoSans"
FONT_SANS_BOLD = "NotoSansBold"

# Font registry: maps font_name → { variant: (internal_name, relative_ttf_path) }
# To add a new font: drop TTFs in fonts/<name>/, add entry here, and add to SupportedFont enum
FONT_REGISTRY = {
    "noto-serif": {
        "regular": ("NotoSerif", "noto-serif/NotoSerif-Regular.ttf"),
        "bold": ("NotoSerifBold", "noto-serif/NotoSerif-Bold.ttf"),
        "italic": ("NotoSerifItalic", "noto-serif/NotoSerif-Italic.ttf"),
    },
    "libre-baskerville": {
        "regular": ("LibreBaskerville", "libre-baskerville/LibreBaskerville-Regular.ttf"),
        "bold": ("LibreBaskervilleBold", "libre-baskerville/LibreBaskerville-Bold.ttf"),
        "italic": ("LibreBaskervilleItalic", "libre-baskerville/LibreBaskerville-Italic.ttf"),
    },
    "eb-garamond": {
        "regular": ("EBGaramond", "eb-garamond/EbGaramond-Regular.ttf"),
        "bold": ("EBGaramondBold", "eb-garamond/EbGaramond-Bold.ttf"),
        "italic": ("EBGaramondItalic", "eb-garamond/EbGaramond-Italic.ttf"),
    },
    "cormorant-garamond": {
        "regular": ("CormorantGaramond", "cormorant-garamond/CormorantGaramond-Regular.ttf"),
        "bold": ("CormorantGaramondBold", "cormorant-garamond/CormorantGaramond-Bold.ttf"),
        "italic": ("CormorantGaramondItalic", "cormorant-garamond/CormorantGaramond-Italic.ttf"),
    },
    "libertinus-serif": {
        "regular": ("LibertinusSerif", "libertinus-serif/LibertinusSerif-Regular.ttf"),
        "bold": ("LibertinusSerifBold", "libertinus-serif/LibertinusSerif-Bold.ttf"),
        "italic": ("LibertinusSerifItalic", "libertinus-serif/LibertinusSerif-Italic.ttf"),
    },
    "taviraj": {
        "regular": ("Taviraj", "taviraj/Taviraj-Regular.ttf"),
        "bold": ("TavirajBold", "taviraj/Taviraj-Bold.ttf"),
        "italic": ("TavirajItalic", "taviraj/Taviraj-Italic.ttf"),
    },
    "crimson-pro": {
        "regular": ("CrimsonPro", "crimson-pro/CrimsonPro-Regular.ttf"),
        "bold": ("CrimsonProBold", "crimson-pro/CrimsonPro-Bold.ttf"),
        "italic": ("CrimsonProItalic", "crimson-pro/CrimsonPro-Italic.ttf"),
    },
}

DEFAULT_FONT = "noto-serif"                 # Fallback when an unknown font_name is requested


def get_font_names(font_name: str) -> dict:
    """Returns a dict with 'regular', 'bold', 'italic' internal font names for the given font."""
    entry = FONT_REGISTRY.get(font_name, FONT_REGISTRY[DEFAULT_FONT])
    return {
        "regular": entry["regular"][0],
        "bold": entry["bold"][0],
        "italic": entry["italic"][0],
    }


def should_draw_full_page_image(
    img_w: float,
    img_h: float,
    page_w: float,
    page_h: float,
    tolerance: float = FULL_PAGE_IMAGE_RATIO_TOLERANCE,
) -> bool:
    if img_w <= 0 or img_h <= 0 or page_w <= 0 or page_h <= 0:
        return False

    image_ratio = img_w / img_h
    page_ratio = page_w / page_h
    ratio_delta = abs(image_ratio - page_ratio) / page_ratio
    return ratio_delta <= tolerance + 1e-12


def get_full_page_image_rect(
    img_w: float,
    img_h: float,
    page_w: float,
    page_h: float,
    margin: float = 0,
) -> tuple[float, float, float, float]:
    avail_w = page_w - 2 * margin
    avail_h = page_h - 2 * margin
    scale = min(avail_w / img_w, avail_h / img_h)
    draw_w = img_w * scale
    draw_h = img_h * scale
    x = (page_w - draw_w) / 2
    y = (page_h - draw_h) / 2
    return x, y, draw_w, draw_h


def get_content_box(page_num: int, margins: dict, page_width: float = PAGE_WIDTH, page_height: float = PAGE_HEIGHT) -> dict:
    is_right_page = page_num % 2 == 1
    if is_right_page:
        left = margins["inside"]
        right = page_width - margins["outside"]
    else:
        left = margins["outside"]
        right = page_width - margins["inside"]

    top = page_height - margins["top"]
    bottom = margins["bottom"]

    return {
        "left": left,
        "right": right,
        "top": top,
        "bottom": bottom,
        "width": right - left,
        "height": top - bottom,
    }
