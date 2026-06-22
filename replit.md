# Simurq Book PDF Generator API

## Overview
A production-ready REST API that accepts structured JSON, generates print-ready PDFs in Simurq (Remento-like) interior style, stores files locally, and returns downloadable file links.

## Architecture
- **Frontend**: React + Vite (API documentation and testing playground)
- **Express Proxy**: Node.js Express server on port 5000 (serves frontend, proxies API requests)
- **Backend API**: Python FastAPI on port 8000 (PDF generation engine)
- **PDF Library**: ReportLab with Noto Serif/Sans fonts
- **Storage**: Local filesystem under `storage/` directory

## Key Files

### Python API (`api/`)
- `api/main.py` - FastAPI routes (`/health`, `/generate-book-pdf`, `/api/download/`)
- `api/models.py` - Pydantic models for request/response validation
- `api/pdf_generator.py` - ReportLab-based PDF rendering engine
- `api/layout.py` - Page constants and layout configuration
- `api/utils.py` - Date formatting (Azerbaijani locale), QR generation, image helpers

### Frontend (`client/src/`)
- `client/src/pages/home.tsx` - API playground with docs, testing, and cURL examples

### Server (`server/`)
- `server/routes.ts` - Express routes that proxy to FastAPI backend
- `server/index.ts` - Express server entry point

### Assets
- `fonts/noto-serif/` - Noto Serif Regular, Bold, Italic TTF files
- `fonts/noto-sans/` - Noto Sans Regular, Bold TTF files
- `examples/book_payload.json` - Sample API request payload
- `storage/` - Generated PDF storage directory

## Authentication
- All endpoints except `/health` require an `X-API-Key` header
- The API key is stored as the `API_KEY` environment secret
- Uses timing-safe comparison (hmac.compare_digest) to prevent timing attacks
- Returns 401 Unauthorized if key is missing or invalid

## API Endpoints
- `GET /health` - Health check (public, no auth)
- `POST /generate-book-pdf` - Generate PDF from JSON payload (auth required)
- `GET /api/download/{path}` - Download generated PDF (auth required)

## Page Design Rules
- 8x10" page size with mirrored margins for print
- Stories without images: QR → Title → Date → Divider → Body
- Stories with images: New spread, photo on left page, opener on right
- Noto Serif for body/titles, Noto Sans for dates
- Bottom-center page numbers (not on title page)
- Blank padding pages (page number only) are appended after the last story until `min_page_count` is reached (default 200)

## Divider Styles
The `divider_style` field in the style config controls the decorative divider between the date and story body text. Possible values:

| Value | Description |
|---|---|
| `simple-line` | Plain horizontal line (default) |
| `graduated-dots` | Row of circles, small at edges, large at center |
| `ornamental-floral` | Centered ornamental diamond with petal shapes and flanking lines |
| `line-with-heart` | Thin line with circle endpoints and a heart at center |
| `line-with-diamond` | Thin line with circle endpoints and a diamond at center |
| `line-with-eyes` | Horizontal line with decorative eye shapes at both ends |

## Running
The workflow `Start application` runs `npm run dev` which starts Express (port 5000) and automatically spawns the FastAPI process (port 8000).
