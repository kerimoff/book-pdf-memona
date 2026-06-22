#!/usr/bin/env bash
#
# Usage: ./generate.sh <input.json> [base_url]
#
# Sends the JSON file to the PDF generator API and downloads the resulting PDF.
#
# Arguments:
#   input.json  - Path to the book JSON input file
#   base_url    - Optional API base URL (default: http://localhost:5000)
#
# Environment:
#   API_KEY     - Optional API key for authentication

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <input.json> [base_url]"
  exit 1
fi

INPUT_FILE="$1"
BASE_URL="${2:-http://localhost:5000}"

if [ ! -f "$INPUT_FILE" ]; then
  echo "Error: File '$INPUT_FILE' not found"
  exit 1
fi

# Build headers
HEADERS=(-H "Content-Type: application/json")
if [ -n "${API_KEY:-}" ]; then
  HEADERS+=(-H "x-api-key: $API_KEY")
fi

echo "Sending $INPUT_FILE to $BASE_URL/generate-book-pdf ..."

RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST \
  "${HEADERS[@]}" \
  -d @"$INPUT_FILE" \
  "$BASE_URL/generate-book-pdf")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
  echo "Error: API returned HTTP $HTTP_CODE"
  echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
  exit 1
fi

echo "PDF generated successfully!"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"

# Extract download URL and file name
DOWNLOAD_URL=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['download_url'])")
FILE_NAME=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['file_name'])")

echo ""
echo "Downloading $FILE_NAME ..."

DOWNLOAD_HEADERS=()
if [ -n "${API_KEY:-}" ]; then
  DOWNLOAD_HEADERS+=(-H "x-api-key: $API_KEY")
fi

HTTP_CODE=$(curl -s -w "%{http_code}" \
  "${DOWNLOAD_HEADERS[@]}" \
  -o "$FILE_NAME" \
  "$DOWNLOAD_URL")

if [ "$HTTP_CODE" != "200" ]; then
  echo "Error: Download failed with HTTP $HTTP_CODE"
  rm -f "$FILE_NAME"
  exit 1
fi

echo "Downloaded: $FILE_NAME ($(wc -c < "$FILE_NAME" | tr -d ' ') bytes)"
