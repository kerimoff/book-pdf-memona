# Simurq Book PDF Generator

Generate print-ready 8×10 inch interior PDFs with QR codes, images, and customizable typography.

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

The request body is a JSON object with 4 top-level sections:

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

**Page & Typography**

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `page_size` | string | `"8x10"` | Only `"8x10"` supported | Page dimensions in inches. |
| `font_name` | string | `"libre-baskerville"` | See [Supported Fonts](#supported-fonts) | Serif font used for titles and body text. |
| `margins_mm` | object | See below | — | Page margins in millimeters. |
| `body_font_size` | number | `11` | 6–24 | Font size for story body text (pt). |
| `title_font_size` | number | `21` | 12–48 | Font size for story titles (pt). |
| `line_height` | number | `1.55` | 1.0–3.0 | Line height multiplier for body text. |
| `paragraph_spacing` | number | `0.4` | 0–2.0 | Extra spacing between paragraphs as a multiplier of line height. |
| `show_page_numbers` | boolean | `true` | — | Whether to display page numbers. |
| `min_page_count` | integer | `200` | 1–2000 | Minimum total pages in the PDF. Blank pages (page number only) are appended after the last story until this count is reached. Has no effect if content already exceeds the value. |
| `date_font_size` | number | `10` | 6–24 | Font size for recorded date text (pt). |
| `page_number_font_size` | number | `9` | 6–24 | Font size for page numbers (pt). |
| `contributor_font_size` | number | `11` | 6–24 | Font size for the contributor byline (pt). |

**QR Code**

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `qr_color` | string | `"#1A5C52"` | 6-digit hex color | Color of the QR code modules. |
| `qr_logo_enabled` | boolean | `true` | — | Whether to show a logo in the QR code center. |
| `qr_code_size` | number | `60` | 20–200 | QR code width/height in points. |
| `qr_top_spacing` | number | `10` | 0–100 | Space between top of content area and QR code (pt). |

**Story Opener Layout**

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `title_spacing` | number | `35` | 0–100 | Space between QR code and story title (pt). |
| `contributor_spacing` | number | `8` | 0–100 | Space between story title and contributor line (pt). Only applies when `contributor` is set on a story. |
| `date_spacing` | number | `10` | 0–100 | Space between contributor (or title, if no contributor) and recorded date (pt). |
| `divider_spacing` | number | `14` | 0–100 | Space between date and divider line (pt). |
| `story_top_spacing` | number | `40` | 0–100 | Space between divider and start of body text (pt). |
| `divider_style` | string | `"simple-line"` | See [Divider Styles](#divider-styles) | Decorative divider between date and story body. |
| `divider_line_width` | number | `0.5` | 0.1–5.0 | Thickness of the divider line (pt). |

**Image Styling**

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `image_border_width` | number | `0.5` | 0–5.0 | Stroke width of the border around story images (pt). |
| `image_border_color` | string | `"#BFBFBF"` | 6-digit hex color | Border color for story images. |
| `image_border_padding` | number | `4` | 0–20 | Padding between image and its border frame (pt). |

**Colors**

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `date_color` | string | `"#737373"` | 6-digit hex color | Color of the recorded date text. |
| `divider_color` | string | `"#B3B3B3"` | 6-digit hex color | Color of the divider line/shapes. |
| `page_number_color` | string | `"#666666"` | 6-digit hex color | Color of page numbers. |
| `contributor_color` | string | `"#8C8C8C"` | 6-digit hex color | Color of the contributor byline text. |

#### `margins_mm`

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `inside` | number | `24` | 5–50 | Inner margin in mm (spine side, wider for binding). |
| `outside` | number | `20` | 5–50 | Outer margin in mm (trim side). |
| `top` | number | `16` | 5–50 | Top margin in mm. |
| `bottom` | number | `18` | 5–50 | Bottom margin in mm. |

#### Supported Fonts

| Value | Font Name |
|-------|-----------|
| `"noto-serif"` | Noto Serif |
| `"libre-baskerville"` | Libre Baskerville **(default)** |
| `"eb-garamond"` | EB Garamond |
| `"cormorant-garamond"` | Cormorant Garamond |
| `"libertinus-serif"` | Libertinus Serif |
| `"taviraj"` | Taviraj |

> Sans-serif elements (dates, page numbers, author) always use **Noto Sans** regardless of the selected font.

#### Divider Styles

| Value | Description |
|-------|-------------|
| `"simple-line"` | Plain horizontal line **(default)** |
| `"graduated-dots"` | Row of circles, small at edges, large at center |
| `"ornamental-floral"` | Centered ornamental diamond with petal shapes and flanking lines |
| `"line-with-heart"` | Thin line with circle endpoints and a heart at center |
| `"line-with-diamond"` | Thin line with circle endpoints and a diamond at center |
| `"line-with-eyes"` | Horizontal line with decorative eye shapes at both ends |
| `"line-with-circles"` | Line with filled circle endpoints, no center element |
| `"ornamental-flat"` | Ornamental floral without vertical accent diamonds above/below center |

---

### `stories` (required)

An array of story objects. At least one story is required.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `title` | string | **Yes** | — | Story title (1–1000 chars). |
| `body` | string | **Yes** | — | Story body text. Use `\n` for paragraph breaks. |
| `recorded_at` | string | No | `null` | ISO 8601 datetime (e.g. `"2026-03-09T10:00:00.000Z"`). Displayed below the title in a smaller sans-serif font. |
| `qr_target_url` | string | **Yes** | — | URL encoded in the QR code shown above each story. |
| `image_url` | string | No | `null` | URL of an image to display on a full page before the story. |
| `contributor` | string | No | `null` | Name of the person who recorded or submitted the story. Displayed below the title in italic, smaller and lighter — like a byline. |

When `image_url` is provided, the story gets a dedicated image page (left) facing the text page (right). Stories without images start directly with the QR + title + body layout.

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

## Example

See [`examples/book_payload.json`](examples/book_payload.json) for a full request example.

**Minimal request:**

```json
{
  "book": {
    "title": "My Book"
  },
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

**With custom font:**

```json
{
  "book": {
    "title": "My Book"
  },
  "style": {
    "font_name": "eb-garamond",
    "body_font_size": 12
  },
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

---

## Running Locally

```bash
# Install dependencies
npm install
pip install -r requirements.txt   # or use a virtualenv

# Start dev server (Express + FastAPI)
source .venv/bin/activate && PORT=3000 npm run dev
```

## Adding a New Font

1. Place `Regular.ttf`, `Bold.ttf`, and `Italic.ttf` files in `fonts/<font-name>/`
2. Add an entry to `FONT_REGISTRY` in `api/layout.py`
3. Add the value to `SupportedFont` enum in `api/models.py`
