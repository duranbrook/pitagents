import base64
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from pydantic import BaseModel
from src.api.deps import get_current_user

router = APIRouter(prefix="/upload", tags=["upload"])

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB — keep base64 payload reasonable
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class UploadResponse(BaseModel):
    image_url: str


@router.post("", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    _: dict = Depends(get_current_user),
):
    """Encode an uploaded image as a base64 data URL for use in chat messages."""
    if not file.content_type or file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type. Allowed: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}",
        )

    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Image too large (max 5 MB)",
        )

    encoded = base64.b64encode(data).decode()
    image_url = f"data:{file.content_type};base64,{encoded}"
    return UploadResponse(image_url=image_url)
