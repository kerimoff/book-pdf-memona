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


class SimurqPDFGenerator:
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
        self._draw_simurq_splash_page()
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
                and story.image_url
                and self.page_num % 2 == 0
            ):
                limit = self.style.allow_reorder_count or len(stories)
                for j in range(i + 1, min(i + 1 + limit, len(stories))):
                    if j not in rendered and not stories[j].image_url:
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

    def _draw_simurq_splash_page(self):
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
        has_image = story.image_url is not None and story.image_url.strip() != ""

        if has_image:
            self._draw_image_story(story)
        else:
            self._draw_text_story(story)
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
    generator = SimurqPDFGenerator(request)
    return generator.generate()
