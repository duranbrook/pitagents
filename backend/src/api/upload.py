import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from pydantic import BaseModel
from src.api.deps import get_current_user
from src.storage.s3 import StorageService

router = APIRouter(prefix="/upload", tags=["upload"])

_storage = StorageService()

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class UploadResponse(BaseModel):
    image_url: str


@router.post("", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    _: dict = Depends(get_current_user),
):
    """Upload an image to S3/R2 and return a presigned URL."""
    if not file.content_type or file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type. Allowed: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}",
        )

    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Image too large (max 10 MB)",
        )

    # Derive extension from content_type to avoid using attacker-controlled filename
    ext = CONTENT_TYPE_EXT.get(file.content_type, "")
    key = f"chat-uploads/{uuid.uuid4()}{ext}"

    try:
        await _storage.upload(data, key, file.content_type)
        image_url = await _storage.presigned_url(key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upload failed: {exc}",
        ) from exc

    return UploadResponse(image_url=image_url)
