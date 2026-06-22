# Simurq Book PDF Generator

Generate print-ready book interior PDFs with QR codes, multi-photo collages, and customisable typography.

## API

### `POST /generate-book-pdf`

Generates a PDF book and returns a download URL.

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type` | Yes | Must be `application/json` |
| `x-api-key` | No | API key (required only if `API_KEY` env var is set) |

---

### Request Body

```jsonc
{
  "book": { ... },      // required — book metadata
  "style": { ... },     // optional — layout and typography settings
  "stories": [ ... ],   // required — array of stories (min 1)
  "output": { ... }     // optional — output file settings
}
```

---

### `book` (required)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `title` | string | **Yes** | — | Book title (1–500 chars). Displayed on the title page. |
| `subtitle` | string | No | `null` | Subtitle shown below the title on the title page. |
| `author` | string | No | `null` | Author name shown on the title page. |
| `language` | string | No | `"az"` | Language code (max 10 chars). Used for date formatting. |
| `brand` | string | No | `"simurq"` | Brand identifier (max 50 chars). |

---

### `style` (optional)

All fields have sensible defaults — you can omit the entire `style` object.

#### Page & Size

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `page_size` | string | `"B5"` | See [Page Sizes](#page-sizes) | Page dimensions preset. |
| `custom_width_mm` | number | `null` | 100–400 | Width in mm. Required when `page_size` is `"custom"`. |
| `custom_height_mm` | number | `null` | 100–500 | Height in mm. Required when `page_size` is `"custom"`. |
| `margins_mm` | object | See below | — | Page margins in millimetres. |
| `print_cut_margin` | number | `0` | 0–30 | Extra blank space added to the outer edge of each page for print-house trimming (mm). |
| `min_page_count` | integer | `200` | 1–2000 | Minimum total pages. Blank pages are appended after the last story until this count is reached. |

#### Page Sizes

| Value | Dimensions |
|-------|-----------|
| `"B5"` | 176 × 250 mm **(default)** |
| `"8x10"` | 203.2 × 254 mm |
| `"6x9"` | 152.4 × 228.6 mm |
| `"A4"` | 210 × 297 mm |
| `"A5"` | 148 × 210 mm |
| `"letter"` | 215.9 × 279.4 mm |
| `"custom"` | Specify `custom_width_mm` and `custom_height_mm` |

#### `margins_mm`

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `inside` | number | `24` | 5–50 | Inner margin in mm (spine side, wider for binding). |
| `outside` | number | `20` | 5–50 | Outer margin in mm (trim side). |
| `top` | number | `20` | 5–50 | Top margin in mm. |
| `bottom` | number | `22` | 5–50 | Bottom margin in mm. |

#### Typography

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `font_name` | string | `"libre-baskerville"` | See [Fonts](#supported-fonts) | Serif font for titles and body text. |
| `body_font_size` | number | `11` | 6–24 | Body text size (pt). |
| `title_font_size` | number | `21` | 12–48 | Story title size (pt). |
| `line_height` | number | `1.55` | 1.0–3.0 | Line height multiplier. |
| `paragraph_spacing` | number | `0.4` | 0–2.0 | Extra spacing between paragraphs as a multiple of line height. |
| `date_font_size` | number | `10` | 6–24 | Recorded-date text size (pt). |
| `page_number_font_size` | number | `9` | 6–24 | Page number size (pt). |
| `contributor_font_size` | number | `11` | 6–24 | Contributor byline size (pt). |
| `show_page_numbers` | boolean | `true` | — | Whether to display page numbers. |

#### Supported Fonts

| Value | Font Name |
|-------|-----------|
| `"noto-serif"` | Noto Serif |
| `"libre-baskerville"` | Libre Baskerville **(default)** |
| `"eb-garamond"` | EB Garamond |
| `"cormorant-garamond"` | Cormorant Garamond |
| `"libertinus-serif"` | Libertinus Serif |
| `"taviraj"` | Taviraj |
| `"crimson-pro"` | Crimson Pro |

> Sans-serif elements (dates, page numbers, author) always use **Noto Sans** regardless of the selected font.

#### QR Code

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `qr_color` | string | `"#1A5C52"` | 6-digit hex | QR code module colour. |
| `logo_color` | string | `"#184b52"` | 6-digit hex | Colour of the Simurq logo inside the QR code and on the splash page. |
| `qr_logo_enabled` | boolean | `true` | — | Whether to embed the logo in the QR code centre. |
| `qr_code_size` | number | `60` | 20–200 | QR code width/height (pt). |
| `qr_top_spacing` | number | `10` | 0–100 | Gap between content area top and QR code (pt). |

#### Story Opener Layout

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `title_spacing` | number | `35` | 0–100 | Gap between QR code and story title (pt). |
| `contributor_spacing` | number | `8` | 0–100 | Gap between title and contributor byline (pt). |
| `date_spacing` | number | `10` | 0–100 | Gap between contributor (or title) and recorded date (pt). |
| `divider_spacing` | number | `14` | 0–100 | Gap between date and divider line (pt). |
| `story_top_spacing` | number | `40` | 0–100 | Gap between divider and start of body text (pt). Also controls the gap below an inline landscape image. |
| `divider_style` | string | `"simple-line"` | See [Dividers](#divider-styles) | Decorative divider between date and body. |
| `divider_line_width` | number | `0.5` | 0.1–5.0 | Divider stroke thickness (pt). |

#### Divider Styles

| Value | Description |
|-------|-------------|
| `"simple-line"` | Plain horizontal line **(default)** |
| `"graduated-dots"` | Row of circles, small at edges, large at centre |
| `"ornamental-floral"` | Centred ornamental diamond with petal shapes and flanking lines |
| `"line-with-heart"` | Thin line with circle endpoints and a heart at centre |
| `"line-with-diamond"` | Thin line with circle endpoints and a diamond at centre |
| `"line-with-eyes"` | Line with decorative eye shapes at both ends |
| `"line-with-circles"` | Line with filled circle endpoints |
| `"ornamental-flat"` | Ornamental floral without vertical accent diamonds |

#### Image Styling

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `image_border_width` | number | `0.5` | 0–5.0 | Stroke width of the border drawn around images and collages (pt). Set to `0` to remove all borders. |
| `image_border_color` | string | `"#BFBFBF"` | 6-digit hex | Border colour. |
| `image_border_padding` | number | `4` | 0–20 | Padding between image and its border frame (pt). |
| `full_page_image_margin` | number | `0` | 0–50 | Extra margin added when an image is scaled to fill an entire page (mm). |

#### Colors

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `body_text_color` | string | `"#000000"` | 6-digit hex | Body text colour. |
| `date_color` | string | `"#737373"` | 6-digit hex | Recorded-date text colour. |
| `divider_color` | string | `"#B3B3B3"` | 6-digit hex | Divider line/shape colour. |
| `page_number_color` | string | `"#666666"` | 6-digit hex | Page number colour. |
| `contributor_color` | string | `"#8C8C8C"` | 6-digit hex | Contributor byline colour. |

#### Story Reordering (advanced)

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `allow_reorder` | boolean | `false` | — | When `true`, the generator may swap the order of adjacent stories to avoid blank filler pages before image spreads. |
| `allow_reorder_count` | integer | `0` | ≥ 0 | How many stories ahead to search for a swap candidate. `0` means search all remaining stories. |

---

### `stories` (required)

An array of story objects. At least one is required.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `title` | string | **Yes** | — | Story title (1–1000 chars). |
| `body` | string | **Yes** | — | Story body text. Use `\n` for paragraph breaks. |
| `recorded_at` | string | No | `null` | ISO 8601 datetime (e.g. `"2026-03-09T10:00:00.000Z"`). Displayed below the title. |
| `qr_target_url` | string | **Yes** | — | URL encoded in the QR code shown above each story. |
| `image_urls` | array | No | `[]` | Up to 3 image URLs. See [Multi-Photo Layout](#multi-photo-layout). |
| `image_url` | string | No | `null` | Backwards-compatible alias for a single image. Equivalent to `image_urls: ["<url>"]`. |
| `contributor` | string | No | `null` | Name of the person who recorded the story. Shown below the title in italic. |
| `relation` | string | No | `null` | Relationship of the contributor (e.g. "Qızı"). Shown below the contributor name. |

#### Multi-Photo Layout

Stories support **up to 3 photos** via `image_urls`. Photos can be any aspect ratio — the layout engine selects the best collage template and sizes images to maximise their visible area.

**Collage templates** (selected automatically based on aspect ratios):

| Template | Triggered when | Description |
|----------|---------------|-------------|
| `1-single` | 1 image | Image centred on a full page |
| `2-hstack` | 2 images, at least one landscape or both square-ish | Stacked vertically, each filling full width |
| `2-vstack` | 2 images, both tall portrait | Side by side, each filling full height |
| `3-hstack` | 3 images, all landscape or all square-ish | All 3 stacked vertically |
| `3-top-spread` | 3 images, 1+ landscape | Widest image spans top; remaining pair fills bottom row |
| `3-left-tall` | 3 images, all tall portrait | Tallest image on left; two smaller images stacked on right |

Each image is drawn **fit** (full image visible, letterbox-free within its slot). All images in a collage share one outer border.

**Special case — landscape image inline:** When a story has exactly 1 landscape image and 1–2 portrait/square images, the landscape image is placed **inline** on the text page (below the title/QR block), and the remaining images appear as a collage on the facing page. This mirrors the existing behaviour for single landscape images.

**Page placement rules:**
- Collage pages always appear on the **left (even)** page, facing the story text on the right.
- A photo page from one story never shares a spread with another story's text.
- Long stories use a sandwich layout: text opener → collage page → remaining text.

---

### `output` (optional)

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `file_name` | string | `"simurq-book.pdf"` | Must end with `.pdf`, no path separators | Output PDF filename. |

---

### Response

**Success (200):**

```json
{
  "status": "ok",
  "file_name": "simurq-book.pdf",
  "storage_path": "books/order-abc12345/interior/simurq-book.pdf",
  "download_url": "http://localhost:3000/api/download/books/order-abc12345/interior/simurq-book.pdf",
  "page_count": 6,
  "story_count": 3
}
```

**Validation Error (422):**

```json
{
  "status": "error",
  "message": "Validation error",
  "details": ["book -> title: Field required"]
}
```

---

### `GET /api/download/{file_path}`

Download a generated PDF using the `download_url` from the generation response.

### `GET /health`

Returns `{"status": "ok"}` when the API is running.

---

## Examples

See [`examples/`](examples/) for full request payloads:

| File | Description |
|------|-------------|
| `small_example.json` | 12 stories covering every collage template and ratio combination |
| `big_example.json` | 30 stories with mixed layouts |
| `book_payload.json` | Minimal 3-story example |

**Minimal request:**

```json
{
  "book": { "title": "My Book" },
  "stories": [
    {
      "title": "First Story",
      "body": "Once upon a time...",
      "recorded_at": "2026-01-01T00:00:00Z",
      "qr_target_url": "https://example.com/story-1"
    }
  ]
}
```

**Story with 3 photos (mixed ratios):**

```json
{
  "title": "Summer Trip",
  "body": "We drove south for three days...",
  "qr_target_url": "https://example.com/story-2",
  "image_urls": [
    "https://example.com/landscape.jpg",
    "https://example.com/portrait.jpg",
    "https://example.com/square.jpg"
  ]
}
```

**No borders, tighter spacing:**

```json
{
  "book": { "title": "My Book" },
  "style": {
    "image_border_width": 0,
    "image_border_padding": 0,
    "story_top_spacing": 20
  },
  "stories": [ ... ]
}
```

---

## Running Locally

```bash
# Install dependencies
npm install
pip install -r requirements.txt   # or: uv sync

# Start dev server (Express + FastAPI)
source .venv/bin/activate && PORT=3000 npm run dev
```

---

## Adding a New Font

1. Place `Regular.ttf`, `Bold.ttf`, and `Italic.ttf` in `fonts/<font-name>/`
2. Add an entry to `FONT_REGISTRY` in `api/layout.py`
3. Add the value to the `SupportedFont` enum in `api/models.py`
