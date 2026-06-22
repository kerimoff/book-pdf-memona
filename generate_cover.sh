#!/usr/bin/env bash
#
# Usage: ./generate_cover.sh <photo_path> [template] [base_url]
#
# Generates a book cover by sending a photo to the cover generation API.
#
# Arguments:
#   photo_path  - Path to a JPEG or PNG photo file
#   template    - 1 (Classic) or 2 (Full Bleed). Default: 1
#   base_url    - Optional API base URL (default: http://localhost:5000)
#
# Environment:
#   API_KEY     - Optional API key for authentication

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <photo_path> [template] [base_url]"
  echo ""
  echo "  photo_path  - Path to a JPEG or PNG photo"
  echo "  template    - 1 (Classic) or 2 (Full Bleed). Default: 1"
  echo "  base_url    - API base URL. Default: http://localhost:5000"
  exit 1
fi

PHOTO_PATH="$1"
TEMPLATE="${2:-1}"
BASE_URL="${3:-http://localhost:3000}"

if [ ! -f "$PHOTO_PATH" ]; then
  echo "Error: Photo file '$PHOTO_PATH' not found"
  exit 1
fi

# Build JSON payload with base64 photo via Python (avoids shell arg length limits)
echo "Building payload..."
TMPFILE=$(mktemp)
trap "rm -f '$TMPFILE'" EXIT

python3 -c "
import json, base64, sys

with open(sys.argv[1], 'rb') as f:
    photo_b64 = base64.b64encode(f.read()).decode()

payload = {
    'template': int(sys.argv[2]),
    'title': 'Mənim gözəl həyatım',
    'subtitle': 'Sevil Həsənovanın dilindən',
    'color': '#2D6B5E',
    'page_count': 96,
    'photo': photo_b64,
}

with open(sys.argv[3], 'w') as out:
    json.dump(payload, out)
" "$PHOTO_PATH" "$TEMPLATE" "$TMPFILE"

# Build headers
HEADERS=(-H "Content-Type: application/json")
if [ -n "${API_KEY:-}" ]; then
  HEADERS+=(-H "x-api-key: $API_KEY")
fi

echo "Sending cover request (template=$TEMPLATE) to $BASE_URL/generate-cover ..."

RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST \
  "${HEADERS[@]}" \
  -d @"$TMPFILE" \
  "$BASE_URL/generate-cover")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
  echo "Error: API returned HTTP $HTTP_CODE"
  echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
  exit 1
fi

echo "Cover generated successfully!"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"

# Extract URLs
COVER_URL=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['cover_pdf_url'])")
THUMB_URL=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['thumbnail_url'])")

# Prepend base URL to relative paths
if [[ "$COVER_URL" == /* ]]; then
  COVER_URL="${BASE_URL}${COVER_URL}"
fi
if [[ "$THUMB_URL" == /* ]]; then
  THUMB_URL="${BASE_URL}${THUMB_URL}"
fi

# Build download headers
DL_HEADERS=(-s)
if [ -n "${API_KEY:-}" ]; then
  DL_HEADERS+=(-H "x-api-key: $API_KEY")
fi

# Download cover PDF
echo ""
echo "Downloading cover_spread.pdf ..."
HTTP_CODE=$(curl -w "%{http_code}" \
  "${DL_HEADERS[@]}" \
  -o "cover_spread.pdf" \
  "$COVER_URL")

if [ "$HTTP_CODE" != "200" ]; then
  echo "Error: Cover PDF download failed with HTTP $HTTP_CODE"
  rm -f "cover_spread.pdf"
else
  echo "Downloaded: cover_spread.pdf ($(wc -c < cover_spread.pdf | tr -d ' ') bytes)"
fi

# Download thumbnail
echo "Downloading cover_thumb.png ..."
HTTP_CODE=$(curl -w "%{http_code}" \
  "${DL_HEADERS[@]}" \
  -o "cover_thumb.png" \
  "$THUMB_URL")

if [ "$HTTP_CODE" != "200" ]; then
  echo "Error: Thumbnail download failed with HTTP $HTTP_CODE"
  rm -f "cover_thumb.png"
else
  echo "Downloaded: cover_thumb.png ($(wc -c < cover_thumb.png | tr -d ' ') bytes)"
fi
