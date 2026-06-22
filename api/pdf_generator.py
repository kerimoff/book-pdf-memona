import io
import os
import time
import logging
from typing import Optional

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from PIL import Image

from api.models import BookRequest, Story, StyleConfig
from api.dividers import draw_divider
from api.layout import (
    FONT_SANS_REGULAR, FONT_SANS_BOLD,
    FONT_REGISTRY, get_font_names,
    get_content_box,
    get_full_page_image_rect,
    should_draw_full_page_image,
)
from api.utils import (
    format_date_az,
    draw_qr_vector,
    draw_svg_logo_vector,
    get_svg_natural_size,
    fetch_image,
    wrap_text,
    pil_image_to_reportlab,
    hex_to_rgb_floats,
)

logger = logging.getLogger(__name__)

FONTS_REGISTERED = False
COLLAGE_GUTTER = 4 * mm  # gap between photos in a multi-photo collage


def register_fonts():
    global FONTS_REGISTERED
    if FONTS_REGISTERED:
        return

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Register sans fonts (always needed for UI elements)
    sans_paths = {
        FONT_SANS_REGULAR: os.path.join(base_dir, "fonts", "noto-sans", "NotoSans-Regular.ttf"),
        FONT_SANS_BOLD: os.path.join(base_dir, "fonts", "noto-sans", "NotoSans-Bold.ttf"),
    }
    for name, path in sans_paths.items():
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
            logger.info(f"Registered font: {name} from {path}")
        else:
            logger.warning(f"Font file not found: {path}")

    # Register all serif font families from the registry
    for font_key, variants in FONT_REGISTRY.items():
        for variant_name, (internal_name, rel_path) in variants.items():
            full_path = os.path.join(base_dir, "fonts", rel_path)
            if os.path.exists(full_path):
                pdfmetrics.registerFont(TTFont(internal_name, full_path))
                logger.info(f"Registered font: {internal_name} from {full_path}")
            else:
                logger.warning(f"Font file not found: {full_path}")

    FONTS_REGISTERED = True


class MemonaPDFGenerator:
    def __init__(self, request: BookRequest):
        self.request = request
        self.style = request.style
        self.margins = {
            "inside": request.style.margins_mm.inside * mm,
            "outside": request.style.margins_mm.outside * mm,
            "top": request.style.margins_mm.top * mm,
            "bottom": request.style.margins_mm.bottom * mm,
        }
        # Page dimensions from style config
        width_mm, height_mm = request.style.get_page_dimensions_mm()
        self.page_width = width_mm * mm
        self.page_height = height_mm * mm
        self.print_cut_margin = request.style.print_cut_margin * mm
        self.full_page_image_margin = request.style.full_page_image_margin * mm

        self.body_font_size = request.style.body_font_size
        self.title_font_size = request.style.title_font_size
        self.line_height = self.body_font_size * request.style.line_height
        self.paragraph_spacing = self.line_height * request.style.paragraph_spacing
        self.page_num = 0
        self.logical_page_num = 0
        self._first_story_done = False
        self.buffer = io.BytesIO()
        cut = self.print_cut_margin
        self.c = canvas.Canvas(
            self.buffer,
            pagesize=(self.page_width + cut, self.page_height + 2 * cut),
        )

        # Resolve font names from the selected font_name
        font_names = get_font_names(request.style.font_name.value)
        self.font_serif_regular = font_names["regular"]
        self.font_serif_bold = font_names["bold"]
        self.font_serif_italic = font_names["italic"]

        # Story opener layout
        self.qr_code_size = self.style.qr_code_size
        self.qr_top_spacing = self.style.qr_top_spacing
        self.title_spacing = self.style.title_spacing
        self.date_spacing = self.style.date_spacing
        self.divider_spacing = self.style.divider_spacing
        self.story_top_spacing = self.style.story_top_spacing
        self.divider_line_width = self.style.divider_line_width
        self.divider_style = self.style.divider_style

        # Image styling
        self.image_border_width = self.style.image_border_width
        self.image_border_color = hex_to_rgb_floats(self.style.image_border_color)
        self.image_border_padding = self.style.image_border_padding

        # Colors (hex → RGB 0-1 tuples)
        self.date_color = hex_to_rgb_floats(self.style.date_color)
        self.divider_color = hex_to_rgb_floats(self.style.divider_color)
        self.page_number_color = hex_to_rgb_floats(self.style.page_number_color)
        self.contributor_color = hex_to_rgb_floats(self.style.contributor_color)
        self.body_text_color = hex_to_rgb_floats(self.style.body_text_color)

        # Typography
        self.date_font_size = self.style.date_font_size
        self.page_number_font_size = self.style.page_number_font_size
        self.contributor_font_size = self.style.contributor_font_size
        self.contributor_spacing = self.style.contributor_spacing

        register_fonts()

        _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._logo_path = os.path.join(_base_dir, "assets", "logo", "favicon.svg")
        self._word_logo_path = os.path.join(_base_dir, "assets", "logo", "logo_word.svg")

    def generate(self) -> tuple[bytes, int]:
        start_time = time.time()
        logger.info(f"Starting PDF generation for '{self.request.book.title}' with {len(self.request.stories)} stories")

        self.c._doc.Catalog.setPageLayout("TwoPageRight")

        self._new_page(count_as_logical=False)   # physical pg 1 — alone on right (cover slot)
        self._new_page(count_as_logical=False)   # physical pg 2 — blank endpaper, left of first spread
        self._draw_memona_splash_page()
        self._new_page(count_as_logical=True)    # blank leaf — logical page 2
        self._draw_title_page()

        stories = self.request.stories
        rendered: set[int] = set()
        i = 0
        while i < len(stories):
            if i in rendered:
                i += 1
                continue
            story = stories[i]
            if (
                self.style.allow_reorder
                and story.image_urls
                and self.page_num % 2 == 0
            ):
                limit = self.style.allow_reorder_count or len(stories)
                for j in range(i + 1, min(i + 1 + limit, len(stories))):
                    if j not in rendered and not stories[j].image_urls:
                        logger.info(
                            f"Reordering: drawing story {j + 1} ('{stories[j].title}') "
                            f"before story {i + 1} ('{story.title}') to avoid filler page"
                        )
                        self._draw_story(stories[j])
                        rendered.add(j)
                        break
            logger.info(f"Processing story {i + 1}/{len(stories)}: '{story.title}'")
            self._draw_story(story)
            i += 1

        min_pages = self.style.min_page_count
        if self.page_num < min_pages:
            self._draw_transition_page()
            blank_count = min_pages - self.page_num
            logger.info(f"Adding {blank_count} blank padding pages to reach {min_pages} total")
            for _ in range(blank_count):
                self._new_page()
                self._draw_page_number()

        self.c.save()
        pdf_bytes = self.buffer.getvalue()
        duration = time.time() - start_time
        logger.info(f"PDF generation completed in {duration:.2f}s, {self.page_num} pages, {len(pdf_bytes)} bytes")
        return pdf_bytes, self.page_num

    def _new_page(self, count_as_logical: bool = True):
        if self.page_num > 0:
            self.c.showPage()
        self.page_num += 1
        if count_as_logical:
            self.logical_page_num += 1
        if self.print_cut_margin > 0:
            cut = self.print_cut_margin
            x_off = cut if self.page_num % 2 == 0 else 0
            self.c.translate(x_off, cut)

    def _get_content_box(self):
        return get_content_box(self.page_num, self.margins, self.page_width, self.page_height)

    def _draw_page_number(self):
        if not self.style.show_page_numbers:
            return
        if self.logical_page_num <= 0:
            return
        self.c.setFont(FONT_SANS_REGULAR, self.page_number_font_size)
        self.c.setFillColorRGB(*self.page_number_color)
        num_str = str(self.logical_page_num)
        self.c.drawCentredString(self.page_width / 2, self.margins["bottom"] / 2, num_str)
        self.c.setFillColorRGB(0, 0, 0)

    def _draw_memona_splash_page(self):
        self._new_page(count_as_logical=True)

        if os.path.exists(self._word_logo_path):
            vb_w, vb_h = get_svg_natural_size(self._word_logo_path)
            # size controls the max dimension (width for a wide logo)
            logo_size = self.page_width * 0.70
            logo_x = (self.page_width - logo_size) / 2
            # Rendered height = logo_size * vb_h / vb_w (since vb_w > vb_h)
            logo_h = logo_size * vb_h / vb_w
            # In ReportLab coords the content occupies [y + logo_size - logo_h, y + logo_size]
            # Center that range on the page:
            logo_y = self.page_height / 2 - logo_size + logo_h / 2
            draw_svg_logo_vector(self.c, self._word_logo_path, logo_x, logo_y, logo_size, self.style.logo_color)
            # URL sits just below the bottom of the rendered content
            url_y = logo_y + logo_size - logo_h - 28
        else:
            url_y = self.page_height / 2 - 14

        self.c.setFont(FONT_SANS_REGULAR, 13)
        self.c.setFillColorRGB(0.4, 0.4, 0.4)
        self.c.drawCentredString(self.page_width / 2, url_y, "www.memona.app")
        self.c.setFillColorRGB(0, 0, 0)

    def _draw_title_page(self):
        self._new_page(count_as_logical=True)

        center_x = self.page_width / 2
        center_y = self.page_height / 2

        self.c.setFont(self.font_serif_bold, 28)
        self.c.drawCentredString(center_x, center_y + 30, self.request.book.title)

        if self.request.book.subtitle:
            self.c.setFont(self.font_serif_italic, 16)
            self.c.setFillColorRGB(0.35, 0.35, 0.35)
            self.c.drawCentredString(center_x, center_y - 10, self.request.book.subtitle)
            self.c.setFillColorRGB(0, 0, 0)

        if self.request.book.author:
            self.c.setFont(FONT_SANS_REGULAR, 12)
            self.c.setFillColorRGB(0.4, 0.4, 0.4)
            self.c.drawCentredString(center_x, center_y - 50, self.request.book.author)
            self.c.setFillColorRGB(0, 0, 0)

    def _draw_story(self, story: Story):
        n = len(story.image_urls)
        if n == 0:
            self._draw_text_story(story)
        elif n == 1:
            self._draw_image_story(story)
        else:
            self._draw_multi_image_story(story)
        self._first_story_done = True

    def _draw_image_story(self, story: Story):
        pil_img = fetch_image(story.image_url)
        if pil_img is not None:
            img_w, img_h = pil_img.size
            is_landscape = img_w / img_h > 1.33
        else:
            is_landscape = False

        if is_landscape:
            # Landscape: always inline regardless of page parity
            self._draw_inline_image_story(story, pil_img)
            return

        # Portrait: image must land on left (even) page
        would_create_blank = self.page_num % 2 == 0
        if would_create_blank:
            if self._is_long_text(story):
                # 3-page sandwich: text opener (right) → image (left) → continuation (right)
                self._draw_3page_portrait_story(story, pil_img)
            else:
                # Short text: standard filler + image-left spread
                self._draw_filler_page()
                self._draw_spread_image_story(story, pil_img)
        else:
            self._draw_spread_image_story(story, pil_img)

    def _draw_spread_image_story(self, story: Story, prefetched_img: Optional[Image.Image] = None):
        """Original spread layout: image on left page, text on right page."""
        self._new_page(count_as_logical=True)
        self._draw_image_page(story, prefetched_img=prefetched_img)

        self._new_page(count_as_logical=True)
        y_cursor = self._draw_opener_block(story)
        y_cursor = self._draw_body_text(story.body, y_cursor)
        self._draw_page_number()

    def _draw_3page_portrait_story(self, story: Story, prefetched_img: Optional[Image.Image] = None):
        """Sandwich layout for long-text portrait stories when image-left would need a filler.
        Page N (odd/right): opener + first page of body text
        Page N+1 (even/left): portrait image
        Page N+2+ (odd/right ...): remaining body text continuation (only if text is left)
        """
        self._new_page(count_as_logical=True)          # page N (odd — right side)
        y_cursor = self._draw_opener_block(story)
        remaining, y_cursor = self._draw_body_text_partial(story.body, y_cursor)
        self._draw_page_number()

        self._new_page(count_as_logical=True)          # page N+1 (even — left side, image)
        self._draw_image_page(story, prefetched_img=prefetched_img)

        if remaining:
            self._new_page(count_as_logical=True)      # page N+2 (odd — right side, continuation)
            box = self._get_content_box()
            self._draw_body_text(remaining, box["top"])
            self._draw_page_number()


    # ── Multi-photo layout ────────────────────────────────────────────

    def _draw_multi_image_story(self, story: Story):
        """Handle stories with 2 or 3 photos."""
        images = [fetch_image(url) for url in story.image_urls]
        images = [img for img in images if img is not None]

        if len(images) == 0:
            self._draw_text_story(story)
            return
        if len(images) == 1:
            self._draw_image_story(story)
            return

        def is_landscape(img): return img.size[0] / img.size[1] > 1.33
        landscape = [img for img in images if is_landscape(img)]
        others    = [img for img in images if not is_landscape(img)]

        # Exactly 1 landscape + at least 1 other: landscape goes inline on the
        # text page (mirrors the existing single-landscape inline behaviour);
        # the remaining portrait/square images form a collage on the left page.
        if len(landscape) == 1 and len(others) >= 1:
            self._draw_landscape_inline_with_collage(story, landscape[0], others)
            return

        # 3 photos with long text → split [photo 1] / [photos 2+3]
        if len(images) == 3 and self._is_long_text(story):
            self._draw_3photo_split_story(story, images)
        else:
            self._draw_collage_spread_story(story, images)

    def _draw_collage_spread_story(self, story: Story, images: list):
        """All photos as a collage on left page, text on right page (same spread)."""
        if self.page_num % 2 == 0:
            # Next page would be odd (right). Need even (left) for the collage.
            if self._is_long_text(story):
                self._draw_collage_sandwich(story, images)
            else:
                self._draw_filler_page()
                self._draw_collage_and_text(story, images)
        else:
            self._draw_collage_and_text(story, images)

    def _draw_collage_and_text(self, story: Story, images: list):
        """Collage on even/left page, opener+text on odd/right page."""
        self._new_page(count_as_logical=True)   # even (left) — collage
        self._draw_photo_collage(images)

        self._new_page(count_as_logical=True)   # odd (right) — text
        y_cursor = self._draw_opener_block(story)
        self._draw_body_text(story.body, y_cursor)
        self._draw_page_number()

    def _draw_landscape_inline_with_collage(self, story: Story,
                                            landscape_img: Image.Image,
                                            other_imgs: list):
        """Portrait/square images as collage on left page; landscape image inline
        on the text page alongside QR, title and body — mirrors the existing
        single-landscape inline behaviour for multi-photo stories."""
        # Ensure collage lands on even (left) page
        if self.page_num % 2 == 0:
            self._draw_filler_page()

        self._new_page(count_as_logical=True)   # even (left) — collage of non-landscape
        self._draw_photo_collage(other_imgs)

        self._new_page(count_as_logical=True)   # odd (right) — opener + landscape inline + text
        y_cursor = self._draw_opener_block(story)

        # Draw the landscape image inline (full content width, capped at 55% of content height)
        box = self._get_content_box()
        img_w, img_h = landscape_img.size
        draw_w = box["width"]
        draw_h = img_h * (draw_w / img_w)
        max_h = box["height"] * 0.55
        if draw_h > max_h:
            draw_h = max_h
            draw_w = img_w * (draw_h / img_h)

        if y_cursor - draw_h < box["bottom"]:
            self._draw_page_number()
            self._new_page(count_as_logical=True)
            box = self._get_content_box()
            y_cursor = box["top"]

        x = box["left"] + (box["width"] - draw_w) / 2
        y = y_cursor - draw_h

        if self.image_border_width > 0:
            bp = self.image_border_padding
            self.c.setStrokeColorRGB(*self.image_border_color)
            self.c.setLineWidth(self.image_border_width)
            self.c.rect(x - bp, y - bp, draw_w + bp * 2, draw_h + bp * 2, stroke=1, fill=0)

        img_buf = pil_image_to_reportlab(landscape_img)
        self.c.drawImage(ImageReader(img_buf), x, y, draw_w, draw_h, preserveAspectRatio=True)

        y_cursor = y - self.story_top_spacing
        self._draw_body_text(story.body, y_cursor)
        self._draw_page_number()

    def _draw_collage_sandwich(self, story: Story, images: list):
        """Text opener on odd/right → collage on even/left → continuation on odd/right."""
        self._new_page(count_as_logical=True)   # odd (right) — opener + partial text
        y_cursor = self._draw_opener_block(story)
        remaining, _ = self._draw_body_text_partial(story.body, y_cursor)
        self._draw_page_number()

        self._new_page(count_as_logical=True)   # even (left) — collage
        self._draw_photo_collage(images)

        if remaining:
            self._new_page(count_as_logical=True)   # odd (right) — continuation
            box = self._get_content_box()
            self._draw_body_text(remaining, box["top"])
            self._draw_page_number()

    def _draw_3photo_split_story(self, story: Story, images: list):
        """Split: photo 1 on left spread 1, photos 2+3 on left spread 2.
        Constraint: each collage page pairs only with this story's text."""
        group_a = [images[0]]
        group_b = images[1:]

        # Ensure collage A lands on even (left) page
        if self.page_num % 2 == 0:
            self._draw_filler_page()

        self._new_page(count_as_logical=True)   # even (left) — photo 1
        self._draw_photo_collage(group_a)

        self._new_page(count_as_logical=True)   # odd (right) — opener + text part 1
        y_cursor = self._draw_opener_block(story)
        remaining, _ = self._draw_body_text_partial(story.body, y_cursor)
        self._draw_page_number()

        # After even+odd pair, page_num is odd → next is even (left). No filler needed.
        self._new_page(count_as_logical=True)   # even (left) — photos 2+3
        self._draw_photo_collage(group_b)

        if remaining:
            self._new_page(count_as_logical=True)   # odd (right) — continuation
            box = self._get_content_box()
            self._draw_body_text(remaining, box["top"])
            self._draw_page_number()

    def _plan_collage(self, images: list) -> tuple[str, list]:
        """Choose layout template and reorder images for best visual fit.
        Templates:
          '1-single'      — single image centred
          '2-vstack'      — side by side (A left | B right)
          '2-hstack'      — stacked (A top / B bottom)
          '3-hstack'      — all 3 stacked vertically (top / mid / bottom)
          '3-left-tall'   — A left tall, B top-right, C bottom-right
          '3-top-spread'  — A top spanning, B bottom-left, C bottom-right
        Selection maximises the minimum image dimension across the collage.
        """
        def aspect(img): return img.size[0] / img.size[1]

        n = len(images)
        if n == 1:
            return '1-single', images
        if n == 2:
            r0, r1 = aspect(images[0]), aspect(images[1])
            # hstack when any image is landscape, OR when both are square-ish
            # (product > 0.5 means neither is tall-portrait; hstack gives ~50% bigger images)
            if r0 > 1.33 or r1 > 1.33 or r0 * r1 > 0.5:
                return '2-hstack', images
            return '2-vstack', sorted(images, key=aspect)   # both tall-portrait → side by side
        # n == 3: sort ascending (most portrait first)
        ranked = sorted(images, key=aspect)
        n_landscape = sum(1 for img in images if aspect(img) > 1.33)
        min_ratio = aspect(ranked[0])  # most portrait image's ratio

        if n_landscape == 3:
            # All landscape → stacking vertically gives each image ~2× more height
            # than 3-top-spread (which makes the bottom two tiny)
            return '3-hstack', list(reversed(ranked))   # widest on top

        if n_landscape >= 1:
            # Any landscape image goes on top spanning full width;
            # remaining images fill the bottom row at their natural heights.
            # This beats 3-left-tall for 1L+2P by up to 2.4×.
            return '3-top-spread', list(reversed(ranked))

        # 0 landscape: all portrait / square
        if min_ratio > 0.75:
            # Square-ish images → stacking gives 50% more height than 3-left-tall
            return '3-hstack', list(reversed(ranked))

        # Very tall portraits (9:16 etc.) — 3-left-tall keeps the left portrait
        # at nearly full-page height, which beats stacking
        return '3-left-tall', ranked

    def _compute_collage_layout(self, images: list, template: str,
                                x0: float, y0: float, W: float, H: float
                                ) -> tuple[list, list]:
        """Return (positions, sep_lines).
        positions — [(x, y, w, h) ...] one per image (ReportLab bottom-left origin).
        sep_lines — [(x1, y1, x2, y2) ...] thin divider lines between images.
        For 2-hstack / 2-vstack images are sized adaptively (no letterbox within the group).
        For 3-slot templates images are fit-within-slot with letterbox, but share one border.
        """
        SEP = 1.0  # points — thin gap / divider line between images

        def ratio(img):
            return img.size[0] / img.size[1]

        def fit_in_slot(img, sw, sh):
            """Fit image inside slot (sw×sh), centred. Returns offset (ox,oy) and size (dw,dh)."""
            iw, ih = img.size
            scale = min(sw / iw, sh / ih)
            dw, dh = iw * scale, ih * scale
            return (sw - dw) / 2, (sh - dh) / 2, dw, dh

        if template == '1-single':
            ox, oy, dw, dh = fit_in_slot(images[0], W, H)
            return [(x0 + ox, y0 + oy, dw, dh)], []

        if template == '2-hstack':
            r0, r1 = ratio(images[0]), ratio(images[1])
            # Each image fills the full width; height is determined by ratio.
            h0 = W / r0
            h1 = W / r1
            total_h = h0 + SEP + h1
            if total_h > H:
                # Solve: w/r0 + SEP + w/r1 = H  →  w = (H-SEP)/(1/r0+1/r1)
                w = (H - SEP) / (1 / r0 + 1 / r1)
                h0, h1 = w / r0, w / r1
                total_h = h0 + SEP + h1
            else:
                w = W
            cx = x0 + (W - w) / 2
            cy = y0 + (H - total_h) / 2  # centre group vertically
            pos = [
                (cx, cy + h1 + SEP, w, h0),   # top image
                (cx, cy, w, h1),               # bottom image
            ]
            sep_y = cy + h1 + SEP / 2
            sep_lines = [(cx, sep_y, cx + w, sep_y)]
            return pos, sep_lines

        if template == '2-vstack':
            r0, r1 = ratio(images[0]), ratio(images[1])
            # Each image fills the full height; width is determined by ratio.
            w0 = H * r0
            w1 = H * r1
            total_w = w0 + SEP + w1
            if total_w > W:
                # Solve: h*r0 + SEP + h*r1 = W  →  h = (W-SEP)/(r0+r1)
                h = (W - SEP) / (r0 + r1)
                w0, w1 = h * r0, h * r1
                total_w = w0 + SEP + w1
            else:
                h = H
            cy = y0 + (H - h) / 2
            cx = x0 + (W - total_w) / 2  # centre group horizontally
            pos = [
                (cx, cy, w0, h),                # left image
                (cx + w0 + SEP, cy, w1, h),     # right image
            ]
            sep_x = cx + w0 + SEP / 2
            sep_lines = [(sep_x, cy, sep_x, cy + h)]
            return pos, sep_lines

        if template == '3-hstack':
            r0, r1, r2 = ratio(images[0]), ratio(images[1]), ratio(images[2])
            # Each image fills the full width, heights determined by ratio
            h0 = W / r0
            h1 = W / r1
            h2 = W / r2
            total_h = h0 + SEP + h1 + SEP + h2
            if total_h > H:
                # Scale: w*(1/r0+1/r1+1/r2) + 2*SEP = H
                w = (H - 2 * SEP) / (1 / r0 + 1 / r1 + 1 / r2)
                h0, h1, h2 = w / r0, w / r1, w / r2
                total_h = h0 + SEP + h1 + SEP + h2
            else:
                w = W
            cx = x0 + (W - w) / 2
            cy = y0 + (H - total_h) / 2
            pos = [
                (cx, cy + h2 + SEP + h1 + SEP, w, h0),  # top
                (cx, cy + h2 + SEP, w, h1),              # middle
                (cx, cy, w, h2),                          # bottom
            ]
            sep_lines = [
                (cx, cy + h2 + SEP / 2, cx + w, cy + h2 + SEP / 2),
                (cx, cy + h2 + SEP + h1 + SEP / 2, cx + w, cy + h2 + SEP + h1 + SEP / 2),
            ]
            return pos, sep_lines

        # ── 3-slot templates: solve for a perfect outer rectangle, no letterbox ──
        #
        # 3-left-tall: solve h so that left_w = h*r0 and right pair fills h exactly.
        #   Constraint: left_w + SEP + right_w = W  and  right_w*(1/r1+1/r2)+SEP = h
        #   → h = ((W-SEP)*(1/r1+1/r2) + SEP) / (1 + r0*(1/r1+1/r2))
        #
        # 3-top-spread: bottom pair fills W exactly, top image fills W at natural ratio.
        #   h_bot = (W-SEP)/(r1+r2),  h_top = W/r0
        #   → collage h = h_top + SEP + h_bot

        if template == '3-top-spread':
            r0, r1, r2 = ratio(images[0]), ratio(images[1]), ratio(images[2])
            h_top = W / r0           # top image fills full width
            h_bot = (W - SEP) / (r1 + r2)   # bottom pair fills full width
            w1 = h_bot * r1
            w2 = h_bot * r2
            h = h_top + SEP + h_bot

            if h > H:
                # Scale the whole group to fit content height
                s = H / h
                h_top *= s; h_bot *= s; w1 *= s; w2 *= s
                h = H

            # Group may be narrower than W after scaling (w1+SEP+w2 ≈ W*s)
            w_group = w1 + SEP + w2
            w_top = h_top * r0   # natural width of top image at scaled height
            cx = x0 + (W - max(w_top, w_group)) / 2   # centre group horizontally
            cy = y0 + (H - h) / 2

            top_y = cy + h_bot + SEP
            pos = [
                (cx, top_y, w_top, h_top),              # top spanning
                (cx, cy, w1, h_bot),                    # bottom left
                (cx + w1 + SEP, cy, w2, h_bot),         # bottom right
            ]
            sep_lines = [
                (cx, top_y - SEP / 2, cx + w_top, top_y - SEP / 2),
                (cx + w1 + SEP / 2, cy, cx + w1 + SEP / 2, top_y),
            ]
            return pos, sep_lines

        # '3-left-tall'
        r0, r1, r2 = ratio(images[0]), ratio(images[1]), ratio(images[2])
        A = 1 / r1 + 1 / r2
        h = ((W - SEP) * A + SEP) / (1 + r0 * A)
        left_w = h * r0
        right_w = W - SEP - left_w

        if h > H:
            s = H / h
            h = H
            left_w *= s
            right_w *= s

        h1 = right_w / r1   # right top
        h2 = right_w / r2   # right bottom
        cy = y0 + (H - h) / 2
        right_x = x0 + left_w + SEP

        pos = [
            (x0, cy, left_w, h),                          # left: fills full height
            (right_x, cy + h2 + SEP, right_w, h1),       # right top
            (right_x, cy, right_w, h2),                   # right bottom
        ]
        sep_lines = [
            (x0 + left_w + SEP / 2, cy, x0 + left_w + SEP / 2, cy + h),
            (right_x, cy + h2 + SEP / 2, right_x + right_w, cy + h2 + SEP / 2),
        ]
        return pos, sep_lines

    def _draw_photo_collage(self, images: list):
        """Draw a collage of 1–3 images on the current page.
        One shared border around the entire group; thin separator lines between images."""
        if not images:
            return
        template, ordered = self._plan_collage(images)
        box = self._get_content_box()
        bp = self.image_border_padding

        positions, sep_lines = self._compute_collage_layout(
            ordered, template,
            box["left"] + bp, box["bottom"] + bp,
            box["width"] - bp * 2, box["height"] - bp * 2,
        )

        # Bounding box of all image positions
        gx = min(p[0] for p in positions)
        gy = min(p[1] for p in positions)
        gw = max(p[0] + p[2] for p in positions) - gx
        gh = max(p[1] + p[3] for p in positions) - gy

        # Single outer border + separators (skipped when border width is 0)
        if self.image_border_width > 0:
            self.c.setStrokeColorRGB(*self.image_border_color)
            self.c.setLineWidth(self.image_border_width)
            self.c.rect(gx - bp, gy - bp, gw + bp * 2, gh + bp * 2, stroke=1, fill=0)
            for x1, y1, x2, y2 in sep_lines:
                self.c.line(x1, y1, x2, y2)

        # Draw each image (no individual borders)
        for pil_img, (x, y, w, h) in zip(ordered, positions):
            if pil_img is None:
                continue
            img_buf = pil_image_to_reportlab(pil_img)
            self.c.drawImage(ImageReader(img_buf), x, y, w, h, preserveAspectRatio=True)

    def _draw_inline_image_story(self, story: Story, pil_img: Optional[Image.Image] = None):
        """Inline layout: QR, title, date, image, then text in a single flow."""
        self._new_page(count_as_logical=True)
        y_cursor = self._draw_opener_block(story)

        # Draw the inline image
        if pil_img is None:
            pil_img = fetch_image(story.image_url)

        if pil_img is not None:
            box = self._get_content_box()
            img_w, img_h = pil_img.size

            # Fit image to content width, same margins as text
            draw_w = box["width"]
            scale = draw_w / img_w
            draw_h = img_h * scale

            # Cap height so image doesn't take more than 60% of content area
            max_h = box["height"] * 0.6
            if draw_h > max_h:
                draw_h = max_h
                scale = draw_h / img_h
                draw_w = img_w * scale

            # Check if image fits on current page, otherwise overflow to next
            if y_cursor - draw_h - self.image_border_padding * 2 < box["bottom"]:
                self._draw_page_number()
                self._new_page(count_as_logical=True)
                box = self._get_content_box()
                y_cursor = box["top"]

            x = box["left"] + (box["width"] - draw_w) / 2
            y = y_cursor - draw_h - self.image_border_padding

            # Draw border
            self.c.setStrokeColorRGB(*self.image_border_color)
            self.c.setLineWidth(self.image_border_width)
            self.c.rect(
                x - self.image_border_padding,
                y - self.image_border_padding,
                draw_w + self.image_border_padding * 2,
                draw_h + self.image_border_padding * 2,
                stroke=1, fill=0
            )

            # Draw image
            img_buf = pil_image_to_reportlab(pil_img)
            img_reader = ImageReader(img_buf)
            self.c.drawImage(img_reader, x, y, draw_w, draw_h, preserveAspectRatio=True)

            y_cursor = y - self.image_border_padding - self.story_top_spacing
        else:
            # Image failed to load, just continue with text
            pass

        # Draw body text continuing from below the image
        y_cursor = self._draw_body_text(story.body, y_cursor)
        self._draw_page_number()

    def _draw_text_story(self, story: Story):
        if not self._first_story_done and self.page_num % 2 == 1:
            self._new_page(count_as_logical=True)   # first story only: skip to right (odd) page
        self._new_page(count_as_logical=True)
        y_cursor = self._draw_opener_block(story)
        y_cursor = self._draw_body_text(story.body, y_cursor)
        self._draw_page_number()

    def _draw_filler_page(self):
        """Draw a filler page with centered logo when a blank would otherwise occur."""
        self._new_page(count_as_logical=True)
        box = self._get_content_box()

        if os.path.exists(self._logo_path):
            logo_size = min(box["width"], box["height"]) * 0.3
            lx = box["left"] + (box["width"] - logo_size) / 2
            ly = box["bottom"] + (box["height"] - logo_size) / 2
            draw_svg_logo_vector(self.c, self._logo_path, lx, ly, logo_size, self.style.logo_color)

    def _is_long_text(self, story: Story) -> bool:
        """Return True if story body text overflows the opener page (3-page layout beneficial)."""
        box = self._get_content_box()
        # Estimate vertical space consumed by the opener block
        num_title_lines = max(1, len(story.title) // 30 + 1)  # rough: ~30 chars per title line
        opener_h = (
            self.qr_top_spacing
            + self.qr_code_size
            + self.title_spacing
            + self.title_font_size * 1.3 * num_title_lines
            + (self.contributor_spacing + self.contributor_font_size * 1.3 if story.contributor else 0)
            + (self.contributor_font_size * 1.1 if story.contributor and story.relation else 0)
            + (self.date_spacing + self.date_font_size * 1.3 if story.recorded_at else 0)
            + self.divider_spacing
            + self.story_top_spacing
        )
        available = box["height"] - opener_h
        if available <= 0:
            return True
        lines = wrap_text(story.body, box["width"], self.c, self.font_serif_regular, self.body_font_size)
        total_h = sum(
            self.line_height * 0.6 if not line else self.line_height
            for line, _ in lines
        )
        return total_h > available

    def _draw_body_text_partial(self, body: str, start_y: float) -> tuple[str, float]:
        """Render body text on the current page only, filling as many lines as fit.
        Stops at the first line that won't fit (line-level granularity, not paragraph-level).
        Returns (remaining_text, y_cursor). remaining_text is '' if all text fit."""
        box = self._get_content_box()
        self.c.setFont(self.font_serif_regular, self.body_font_size)
        self.c.setFillColorRGB(*self.body_text_color)
        y = start_y
        paragraphs = body.split('\n')

        for para_idx, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                next_y = y - self.line_height * 0.6
                if next_y < box["bottom"]:
                    return '\n'.join(paragraphs[para_idx:]), y
                y = next_y
                continue

            lines = wrap_text(paragraph, box["width"], self.c, self.font_serif_regular, self.body_font_size)

            for j, (line, is_last) in enumerate(lines):
                if y - self.line_height < box["bottom"]:
                    # Can't fit this line — reconstruct remaining text from here
                    remaining_para = ' '.join(ln for ln, _ in lines[j:])
                    remaining = '\n'.join([remaining_para] + paragraphs[para_idx + 1:])
                    return remaining, y

                space_count = line.count(' ')
                if not is_last and space_count > 0:
                    text_width = self.c.stringWidth(line, self.font_serif_regular, self.body_font_size)
                    extra_space = box["width"] - text_width
                    word_spacing = extra_space / space_count
                    t = self.c.beginText(box["left"], y)
                    t.setFont(self.font_serif_regular, self.body_font_size)
                    t.setWordSpace(word_spacing)
                    t.textLine(line)
                    self.c.drawText(t)
                else:
                    t = self.c.beginText(box["left"], y)
                    t.setFont(self.font_serif_regular, self.body_font_size)
                    t.setWordSpace(0)
                    t.textLine(line)
                    self.c.drawText(t)
                y -= self.line_height

            if para_idx < len(paragraphs) - 1:
                y -= self.paragraph_spacing

        return '', y

    def _draw_transition_page(self):
        HEADING = "Hekayə hələ davam edir…"
        BODY = (
            "Bu səhifələr hələ yaşanacaq günlər, hələ danışılacaq sözlər "
            "və hələ yazılacaq xatirələr üçündür.\n"
            "Qələmini götür və həyatın sənə bəxş etdiyi yeni anları buraya əlavə et.\n"
            "Çünki yazılan hər xatirə gələcəyə qalan bir mirasdır."
        )

        heading_size = 16
        body_size = 12
        heading_line_h = heading_size * 1.4
        body_line_h = body_size * 1.6
        gap = 20

        self._new_page(count_as_logical=True)
        box = self._get_content_box()
        center_x = box["left"] + box["width"] / 2

        body_lines = wrap_text(BODY, box["width"], self.c, self.font_serif_italic, body_size)
        total_height = heading_line_h + gap + len(body_lines) * body_line_h
        y = box["bottom"] + box["height"] / 2 + total_height / 2

        self.c.setFont(self.font_serif_italic, heading_size)
        self.c.setFillColorRGB(0.35, 0.35, 0.35)
        self.c.drawCentredString(center_x, y, HEADING)
        y -= heading_line_h + gap

        self.c.setFont(self.font_serif_italic, body_size)
        self.c.setFillColorRGB(0.5, 0.5, 0.5)
        for line_text, _ in body_lines:
            self.c.drawCentredString(center_x, y, line_text)
            y -= body_line_h

        self.c.setFillColorRGB(0, 0, 0)
        self._draw_page_number()

    def _draw_image_page(self, story: Story, prefetched_img: Optional[Image.Image] = None):
        box = self._get_content_box()
        pil_img = prefetched_img if prefetched_img is not None else fetch_image(story.image_url)

        if pil_img is None:
            self.c.setFont(FONT_SANS_REGULAR, 12)
            self.c.setFillColorRGB(0.5, 0.5, 0.5)
            self.c.drawCentredString(
                box["left"] + box["width"] / 2,
                box["top"] - box["height"] / 2,
                "Image could not be loaded"
            )
            self.c.setFillColorRGB(0, 0, 0)
            return

        img_w, img_h = pil_img.size

        img_buf = pil_image_to_reportlab(pil_img)
        img_reader = ImageReader(img_buf)

        if should_draw_full_page_image(img_w, img_h, self.page_width, self.page_height):
            effective_margin = self.full_page_image_margin + self.image_border_padding
            x, y, draw_w, draw_h = get_full_page_image_rect(
                img_w, img_h, self.page_width, self.page_height, effective_margin,
            )
            self.c.setStrokeColorRGB(*self.image_border_color)
            self.c.setLineWidth(self.image_border_width)
            self.c.rect(
                x - self.image_border_padding,
                y - self.image_border_padding,
                draw_w + self.image_border_padding * 2,
                draw_h + self.image_border_padding * 2,
                stroke=1, fill=0,
            )
            self.c.drawImage(img_reader, x, y, draw_w, draw_h, preserveAspectRatio=True)
            return

        max_w = box["width"] - self.image_border_padding * 2
        max_h = box["height"] - self.image_border_padding * 2

        scale = min(max_w / img_w, max_h / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale

        x = box["left"] + (box["width"] - draw_w) / 2
        y = box["bottom"] + (box["height"] - draw_h) / 2

        self.c.setStrokeColorRGB(*self.image_border_color)
        self.c.setLineWidth(self.image_border_width)
        self.c.rect(
            x - self.image_border_padding,
            y - self.image_border_padding,
            draw_w + self.image_border_padding * 2,
            draw_h + self.image_border_padding * 2,
            stroke=1, fill=0
        )

        self.c.drawImage(img_reader, x, y, draw_w, draw_h, preserveAspectRatio=True)

    def _draw_opener_block(self, story: Story) -> float:
        box = self._get_content_box()
        center_x = box["left"] + box["width"] / 2
        y = box["top"] - self.qr_top_spacing

        qr_x = center_x - self.qr_code_size / 2
        y -= self.qr_code_size
        draw_qr_vector(
            self.c,
            story.qr_target_url,
            qr_x,
            y,
            self.qr_code_size,
            qr_color=self.style.qr_color,
            logo_path=self._logo_path if self.style.qr_logo_enabled else None,
            logo_color=self.style.logo_color,
        )

        y -= self.title_spacing

        self.c.setFont(self.font_serif_bold, self.title_font_size)
        self.c.setFillColorRGB(*self.body_text_color)
        title_lines = []
        words = story.title.split()
        current = words[0] if words else ""
        for word in words[1:]:
            test = current + " " + word
            if self.c.stringWidth(test, self.font_serif_bold, self.title_font_size) <= box["width"]:
                current = test
            else:
                title_lines.append(current)
                current = word
        if current:
            title_lines.append(current)

        for line in title_lines:
            y -= self.title_font_size * 1.3
            self.c.drawCentredString(center_x, y, line)

        if story.contributor:
            y -= self.contributor_spacing
            self.c.setFont(self.font_serif_italic, self.contributor_font_size)
            self.c.setFillColorRGB(*self.contributor_color)
            y -= self.contributor_font_size * 1.3
            self.c.drawCentredString(center_x, y, story.contributor)
            if story.relation:
                y -= self.contributor_font_size * 1.1
                self.c.setFont(self.font_serif_italic, self.contributor_font_size - 1)
                self.c.drawCentredString(center_x, y, story.relation)
            self.c.setFillColorRGB(*self.body_text_color)

        if story.recorded_at:
            y -= self.date_spacing

            formatted_date = format_date_az(story.recorded_at)
            self.c.setFont(FONT_SANS_REGULAR, self.date_font_size)
            self.c.setFillColorRGB(*self.date_color)
            y -= self.date_font_size * 1.3
            self.c.drawCentredString(center_x, y, formatted_date)
            self.c.setFillColorRGB(*self.body_text_color)

        y -= self.divider_spacing

        divider_width = min(box["width"] * 0.4, 200)
        draw_divider(
            self.c, center_x, y, divider_width,
            self.divider_color, self.divider_line_width,
            self.divider_style,
        )

        y -= self.story_top_spacing

        return y

    def _draw_body_text(self, body: str, start_y: float) -> float:
        box = self._get_content_box()
        lines = wrap_text(body, box["width"], self.c, self.font_serif_regular, self.body_font_size)
        self.c.setFont(self.font_serif_regular, self.body_font_size)
        self.c.setFillColorRGB(*self.body_text_color)

        y = start_y
        line_idx = 0

        while line_idx < len(lines):
            line_data = lines[line_idx]
            if isinstance(line_data, tuple):
                line, is_last_line = line_data
            else:
                line = line_data
                is_last_line = (line_idx == len(lines) - 1) or (lines[line_idx + 1] == "")

            if y - self.line_height < box["bottom"]:
                self._draw_page_number()
                self._new_page(count_as_logical=True)
                box = self._get_content_box()
                y = box["top"]
                self.c.setFont(self.font_serif_regular, self.body_font_size)
                self.c.setFillColorRGB(*self.body_text_color)

            if line == "":
                y -= self.line_height * 0.6
            else:
                space_count = line.count(' ')
                
                if not is_last_line and space_count > 0:
                    text_width = self.c.stringWidth(line, self.font_serif_regular, self.body_font_size)
                    extra_space = box["width"] - text_width
                    word_spacing = extra_space / space_count
                    
                    t = self.c.beginText(box["left"], y)
                    t.setFont(self.font_serif_regular, self.body_font_size)
                    t.setWordSpace(word_spacing)
                    t.textLine(line)
                    self.c.drawText(t)
                else:
                    t = self.c.beginText(box["left"], y)
                    t.setFont(self.font_serif_regular, self.body_font_size)
                    t.setWordSpace(0)
                    t.textLine(line)
                    self.c.drawText(t)
                    
                y -= self.line_height
                if is_last_line and line_idx < len(lines) - 1:
                    y -= self.paragraph_spacing

            line_idx += 1

        return y


def generate_pdf(request: BookRequest) -> tuple[bytes, int]:
    generator = MemonaPDFGenerator(request)
    return generator.generate()
