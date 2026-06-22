import io
import os
import logging
from PIL import Image, ImageDraw, ImageFont, ImageOps

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader

from api.cover_models import CoverRequest, CoverTemplate
from api.utils import _hex_to_rgb, decode_base64_photo, fetch_image, pil_image_to_reportlab

logger = logging.getLogger(__name__)

# ── Print specifications ──────────────────────────────────────────────
TRIM_W_MM = 200.0
TRIM_H_MM = 250.0
BLEED_MM = 3.0
SAFE_ZONE_MM = 8.0
DPI = 300
MM_TO_PX = DPI / 25.4  # ~11.811

THUMB_W = 600
THUMB_H = 750

# ── Paths ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")

FONT_MAP = {
    "cormorant-garamond": ("CormorantGaramond-Bold.ttf", "CormorantGaramond-Regular.ttf"),
    "crimson-pro": ("CrimsonPro-Bold.ttf", "CrimsonPro-Regular.ttf"),
    "eb-garamond": ("EbGaramond-Bold.ttf", "EbGaramond-Regular.ttf"),
    "libertinus-serif": ("LibertinusSerif-Bold.ttf", "LibertinusSerif-Regular.ttf"),
    "libre-baskerville": ("LibreBaskerville-Bold.ttf", "LibreBaskerville-Regular.ttf"),
    "noto-sans": ("NotoSans-Bold.ttf", "NotoSans-Regular.ttf"),
    "noto-serif": ("NotoSerif-Bold.ttf", "NotoSerif-Regular.ttf"),
    "taviraj": ("Taviraj-Bold.ttf", "Taviraj-Regular.ttf"),
}


def _resolve_font(font_name: str, bold: bool = True) -> str:
    files = FONT_MAP.get(font_name, FONT_MAP["cormorant-garamond"])
    filename = files[0] if bold else files[1]
    return os.path.join(BASE_DIR, "fonts", font_name, filename)


def _mm_to_px(v: float) -> int:
    return round(v * MM_TO_PX)


def _pt_to_px(pt: float) -> int:
    """Convert typographic points to pixels at 300 DPI."""
    return round(pt * DPI / 72)


# ── Text helpers ──────────────────────────────────────────────────────

def _wrap_text_pillow(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines = []
    current = words[0]
    for word in words[1:]:
        test = current + " " + word
        bbox = font.getbbox(test)
        if (bbox[2] - bbox[0]) <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _draw_centered_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
                         fill, center_x: int, y: int) -> int:
    """Draw text centered horizontally at (center_x, y). Returns the bottom y."""
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((center_x - tw // 2, y), text, font=font, fill=fill)
    return y + th


def _draw_vertical_text(image: Image.Image, text: str, font: ImageFont.FreeTypeFont,
                         fill, center_x: int, center_y: int):
    """Draw text rotated 90 degrees CCW (reads bottom-to-top)."""
    tmp = Image.new("RGBA", (2000, 500), (0, 0, 0, 0))
    tmp_draw = ImageDraw.Draw(tmp)
    bbox = tmp_draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    # Draw at origin offset
    tmp_draw.text((-bbox[0], -bbox[1]), text, font=font, fill=fill)
    tmp = tmp.crop((0, 0, tw, th))
    rotated = tmp.rotate(90, expand=True, resample=Image.BICUBIC)
    paste_x = center_x - rotated.width // 2
    paste_y = center_y - rotated.height // 2
    image.paste(rotated, (paste_x, paste_y), rotated)


# ── Logo helper ───────────────────────────────────────────────────────

def _make_white_logo(target_width_px: int) -> Image.Image | None:
    if not os.path.isfile(LOGO_PATH):
        logger.warning(f"Logo not found at {LOGO_PATH}, skipping back cover logo")
        return None
    logo = Image.open(LOGO_PATH).convert("RGBA")
    r, g, b, a = logo.split()

    # Check if alpha channel has real transparency
    has_transparency = a.getextrema()[0] < 250
    if has_transparency:
        mask = a
    else:
        # Logo has opaque white background -- derive mask from luminance.
        # Dark/colored pixels = logo shape, white pixels = background.
        gray = logo.convert("L")
        mask = ImageOps.invert(gray)
        # Sharpen edges: anything noticeably non-white becomes fully opaque
        mask = mask.point(lambda p: min(255, p * 4))

    scale = target_width_px / logo.width
    new_h = round(logo.height * scale)
    white_ch = Image.new("L", logo.size, 255)
    result = Image.merge("RGBA", (white_ch, white_ch, white_ch, mask))
    return result.resize((target_width_px, new_h), Image.LANCZOS)


# ── Spread geometry ───────────────────────────────────────────────────

class SpreadGeometry:
    def __init__(self, spine_mm: float):
        self.spine_mm = spine_mm
        self.spread_w_mm = BLEED_MM + TRIM_W_MM + spine_mm + TRIM_W_MM + BLEED_MM
        self.spread_h_mm = BLEED_MM + TRIM_H_MM + BLEED_MM
        self.spread_w_px = _mm_to_px(self.spread_w_mm)
        self.spread_h_px = _mm_to_px(self.spread_h_mm)

        # Panel boundaries in px (left edge of each region)
        self.back_left = 0
        self.back_right = _mm_to_px(BLEED_MM + TRIM_W_MM)
        self.spine_left = self.back_right
        self.spine_right = self.spine_left + _mm_to_px(spine_mm)
        self.front_left = self.spine_right
        self.front_right = self.spread_w_px

        # Trim boundaries (without bleed) for each panel
        self.bleed_px = _mm_to_px(BLEED_MM)
        self.safe_px = _mm_to_px(SAFE_ZONE_MM)

        # Front cover trim area (for thumbnail cropping)
        self.front_trim_left = _mm_to_px(BLEED_MM + TRIM_W_MM + spine_mm)
        self.front_trim_right = self.front_trim_left + _mm_to_px(TRIM_W_MM)
        self.trim_top = self.bleed_px
        self.trim_bottom = self.bleed_px + _mm_to_px(TRIM_H_MM)


# ── Template 1: Classic ──────────────────────────────────────────────

def _compose_classic(photo: Image.Image, req: CoverRequest, geo: SpreadGeometry) -> Image.Image:
    bg_color = _hex_to_rgb(req.color)
    img = Image.new("RGB", (geo.spread_w_px, geo.spread_h_px), bg_color)
    draw = ImageDraw.Draw(img)

    # ── Front cover ──
    front_cx = (geo.front_left + geo.front_right) // 2
    front_inner_left = geo.front_left + geo.safe_px
    front_inner_right = geo.front_right - geo.safe_px
    front_content_w = front_inner_right - front_inner_left
    panel_h = geo.spread_h_px

    # Title
    title_color = _hex_to_rgb(req.title_color)
    title_font_size = _pt_to_px(req.title_font_size)
    title_font = ImageFont.truetype(_resolve_font(req.title_font), title_font_size)
    title_y = geo.bleed_px + round(_mm_to_px(TRIM_H_MM) * 0.15)

    title_lines = _wrap_text_pillow(req.title, title_font, front_content_w)

    # Decorative line above title
    line_w = round(front_content_w * 0.6)
    line_x1 = front_cx - line_w // 2
    line_x2 = front_cx + line_w // 2
    line_y = title_y - _mm_to_px(4)
    draw.line([(line_x1, line_y), (line_x2, line_y)], fill=title_color, width=2)

    # Draw title lines
    line_height = round(title_font_size * 1.25)
    for line_text in title_lines:
        _draw_centered_text(draw, line_text, title_font, title_color, front_cx, title_y)
        title_y += line_height
    title_bottom = title_y

    # Decorative line below title
    line_y_below = title_bottom + _mm_to_px(3)
    draw.line([(line_x1, line_y_below), (line_x2, line_y_below)], fill=title_color, width=2)

    # Photo area: 57% of trim height, centered vertically in remaining space
    photo_area_h = round(_mm_to_px(TRIM_H_MM) * 0.57)
    border_px = _mm_to_px(4)

    # Vertical centering: between below-title line and subtitle area
    subtitle_reserve = _mm_to_px(25)  # reserve space at bottom for subtitle
    available_top = line_y_below + _mm_to_px(5)
    available_bottom = geo.trim_bottom - subtitle_reserve
    photo_outer_h = min(photo_area_h, available_bottom - available_top)
    photo_outer_w = min(front_content_w, round(photo_outer_h * 0.85))  # maintain reasonable aspect

    photo_center_y = (available_top + available_bottom) // 2
    photo_top = photo_center_y - photo_outer_h // 2
    photo_left = front_cx - photo_outer_w // 2

    # White border rectangle
    draw.rectangle(
        [photo_left, photo_top, photo_left + photo_outer_w, photo_top + photo_outer_h],
        fill="white",
    )

    # Crop and paste photo inside border
    inner_w = photo_outer_w - 2 * border_px
    inner_h = photo_outer_h - 2 * border_px
    if inner_w > 0 and inner_h > 0:
        fitted = ImageOps.fit(photo, (inner_w, inner_h), method=Image.LANCZOS)
        img.paste(fitted, (photo_left + border_px, photo_top + border_px))

    # Subtitle below photo
    if req.subtitle:
        subtitle_color = _hex_to_rgb(req.subtitle_color)
        sub_font_size = _pt_to_px(req.subtitle_font_size)
        sub_font = ImageFont.truetype(_resolve_font(req.subtitle_font, bold=False), sub_font_size)
        sub_y = photo_top + photo_outer_h + _mm_to_px(5)
        sub_lines = _wrap_text_pillow(req.subtitle, sub_font, front_content_w)
        sub_line_h = round(sub_font_size * 1.3)
        for sl in sub_lines:
            _draw_centered_text(draw, sl, sub_font, subtitle_color, front_cx, sub_y)
            sub_y += sub_line_h

    # ── Spine ──
    spine_cx = (geo.spine_left + geo.spine_right) // 2
    spine_w_px = geo.spine_right - geo.spine_left

    if spine_w_px > _mm_to_px(6):
        title_color = _hex_to_rgb(req.title_color)
        # Title vertical (bottom-to-top)
        max_spine_font = max(8, spine_w_px - _mm_to_px(4))
        spine_title_size = min(_pt_to_px(12), max_spine_font)
        spine_title_font = ImageFont.truetype(_resolve_font(req.title_font), spine_title_size)

        spine_center_y = geo.spread_h_px // 2
        _draw_vertical_text(img, req.title, spine_title_font, title_color, spine_cx, spine_center_y)

        # Subtitle horizontal at bottom (only if spine is wide enough)
        if req.subtitle and spine_w_px > _mm_to_px(8):
            subtitle_color = _hex_to_rgb(req.subtitle_color)
            spine_sub_size = min(_pt_to_px(7), max(6, spine_w_px - _mm_to_px(5)))
            spine_sub_font = ImageFont.truetype(_resolve_font(req.subtitle_font, bold=False), spine_sub_size)
            sub_bbox = spine_sub_font.getbbox(req.subtitle)
            sub_tw = sub_bbox[2] - sub_bbox[0]
            # Only draw if it fits within the spine width
            if sub_tw <= spine_w_px - 4:
                sub_x = spine_cx - sub_tw // 2
                sub_y = geo.trim_bottom - _mm_to_px(8)
                draw.text((sub_x, sub_y), req.subtitle, font=spine_sub_font, fill=subtitle_color)

    # ── Back cover ──
    back_cx = (geo.back_left + geo.back_right) // 2
    logo = _make_white_logo(_mm_to_px(28))
    if logo:
        logo_x = back_cx - logo.width // 2
        logo_y = geo.bleed_px + round(_mm_to_px(TRIM_H_MM) * 0.70)
        img.paste(logo, (logo_x, logo_y), logo)

    return img


# ── Template 2: Full Bleed ────────────────────────────────────────────

def _compose_full_bleed(photo: Image.Image, req: CoverRequest, geo: SpreadGeometry) -> Image.Image:
    bg_color = _hex_to_rgb(req.color)

    # Start with solid color background for the entire spread
    img = Image.new("RGBA", (geo.spread_w_px, geo.spread_h_px), (*bg_color, 255))

    # Photo covers front + spine only (not back)
    photo_region_w = geo.spread_w_px - geo.spine_left  # spine + front
    photo_fitted = ImageOps.fit(photo, (photo_region_w, geo.spread_h_px), method=Image.LANCZOS)
    img.paste(photo_fitted, (geo.spine_left, 0))

    # ── Front cover gradient (bottom 40%, up to 70% opacity) ──
    gradient = Image.new("RGBA", (geo.spread_w_px, geo.spread_h_px), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(gradient)
    gradient_start_y = round(geo.spread_h_px * 0.55)

    for y in range(gradient_start_y, geo.spread_h_px):
        progress = (y - gradient_start_y) / (geo.spread_h_px - gradient_start_y)
        alpha = round(180 * progress)
        grad_draw.line(
            [(geo.front_left, y), (geo.front_right, y)],
            fill=(0, 0, 0, alpha),
        )

    # ── Spine dark strip ──
    for y in range(geo.spread_h_px):
        grad_draw.line(
            [(geo.spine_left, y), (geo.spine_right, y)],
            fill=(0, 0, 0, 70),
        )

    img = Image.alpha_composite(img, gradient)

    # ── Front cover text ──
    front_inner_left = geo.front_left + geo.safe_px
    front_inner_right = geo.front_right - geo.safe_px
    front_content_w = front_inner_right - front_inner_left

    # Subtitle top-left
    subtitle_color = _hex_to_rgb(req.subtitle_color)
    title_color = _hex_to_rgb(req.title_color)
    if req.subtitle:
        sub_font_size = _pt_to_px(req.subtitle_font_size)
        sub_font = ImageFont.truetype(_resolve_font(req.subtitle_font, bold=False), sub_font_size)
        sub_x = front_inner_left
        sub_y = geo.bleed_px + round(_mm_to_px(TRIM_H_MM) * 0.10)
        draw = ImageDraw.Draw(img)
        draw.text((sub_x + 2, sub_y + 2), req.subtitle, font=sub_font, fill=(0, 0, 0, 140))
        draw.text((sub_x, sub_y), req.subtitle, font=sub_font, fill=subtitle_color)

    # Title bottom-left, large bold
    title_font_size = _pt_to_px(req.title_font_size)
    title_font = ImageFont.truetype(_resolve_font(req.title_font), title_font_size)
    title_lines = _wrap_text_pillow(req.title, title_font, front_content_w)
    line_height = round(title_font_size * 1.15)

    title_block_h = line_height * len(title_lines)
    title_start_y = geo.bleed_px + round(_mm_to_px(TRIM_H_MM) * 0.78) - title_block_h

    draw = ImageDraw.Draw(img)
    ty = title_start_y
    for line_text in title_lines:
        draw.text((front_inner_left + 3, ty + 3), line_text, font=title_font, fill=(0, 0, 0, 160))
        draw.text((front_inner_left, ty), line_text, font=title_font, fill=title_color)
        ty += line_height

    # ── Spine text ──
    spine_cx = (geo.spine_left + geo.spine_right) // 2
    spine_w_px = geo.spine_right - geo.spine_left

    if spine_w_px > _mm_to_px(6):
        max_spine_font = max(8, spine_w_px - _mm_to_px(4))
        spine_title_size = min(_pt_to_px(11), max_spine_font)
        spine_title_font = ImageFont.truetype(_resolve_font(req.title_font), spine_title_size)
        spine_center_y = geo.spread_h_px // 2

        _draw_vertical_text(img, req.title, spine_title_font, (0, 0, 0, 160), spine_cx + 2, spine_center_y + 2)
        _draw_vertical_text(img, req.title, spine_title_font, title_color, spine_cx, spine_center_y)

    # ── Back cover (solid color) with logo ──
    back_cx = (geo.back_left + geo.back_right) // 2
    logo = _make_white_logo(_mm_to_px(28))
    if logo:
        logo_x = back_cx - logo.width // 2
        logo_y = geo.bleed_px + round(_mm_to_px(TRIM_H_MM) * 0.70)
        img.paste(logo, (logo_x, logo_y), logo)

    return img.convert("RGB")


# ── PDF wrapping ──────────────────────────────────────────────────────

def _image_to_pdf(image: Image.Image, width_mm: float, height_mm: float) -> bytes:
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(width_mm * mm, height_mm * mm))
    img_buf = pil_image_to_reportlab(image)
    reader = ImageReader(img_buf)
    c.drawImage(reader, 0, 0, width=width_mm * mm, height=height_mm * mm)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


# ── Thumbnail extraction ─────────────────────────────────────────────

def _extract_thumbnail(spread: Image.Image, geo: SpreadGeometry) -> bytes:
    front_crop = spread.crop((
        geo.front_trim_left,
        geo.trim_top,
        geo.front_trim_right,
        geo.trim_bottom,
    ))
    thumb = front_crop.resize((THUMB_W, THUMB_H), Image.LANCZOS)
    buf = io.BytesIO()
    thumb.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ── Public API ────────────────────────────────────────────────────────

def generate_cover(request: CoverRequest) -> tuple[bytes, bytes]:
    """Generate a print-ready cover spread PDF and front-cover thumbnail.

    Returns (pdf_bytes, thumbnail_png_bytes).
    """
    if request.photo:
        photo = decode_base64_photo(request.photo)
    elif request.photo_url:
        photo = fetch_image(request.photo_url)
        if photo is None:
            raise ValueError(f"Failed to fetch photo from URL: {request.photo_url}")
    else:
        raise ValueError("No photo source provided")

    # Cap oversized photos to limit memory
    max_dim = 8000
    if photo.width > max_dim or photo.height > max_dim:
        photo.thumbnail((max_dim, max_dim), Image.LANCZOS)
        logger.info(f"Photo downscaled to {photo.width}x{photo.height}")

    if photo.width < 400 or photo.height < 400:
        logger.warning(f"Photo resolution is low ({photo.width}x{photo.height}), result may be blurry")

    spine_mm = request.get_spine_width_mm()
    geo = SpreadGeometry(spine_mm)

    logger.info(
        f"Cover spread: {geo.spread_w_mm:.1f}x{geo.spread_h_mm:.1f}mm "
        f"({geo.spread_w_px}x{geo.spread_h_px}px), spine={spine_mm:.1f}mm"
    )

    if request.template == CoverTemplate.CLASSIC:
        spread = _compose_classic(photo, request, geo)
    else:
        spread = _compose_full_bleed(photo, request, geo)

    pdf_bytes = _image_to_pdf(spread, geo.spread_w_mm, geo.spread_h_mm)
    thumb_bytes = _extract_thumbnail(spread, geo)

    return pdf_bytes, thumb_bytes
