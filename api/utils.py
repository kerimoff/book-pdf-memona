import io
import os
import logging
from datetime import datetime
from typing import Optional
from PIL import Image, ImageDraw, ImageOps
import httpx
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import CircleModuleDrawer, RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask

logger = logging.getLogger(__name__)

AZ_MONTHS = {
    1: "yanvar",
    2: "fevral",
    3: "mart",
    4: "aprel",
    5: "may",
    6: "iyun",
    7: "iyul",
    8: "avqust",
    9: "sentyabr",
    10: "oktyabr",
    11: "noyabr",
    12: "dekabr",
}


def format_date_az(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        month_name = AZ_MONTHS.get(dt.month, "")
        return f"{dt.day} {month_name} {dt.year}"
    except Exception:
        return date_str


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def hex_to_rgb_floats(hex_color: str) -> tuple[float, float, float]:
    """Convert '#RRGGBB' to (r, g, b) with each component in 0.0-1.0."""
    r, g, b = _hex_to_rgb(hex_color)
    return (r / 255.0, g / 255.0, b / 255.0)


def _parse_svg_transform(transform_str: str) -> tuple:
    import re
    m = re.search(r'matrix\(([^)]+)\)', transform_str)
    if m:
        vals = [float(v) for v in re.split(r'[,\s]+', m.group(1).strip())]
        return tuple(vals[:6])
    m = re.search(r'translate\(([^)]+)\)', transform_str)
    if m:
        vals = [float(v) for v in re.split(r'[,\s]+', m.group(1).strip())]
        tx = vals[0]
        ty = vals[1] if len(vals) > 1 else 0.0
        return (1.0, 0.0, 0.0, 1.0, tx, ty)
    return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _compose_matrices(parent: tuple, child: tuple) -> tuple:
    a1, b1, c1, d1, e1, f1 = parent
    a2, b2, c2, d2, e2, f2 = child
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _apply_svg_matrix(x: float, y: float, matrix: tuple) -> tuple:
    a, b, c, d, e, f = matrix
    return (a * x + c * y + e, b * x + d * y + f)


_SVG_SKIP_TAGS = {'defs', 'clipPath', 'mask', 'symbol', 'linearGradient', 'radialGradient', 'pattern', 'filter'}


def _build_clip_defs(root) -> dict:
    """Return {clip_id: path_d} for all <clipPath> elements in <defs>."""
    defs = {}
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'clipPath':
            clip_id = elem.get('id', '')
            for child in elem.iter():
                ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if ctag == 'path':
                    d = child.get('d', '')
                    if d and clip_id:
                        defs[clip_id] = d
                        break
    return defs


def _svg_path_is_curved(path_d: str) -> bool:
    """True if the path contains any curves (Bezier / arc), i.e. it is not a plain polygon."""
    return any(c in path_d for c in ('C', 'c', 'S', 's', 'Q', 'q', 'A', 'a'))


def _leaf_fill(elem) -> str | None:
    """Return the first explicit #rrggbb fill found on any descendant <path>."""
    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
    if tag == 'path':
        f = elem.get('fill', '')
        if f and f != 'none' and f.startswith('#'):
            return f
    for child in elem:
        result = _leaf_fill(child)
        if result:
            return result
    return None


def _collect_svg_paths(elem, accumulated=(1.0, 0.0, 0.0, 1.0, 0.0, 0.0),
                       clip_defs: dict | None = None) -> list:
    """Recursively collect (path_d, matrix, fill_override_or_None).

    fill_override_or_None:
        None  — render with the theme colour passed to draw_svg_logo_vector
        str   — render with this specific hex colour (e.g. '#ff5757' for the heart)

    When a <g clip-path="url(#id)"> references a *curved* clip shape AND its
    descendant <path> has an explicit fill, we draw the clip shape directly
    with that fill colour (instead of drawing the clipped rectangle as a square).
    """
    results = []
    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

    if tag in _SVG_SKIP_TAGS:
        return results

    transform_str = elem.get('transform', '')
    current = _compose_matrices(accumulated, _parse_svg_transform(transform_str)) if transform_str else accumulated

    # Handle clip-path references: if the clip shape is curved and the child
    # has an explicit fill colour, draw the clip shape rather than the rect.
    clip_ref = elem.get('clip-path', '')
    if clip_ref and clip_defs is not None:
        clip_id = clip_ref.replace('url(#', '').rstrip(')')
        clip_d = clip_defs.get(clip_id, '')
        if clip_d and _svg_path_is_curved(clip_d):
            fill = _leaf_fill(elem)
            if fill:
                results.append((clip_d, current, fill))
                return results   # don't recurse — the clip IS the visual shape

    if tag == 'path':
        d = elem.get('d', '')
        if d:
            results.append((d, current, None))

    for child in elem:
        results.extend(_collect_svg_paths(child, current, clip_defs))

    return results


def _parse_path_d(d: str) -> list:
    import re
    tokens = re.findall(r'[MmLlCcZz]|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?', d)
    commands = []
    i = 0
    while i < len(tokens):
        if tokens[i] in 'MmLlCcZz':
            cmd = tokens[i]
            i += 1
            params = []
            while i < len(tokens) and tokens[i] not in 'MmLlCcZz':
                params.append(float(tokens[i]))
                i += 1
            commands.append((cmd, params))
        else:
            i += 1
    return commands


def get_svg_natural_size(svg_path: str) -> tuple[float, float]:
    """Return (width, height) from an SVG viewBox."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.parse(svg_path).getroot()
        viewbox = root.get('viewBox', '0 0 1000 1000')
        vb = [float(v) for v in viewbox.split()]
        return (vb[2] - vb[0], vb[3] - vb[1])
    except Exception:
        return (1000.0, 1000.0)


def draw_svg_logo_vector(
    canvas_obj,
    svg_path: str,
    x: float,
    y: float,
    size: float,
    color_hex: str,
) -> None:
    """Draw an SVG logo as crisp vector paths on a ReportLab canvas.
    x, y is the bottom-left corner (ReportLab convention). size controls the max dimension.
    Handles nested <g transform="translate/matrix(...)"> and multiple path elements.
    """
    import xml.etree.ElementTree as ET

    try:
        tree = ET.parse(svg_path)
    except Exception:
        return

    root = tree.getroot()
    viewbox = root.get('viewBox', '0 0 1000 1000')
    vb = [float(v) for v in viewbox.split()]
    vb_w, vb_h = vb[2] - vb[0], vb[3] - vb[1]
    scale = size / max(vb_w, vb_h)

    clip_defs = _build_clip_defs(root)
    paths = _collect_svg_paths(root, clip_defs=clip_defs)
    if not paths:
        return

    def to_rl(px, py, matrix):
        tx, ty = _apply_svg_matrix(px, py, matrix)
        return (x + (tx - vb[0]) * scale, y + size - (ty - vb[1]) * scale)

    theme_r, theme_g, theme_b = _hex_to_rgb(color_hex)
    canvas_obj.saveState()
    canvas_obj.setFillColorRGB(theme_r / 255, theme_g / 255, theme_b / 255)
    current_fill = color_hex  # track which fill is currently set on the canvas

    for d, matrix, fill_override in paths:
        # Switch fill colour when a path has its own explicit colour (e.g. the heart)
        target_fill = fill_override if fill_override else color_hex
        if target_fill != current_fill:
            fr, fg, fb = _hex_to_rgb(target_fill)
            canvas_obj.setFillColorRGB(fr / 255, fg / 255, fb / 255)
            current_fill = target_fill
        p = canvas_obj.beginPath()
        cur_x, cur_y = 0.0, 0.0

        for cmd, params in _parse_path_d(d):
            if cmd == 'M':
                cur_x, cur_y = params[0], params[1]
                p.moveTo(*to_rl(cur_x, cur_y, matrix))
            elif cmd == 'L':
                for i in range(0, len(params), 2):
                    cur_x, cur_y = params[i], params[i + 1]
                    p.lineTo(*to_rl(cur_x, cur_y, matrix))
            elif cmd == 'C':
                for i in range(0, len(params), 6):
                    x1, y1 = to_rl(params[i], params[i + 1], matrix)
                    x2, y2 = to_rl(params[i + 2], params[i + 3], matrix)
                    xe, ye = to_rl(params[i + 4], params[i + 5], matrix)
                    p.curveTo(x1, y1, x2, y2, xe, ye)
                    cur_x, cur_y = params[i + 4], params[i + 5]
            elif cmd in 'zZ':
                p.close()

        canvas_obj.drawPath(p, fill=1, stroke=0)

    canvas_obj.restoreState()


def _make_circular_logo(logo_path: str, diameter: int) -> Image.Image:
    logo = Image.open(logo_path).convert("RGBA")
    logo = logo.resize((diameter, diameter), Image.LANCZOS)
    bg = Image.new("RGBA", (diameter, diameter), (255, 255, 255, 0))
    mask = Image.new("L", (diameter, diameter), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, diameter - 1, diameter - 1), fill=255)
    white_circle = Image.new("RGBA", (diameter, diameter), (255, 255, 255, 255))
    white_circle.putalpha(mask)
    bg = Image.alpha_composite(bg, white_circle)
    logo_mask = logo.split()[3] if logo.mode == "RGBA" else None
    bg.paste(logo, (0, 0), mask=logo_mask)
    return bg


def draw_qr_vector(
    canvas_obj,
    url: str,
    x: float,
    y: float,
    size: float,
    qr_color: str = "#1A5C52",
    logo_path: Optional[str] = None,
    logo_color: str = "#184b52",
) -> None:
    """Draw a styled QR code as crisp vector graphics directly on a ReportLab canvas."""
    from reportlab.lib.colors import Color
    from reportlab.lib.utils import ImageReader

    use_logo = logo_path is not None and os.path.isfile(logo_path)

    qr = qrcode.QRCode(
        version=1,
        error_correction=(
            qrcode.constants.ERROR_CORRECT_H if use_logo
            else qrcode.constants.ERROR_CORRECT_M
        ),
        box_size=1,
        border=0,
    )
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)

    border = 1
    cell = size / (n + 2 * border)

    r, g, b = _hex_to_rgb(qr_color)
    fg = Color(r / 255, g / 255, b / 255)
    white = Color(1, 1, 1)

    finder_set: set[tuple[int, int]] = set()
    for fr, fc in ((0, 0), (0, n - 7), (n - 7, 0)):
        for dr in range(7):
            for dc in range(7):
                finder_set.add((fr + dr, fc + dc))

    canvas_obj.saveState()

    # Data modules as circles
    canvas_obj.setFillColor(fg)
    for row in range(n):
        for col in range(n):
            if matrix[row][col] and (row, col) not in finder_set:
                cx = x + (border + col + 0.5) * cell
                cy = y + size - (border + row + 0.5) * cell
                canvas_obj.circle(cx, cy, cell * 0.42, fill=1, stroke=0)

    # Finder patterns as rounded rectangles
    for fr, fc in ((0, 0), (0, n - 7), (n - 7, 0)):
        fx = x + (border + fc) * cell
        fy = y + size - (border + fr + 7) * cell
        rr = cell * 1.0

        canvas_obj.setFillColor(fg)
        canvas_obj.roundRect(fx, fy, 7 * cell, 7 * cell, rr, fill=1, stroke=0)

        canvas_obj.setFillColor(white)
        canvas_obj.roundRect(fx + cell, fy + cell, 5 * cell, 5 * cell, rr * 0.5, fill=1, stroke=0)

        canvas_obj.setFillColor(fg)
        canvas_obj.roundRect(fx + 2 * cell, fy + 2 * cell, 3 * cell, 3 * cell, rr * 0.3, fill=1, stroke=0)

    # Logo in center
    if use_logo:
        logo_size = size * 0.24
        lx = x + (size - logo_size) / 2
        ly = y + (size - logo_size) / 2

        pad = logo_size * 0.12
        canvas_obj.setFillColor(white)
        canvas_obj.rect(lx - pad, ly - pad, logo_size + 2 * pad, logo_size + 2 * pad, fill=1, stroke=0)

        if logo_path.lower().endswith('.svg'):
            draw_svg_logo_vector(canvas_obj, logo_path, lx, ly, logo_size, logo_color)
        else:
            logo_img = Image.open(logo_path).convert("RGB")
            logo_buf = pil_image_to_reportlab(logo_img)
            logo_reader = ImageReader(logo_buf)
            canvas_obj.drawImage(logo_reader, lx, ly, logo_size, logo_size, preserveAspectRatio=True)

    canvas_obj.restoreState()


def generate_qr_image(
    url: str,
    size: int = 120,
    qr_color: str = "#000000",
    logo_path: Optional[str] = None,
) -> Image.Image:
    use_logo = logo_path is not None and os.path.isfile(logo_path)

    qr = qrcode.QRCode(
        version=1,
        error_correction=(
            qrcode.constants.ERROR_CORRECT_H if use_logo
            else qrcode.constants.ERROR_CORRECT_M
        ),
        box_size=10,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)

    rgb = _hex_to_rgb(qr_color)
    color_mask = SolidFillColorMask(
        back_color=(255, 255, 255),
        front_color=rgb,
    )

    make_image_kwargs: dict = {
        "image_factory": StyledPilImage,
        "module_drawer": CircleModuleDrawer(),
        "eye_drawer": RoundedModuleDrawer(),
        "color_mask": color_mask,
    }

    if use_logo:
        logo_diameter = max(1, int(size * 0.22))
        make_image_kwargs["embedded_image"] = _make_circular_logo(logo_path, logo_diameter)
        make_image_kwargs["embedded_image_ratio"] = 0.25

    img = qr.make_image(**make_image_kwargs)
    pil_img = img.get_image()

    if pil_img.mode == "RGBA":
        background = Image.new("RGB", pil_img.size, (255, 255, 255))
        background.paste(pil_img, mask=pil_img.split()[3])
        pil_img = background

    pil_img = pil_img.resize((size, size), Image.LANCZOS)
    return pil_img


def _is_safe_url(url: str) -> bool:
    from urllib.parse import urlparse
    import ipaddress
    import socket

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    try:
        resolved = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in resolved:
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
    except (socket.gaierror, ValueError):
        return False

    return True


def fetch_image(url: str, timeout: float = 15.0) -> Optional[Image.Image]:
    try:
        if not _is_safe_url(url):
            logger.warning(f"Blocked unsafe image URL: {url}")
            return None

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            if len(response.content) > 50 * 1024 * 1024:
                logger.warning(f"Image too large from {url}")
                return None
            img = Image.open(io.BytesIO(response.content))
            img = ImageOps.exif_transpose(img)
            if img.mode != "RGB":
                img = img.convert("RGB")
            return img
    except Exception as e:
        logger.warning(f"Failed to fetch image from {url}: {e}")
        return None


def wrap_text(text: str, max_width: float, canvas_obj, font_name: str, font_size: float) -> list[tuple[str, bool]]:
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append(("", True))
            continue
        words = paragraph.split()
        if not words:
            lines.append(("", True))
            continue
        current_line = words[0]
        for word in words[1:]:
            test_line = current_line + " " + word
            width = canvas_obj.stringWidth(test_line, font_name, font_size)
            if width <= max_width:
                current_line = test_line
            else:
                lines.append((current_line, False))
                current_line = word
        lines.append((current_line, True))
    return lines


def decode_base64_photo(b64_string: str) -> Image.Image:
    """Decode a base64-encoded image string to a PIL Image (RGB).
    Handles optional data URI prefix (data:image/...;base64,)."""
    import base64
    if "," in b64_string and b64_string.index(",") < 100:
        b64_string = b64_string.split(",", 1)[1]
    raw = base64.b64decode(b64_string)
    img = Image.open(io.BytesIO(raw))
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def ensure_storage_dir(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def pil_image_to_reportlab(pil_img: Image.Image) -> io.BytesIO:
    """Convert a PIL image to a lossless PNG BytesIO buffer for ReportLab."""
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    return buf
