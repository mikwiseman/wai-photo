import os
import random
import base64
from pathlib import Path
from io import BytesIO

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from PIL import Image
import httpx

# Configuration
MASKS_DIR = Path(__file__).parent / "masks"
MAX_IMAGE_SIZE_MB = 10
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"]
REQUEST_TIMEOUT = 30.0
API_KEY = os.environ.get("API_KEY")


# API Key authentication
async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify the API key from request header."""
    if not API_KEY:
        # If no API_KEY is set, allow all requests (for local development)
        return True
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# FastAPI app
app = FastAPI(
    title="Photo Masking API",
    description="API for applying decorative masks to photos",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class MaskByUrlRequest(BaseModel):
    url: HttpUrl


class MaskResponse(BaseModel):
    success: bool
    mask_used: str
    image_data: str
    content_type: str = "image/png"


# Helper functions
def get_random_mask() -> tuple[Path, str]:
    """Select a random mask file from the masks directory."""
    mask_files = list(MASKS_DIR.glob("mask_*.png"))
    if not mask_files:
        raise HTTPException(status_code=500, detail="No mask files found")
    mask_path = random.choice(mask_files)
    return mask_path, mask_path.name


def apply_mask(image_buffer: BytesIO, mask_path: Path) -> Image.Image:
    """
    Apply mask as a crop shape to the image.

    The mask's alpha channel defines visible areas:
    - Opaque (alpha=255) = visible in output
    - Transparent (alpha=0) = cut out
    """
    try:
        image = Image.open(image_buffer)
        if image.mode != "RGBA":
            image = image.convert("RGBA")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot open image: {str(e)}")

    mask = Image.open(mask_path).convert("RGBA")
    mask_width, mask_height = mask.size

    # Resize to cover mask dimensions
    img_width, img_height = image.size
    scale = max(mask_width / img_width, mask_height / img_height)
    new_width = int(img_width * scale)
    new_height = int(img_height * scale)
    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Top-center crop to mask size (for portraits/faces)
    left = (new_width - mask_width) // 2  # Center horizontally
    top = 0  # Start from top to capture faces
    image = image.crop((left, top, left + mask_width, top + mask_height))

    # Apply mask alpha channel
    mask_alpha = mask.split()[3]
    output = Image.new("RGBA", (mask_width, mask_height), (0, 0, 0, 0))
    output.paste(image, (0, 0))
    output.putalpha(mask_alpha)

    return output


def image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64-encoded PNG string."""
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


async def fetch_image_from_url(url: str) -> BytesIO:
    """Fetch image from URL and return as BytesIO buffer."""
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(
                url,
                follow_redirects=True,
                headers={"User-Agent": "PhotoMaskingAPI/1.0"},
            )
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").split(";")[0]
            if content_type not in ALLOWED_CONTENT_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported content type: {content_type}",
                )

            content_length = response.headers.get("content-length")
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > MAX_IMAGE_SIZE_MB:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Image exceeds maximum size of {MAX_IMAGE_SIZE_MB}MB",
                    )

            return BytesIO(response.content)

    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="Request timed out")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"HTTP error: {e.response.status_code}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Request failed: {str(e)}")


def process_image(image_buffer: BytesIO) -> dict:
    """Apply random mask and return result."""
    mask_path, mask_name = get_random_mask()
    processed_image = apply_mask(image_buffer, mask_path)
    base64_data = image_to_base64(processed_image)

    return {
        "success": True,
        "mask_used": mask_name,
        "image_data": base64_data,
        "content_type": "image/png",
    }


# Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "service": "Photo Masking API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "mask_by_url": "POST /mask-by-url",
            "mask_by_upload": "POST /mask-by-upload",
        },
    }


@app.post("/mask-by-url", response_model=MaskResponse)
async def mask_photo_by_url(
    request: MaskByUrlRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Apply a random mask to an image fetched from a URL.

    The image is cropped to the mask shape, with transparent areas
    of the mask becoming transparent in the output.

    Requires X-API-Key header.
    """
    image_buffer = await fetch_image_from_url(str(request.url))
    result = process_image(image_buffer)
    return MaskResponse(**result)


@app.post("/mask-by-upload", response_model=MaskResponse)
async def mask_photo_by_upload(
    file: UploadFile = File(...),
    _: bool = Depends(verify_api_key)
):
    """
    Apply a random mask to an uploaded image file.

    Accepts: JPEG, PNG, WebP, GIF
    Returns: Base64-encoded PNG with mask applied

    Requires X-API-Key header.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}",
        )

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_IMAGE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"Image exceeds maximum size of {MAX_IMAGE_SIZE_MB}MB",
        )

    image_buffer = BytesIO(contents)
    result = process_image(image_buffer)
    return MaskResponse(**result)
