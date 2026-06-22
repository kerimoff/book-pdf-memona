"""Divider drawing functions for PDF generation.

Each function draws a decorative divider centered at (center_x, y)
spanning a given width, using only ReportLab canvas primitives.
"""
import math
from reportlab.pdfgen.canvas import Canvas
from api.models import DividerStyle


def draw_divider(c: Canvas, center_x: float, y: float, width: float,
                 color: tuple, line_width: float, style: DividerStyle) -> None:
    _DRAW_FUNCTIONS[style](c, center_x, y, width, color, line_width)


def _draw_simple_line(c: Canvas, center_x: float, y: float, width: float,
                      color: tuple, line_width: float) -> None:
    c.saveState()
    c.setStrokeColorRGB(*color)
    c.setLineWidth(line_width)
    c.line(center_x - width / 2, y, center_x + width / 2, y)
    c.restoreState()


def _draw_graduated_dots(c: Canvas, center_x: float, y: float, width: float,
                         color: tuple, line_width: float) -> None:
    c.saveState()
    c.setFillColorRGB(*color)
    c.setStrokeColorRGB(*color)

    dot_count = 15
    max_radius = 3.0
    min_radius = 0.8
    spacing = width / (dot_count - 1)

    for i in range(dot_count):
        # Normalized position: 0 at edges, 1 at center
        t = 1 - abs(2 * i / (dot_count - 1) - 1)
        radius = min_radius + (max_radius - min_radius) * (t ** 1.2)
        cx = center_x - width / 2 + i * spacing
        c.circle(cx, y, radius, fill=1, stroke=0)

    c.restoreState()


def _draw_ornamental_floral(c: Canvas, center_x: float, y: float, width: float,
                            color: tuple, line_width: float) -> None:
    c.saveState()
    c.setStrokeColorRGB(*color)
    c.setFillColorRGB(*color)
    c.setLineWidth(line_width)

    # Central diamond
    ds = 4.0  # diamond half-size
    p = c.beginPath()
    p.moveTo(center_x, y + ds)       # top
    p.lineTo(center_x + ds, y)       # right
    p.lineTo(center_x, y - ds)       # bottom
    p.lineTo(center_x - ds, y)       # left
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    # Horizontal petals only (left and right) to keep vertical height compact
    petal_len = 7.0
    petal_width = 3.0
    for side in [-1, 1]:
        sx = center_x + side * (ds + 1)
        ex = center_x + side * (ds + 1 + petal_len)
        # Perpendicular direction is vertical for horizontal petals
        pp = c.beginPath()
        pp.moveTo(sx, y)
        pp.curveTo(sx + side * petal_len * 0.4, y + petal_width,
                   sx + side * petal_len * 0.7, y + petal_width * 0.5,
                   ex, y)
        pp.curveTo(sx + side * petal_len * 0.7, y - petal_width * 0.5,
                   sx + side * petal_len * 0.4, y - petal_width,
                   sx, y)
        pp.close()
        c.drawPath(pp, fill=1, stroke=0)

    # Small vertical accents (tiny diamonds above and below center)
    accent_size = 2.0
    for vert in [-1, 1]:
        ap = c.beginPath()
        ay = y + vert * (ds + 2)
        ap.moveTo(center_x, ay + vert * accent_size)
        ap.lineTo(center_x + accent_size * 0.6, ay)
        ap.lineTo(center_x, ay - vert * accent_size)
        ap.lineTo(center_x - accent_size * 0.6, ay)
        ap.close()
        c.drawPath(ap, fill=1, stroke=0)

    # Small dots flanking the ornament
    dot_offset = ds + petal_len + 5
    dot_r = 1.2
    for side in [-1, 1]:
        c.circle(center_x + side * dot_offset, y, dot_r, fill=1, stroke=0)

    # Short lines extending outward from the dots
    line_start = dot_offset + dot_r + 3
    line_end = width / 2
    if line_end > line_start:
        for side in [-1, 1]:
            c.line(center_x + side * line_start, y,
                   center_x + side * line_end, y)

    c.restoreState()


def _draw_line_with_heart(c: Canvas, center_x: float, y: float, width: float,
                          color: tuple, line_width: float) -> None:
    c.saveState()
    c.setStrokeColorRGB(*color)
    c.setFillColorRGB(*color)
    c.setLineWidth(line_width)

    half_w = width / 2
    endpoint_r = 1.8
    heart_size = 6.0
    gap = heart_size + 2

    # Left line segment (from left endpoint circle to gap before heart)
    c.line(center_x - half_w + endpoint_r, y,
           center_x - gap, y)
    # Right line segment (from gap after heart to right endpoint circle)
    c.line(center_x + gap, y,
           center_x + half_w - endpoint_r, y)

    # Endpoint circles
    c.circle(center_x - half_w, y, endpoint_r, fill=1, stroke=0)
    c.circle(center_x + half_w, y, endpoint_r, fill=1, stroke=0)

    # Heart shape at center
    hs = heart_size
    p = c.beginPath()
    # Bottom point of heart
    p.moveTo(center_x, y - hs * 0.8)
    # Left lobe
    p.curveTo(center_x - hs * 0.8, y - hs * 0.2,
              center_x - hs, y + hs * 0.4,
              center_x - hs * 0.5, y + hs * 0.7)
    # Top center dip
    p.curveTo(center_x - hs * 0.2, y + hs * 0.9,
              center_x, y + hs * 0.6,
              center_x, y + hs * 0.5)
    # Right lobe (mirror)
    p.curveTo(center_x, y + hs * 0.6,
              center_x + hs * 0.2, y + hs * 0.9,
              center_x + hs * 0.5, y + hs * 0.7)
    p.curveTo(center_x + hs, y + hs * 0.4,
              center_x + hs * 0.8, y - hs * 0.2,
              center_x, y - hs * 0.8)
    p.close()
    c.drawPath(p, fill=0, stroke=1)

    c.restoreState()


def _draw_line_with_diamond(c: Canvas, center_x: float, y: float, width: float,
                            color: tuple, line_width: float) -> None:
    c.saveState()
    c.setStrokeColorRGB(*color)
    c.setFillColorRGB(*color)
    c.setLineWidth(line_width)

    half_w = width / 2
    endpoint_r = 1.8
    diamond_size = 4.0
    gap = diamond_size + 2

    # Left line segment
    c.line(center_x - half_w + endpoint_r, y,
           center_x - gap, y)
    # Right line segment
    c.line(center_x + gap, y,
           center_x + half_w - endpoint_r, y)

    # Endpoint circles
    c.circle(center_x - half_w, y, endpoint_r, fill=1, stroke=0)
    c.circle(center_x + half_w, y, endpoint_r, fill=1, stroke=0)

    # Diamond at center
    ds = diamond_size
    p = c.beginPath()
    p.moveTo(center_x, y + ds)       # top
    p.lineTo(center_x + ds, y)       # right
    p.lineTo(center_x, y - ds)       # bottom
    p.lineTo(center_x - ds, y)       # left
    p.close()
    c.drawPath(p, fill=0, stroke=1)

    c.restoreState()


def _draw_line_with_eyes(c: Canvas, center_x: float, y: float, width: float,
                         color: tuple, line_width: float) -> None:
    c.saveState()
    c.setStrokeColorRGB(*color)
    c.setFillColorRGB(*color)
    c.setLineWidth(line_width)

    half_w = width / 2
    eye_len = 14.0    # horizontal length of eye shape
    eye_height = 5.0  # max vertical bulge
    pupil_r = 1.5
    eye_inset = 4.0   # distance from line end to eye center

    # Central line (between the two eyes)
    line_inner = half_w - eye_inset - eye_len / 2 - 2
    if line_inner > 0:
        c.line(center_x - line_inner, y,
               center_x + line_inner, y)

    # Draw eye shapes at both ends
    for side in [-1, 1]:
        ex = center_x + side * (half_w - eye_inset)  # eye center x

        # Upper arc (bezier curve bowing upward)
        p = c.beginPath()
        p.moveTo(ex - eye_len / 2, y)
        p.curveTo(ex - eye_len / 4, y + eye_height,
                  ex + eye_len / 4, y + eye_height,
                  ex + eye_len / 2, y)
        # Lower arc (bezier curve bowing downward)
        p.curveTo(ex + eye_len / 4, y - eye_height,
                  ex - eye_len / 4, y - eye_height,
                  ex - eye_len / 2, y)
        p.close()
        c.drawPath(p, fill=0, stroke=1)

        # Pupil (filled circle at center)
        c.circle(ex, y, pupil_r, fill=1, stroke=0)

    c.restoreState()


def _draw_line_with_circles(c: Canvas, center_x: float, y: float, width: float,
                            color: tuple, line_width: float) -> None:
    """Line with filled circle endpoints, no center element."""
    c.saveState()
    c.setStrokeColorRGB(*color)
    c.setFillColorRGB(*color)
    c.setLineWidth(line_width)

    half_w = width / 2
    endpoint_r = 1.8

    # Full line between the two endpoint circles
    c.line(center_x - half_w + endpoint_r, y,
           center_x + half_w - endpoint_r, y)

    # Endpoint circles
    c.circle(center_x - half_w, y, endpoint_r, fill=1, stroke=0)
    c.circle(center_x + half_w, y, endpoint_r, fill=1, stroke=0)

    c.restoreState()


def _draw_ornamental_flat(c: Canvas, center_x: float, y: float, width: float,
                          color: tuple, line_width: float) -> None:
    """Ornamental floral without vertical accent diamonds above/below center."""
    c.saveState()
    c.setStrokeColorRGB(*color)
    c.setFillColorRGB(*color)
    c.setLineWidth(line_width)

    # Central diamond
    ds = 4.0  # diamond half-size
    p = c.beginPath()
    p.moveTo(center_x, y + ds)       # top
    p.lineTo(center_x + ds, y)       # right
    p.lineTo(center_x, y - ds)       # bottom
    p.lineTo(center_x - ds, y)       # left
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    # Horizontal petals only (left and right)
    petal_len = 7.0
    petal_width = 3.0
    for side in [-1, 1]:
        sx = center_x + side * (ds + 1)
        ex = center_x + side * (ds + 1 + petal_len)
        pp = c.beginPath()
        pp.moveTo(sx, y)
        pp.curveTo(sx + side * petal_len * 0.4, y + petal_width,
                   sx + side * petal_len * 0.7, y + petal_width * 0.5,
                   ex, y)
        pp.curveTo(sx + side * petal_len * 0.7, y - petal_width * 0.5,
                   sx + side * petal_len * 0.4, y - petal_width,
                   sx, y)
        pp.close()
        c.drawPath(pp, fill=1, stroke=0)

    # Small dots flanking the ornament
    dot_offset = ds + petal_len + 5
    dot_r = 1.2
    for side in [-1, 1]:
        c.circle(center_x + side * dot_offset, y, dot_r, fill=1, stroke=0)

    # Short lines extending outward from the dots
    line_start = dot_offset + dot_r + 3
    line_end = width / 2
    if line_end > line_start:
        for side in [-1, 1]:
            c.line(center_x + side * line_start, y,
                   center_x + side * line_end, y)

    c.restoreState()


_DRAW_FUNCTIONS = {
    DividerStyle.SIMPLE_LINE: _draw_simple_line,
    DividerStyle.GRADUATED_DOTS: _draw_graduated_dots,
    DividerStyle.ORNAMENTAL_FLORAL: _draw_ornamental_floral,
    DividerStyle.LINE_WITH_HEART: _draw_line_with_heart,
    DividerStyle.LINE_WITH_DIAMOND: _draw_line_with_diamond,
    DividerStyle.LINE_WITH_EYES: _draw_line_with_eyes,
    DividerStyle.LINE_WITH_CIRCLES: _draw_line_with_circles,
    DividerStyle.ORNAMENTAL_FLAT: _draw_ornamental_flat,
}
