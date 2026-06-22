import os
import time
import uuid
import logging
import hmac
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from api.models import BookRequest, GenerateResponse, ErrorResponse
from api.cover_models import CoverRequest, CoverResponse
from api.pdf_generator import generate_pdf
from api.cover_generator import generate_cover
from api.utils import ensure_storage_dir

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("simurq-api")

app = FastAPI(
    title="Simurq Book PDF Generator API",
    description="Generate print-ready interior PDFs in Simurq style",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")
API_KEY = os.environ.get("API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
SUPABASE_BUCKET = "temp_pdf"


def upload_to_supabase(file_bytes: bytes, storage_path: str, content_type: str = "application/pdf") -> str | None:
    """Upload a file to Supabase Storage and return the public URL, or None on failure."""
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        logger.warning("Supabase credentials not configured, skipping upload")
        return None
    try:
        upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{storage_path}"
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                upload_url,
                content=file_bytes,
                headers={
                    "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
                    "Content-Type": content_type,
                    "x-upsert": "true",
                },
            )
        if resp.status_code in (200, 201):
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{storage_path}"
            logger.info(f"Uploaded to Supabase: {public_url}")
            return public_url
        else:
            logger.error(f"Supabase upload failed ({resp.status_code}): {resp.text}")
            return None
    except Exception as e:
        logger.error(f"Supabase upload error: {e}")
        return None


def verify_api_key(request: Request) -> bool:
    if not API_KEY:
        return False  # reject all requests when API_KEY is not configured
    provided_key = request.headers.get("x-api-key", "")
    if not provided_key:
        return False
    return hmac.compare_digest(provided_key, API_KEY)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/generate-book-pdf")
async def generate_book_pdf(request: Request):
    if not verify_api_key(request):
        return JSONResponse(
            status_code=401,
            content=ErrorResponse(message="Unauthorized: invalid or missing API key").model_dump(),
        )
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message="Invalid JSON body").model_dump(),
        )

    try:
        book_request = BookRequest(**body)
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            errors.append(f"{loc}: {err['msg']}")
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                message="Validation error",
                details=errors,
            ).model_dump(),
        )

    try:
        start_time = time.time()
        logger.info(f"Generating PDF: '{book_request.book.title}' with {len(book_request.stories)} stories")

        pdf_bytes, page_count = generate_pdf(book_request)

        order_id = f"order-{uuid.uuid4().hex[:8]}"
        storage_dir = os.path.join(STORAGE_BASE, "books", order_id, "interior")
        ensure_storage_dir(os.path.join(storage_dir, book_request.output.file_name))
        file_path = os.path.join(storage_dir, book_request.output.file_name)

        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        storage_path = f"books/{order_id}/interior/{book_request.output.file_name}"

        # Upload to Supabase Storage for direct download (bypasses Replit proxy timeout)
        supabase_url = upload_to_supabase(pdf_bytes, storage_path)
        if supabase_url:
            download_url = supabase_url
        else:
            # Fallback to relative local download endpoint
            download_url = f"/api/download/{storage_path}"

        duration = time.time() - start_time
        logger.info(f"PDF generated in {duration:.2f}s: {page_count} pages, {len(pdf_bytes)} bytes")

        response = GenerateResponse(
            file_name=book_request.output.file_name,
            storage_path=storage_path,
            download_url=download_url,
            page_count=page_count,
            story_count=len(book_request.stories),
        )
        return JSONResponse(status_code=200, content=response.model_dump())

    except Exception as e:
        logger.exception(f"PDF generation failed: {e}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(message="Internal server error during PDF generation").model_dump(),
        )


@app.get("/api/download/{file_path:path}")
async def download_file(file_path: str, request: Request):
    if not verify_api_key(request):
        return JSONResponse(
            status_code=401,
            content=ErrorResponse(message="Unauthorized: invalid or missing API key").model_dump(),
        )
    full_path = os.path.realpath(os.path.join(STORAGE_BASE, file_path))
    storage_real = os.path.realpath(STORAGE_BASE)
    if not full_path.startswith(storage_real + os.sep):
        return JSONResponse(
            status_code=403,
            content=ErrorResponse(message="Access denied").model_dump(),
        )
    if not os.path.exists(full_path):
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message="File not found").model_dump(),
        )
    import mimetypes
    media_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
    return FileResponse(
        full_path,
        media_type=media_type,
        filename=os.path.basename(full_path),
    )


@app.post("/generate-cover")
async def generate_cover_endpoint(request: Request):
    if not verify_api_key(request):
        return JSONResponse(
            status_code=401,
            content=ErrorResponse(message="Unauthorized: invalid or missing API key").model_dump(),
        )
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message="Invalid JSON body").model_dump(),
        )

    try:
        cover_request = CoverRequest(**body)
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            errors.append(f"{loc}: {err['msg']}")
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                message="Validation error",
                details=errors,
            ).model_dump(),
        )

    try:
        start_time = time.time()
        logger.info(f"Generating cover: template={cover_request.template}, title='{cover_request.title}'")

        pdf_bytes, thumb_bytes = generate_cover(cover_request)

        order_id = f"order-{uuid.uuid4().hex[:8]}"

        # Save locally
        storage_dir = os.path.join(STORAGE_BASE, "books", order_id, "exterior")
        ensure_storage_dir(os.path.join(storage_dir, "cover_spread.pdf"))
        with open(os.path.join(storage_dir, "cover_spread.pdf"), "wb") as f:
            f.write(pdf_bytes)
        with open(os.path.join(storage_dir, "cover_thumb.png"), "wb") as f:
            f.write(thumb_bytes)

        # Upload to Supabase
        pdf_path = f"books/{order_id}/exterior/cover_spread.pdf"
        thumb_path = f"books/{order_id}/exterior/cover_thumb.png"

        cover_pdf_url = upload_to_supabase(pdf_bytes, pdf_path, "application/pdf")
        thumbnail_url = upload_to_supabase(thumb_bytes, thumb_path, "image/png")

        if not cover_pdf_url:
            cover_pdf_url = f"/api/download/{pdf_path}"
        if not thumbnail_url:
            thumbnail_url = f"/api/download/{thumb_path}"

        duration = time.time() - start_time
        logger.info(f"Cover generated in {duration:.2f}s: PDF={len(pdf_bytes)} bytes, thumb={len(thumb_bytes)} bytes")

        response = CoverResponse(cover_pdf_url=cover_pdf_url, thumbnail_url=thumbnail_url)
        return JSONResponse(status_code=200, content=response.model_dump())

    except Exception as e:
        logger.exception(f"Cover generation failed: {e}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(message="Internal server error during cover generation").model_dump(),
        )
