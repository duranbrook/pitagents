import base64
import uuid as _uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from pydantic import BaseModel
from src.api.deps import get_current_user
from src.storage.s3 import StorageService

router = APIRouter(prefix="/upload", tags=["upload"])

storage = StorageService()

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB — keep base64 payload reasonable
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-m4v", "video/mpeg"}
MAX_VIDEO_BYTES = 200 * 1024 * 1024  # 200 MB


class UploadResponse(BaseModel):
    image_url: str


class VideoUploadResponse(BaseModel):
    video_url: str


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


@router.post("/video", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    _: dict = Depends(get_current_user),
):
    """Upload a video file to object storage and return the URL."""
    if not file.content_type or file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported video type. Allowed: {', '.join(sorted(ALLOWED_VIDEO_TYPES))}",
        )

    data = await file.read()
    if len(data) > MAX_VIDEO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Video too large (max 200 MB)",
        )

    key = f"videos/{_uuid.uuid4()}.mp4"
    video_url = await storage.upload(data, key, file.content_type)
    return VideoUploadResponse(video_url=video_url)
