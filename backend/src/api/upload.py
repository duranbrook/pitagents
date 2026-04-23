import uuid
import aioboto3
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from pydantic import BaseModel
from src.api.deps import get_current_user
from src.config import settings

router = APIRouter(prefix="/upload", tags=["upload"])

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/heic"}


class UploadResponse(BaseModel):
    image_url: str


@router.post("", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    _: dict = Depends(get_current_user),
):
    """Upload an image to S3/R2 and return its public URL."""
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

    key = f"chat-uploads/{uuid.uuid4()}/{file.filename}"

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY.get_secret_value() or None,
        region_name=settings.AWS_REGION,
    ) as s3:
        try:
            await s3.put_object(
                Bucket=settings.S3_BUCKET,
                Key=key,
                Body=data,
                ContentType=file.content_type,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Upload failed: {exc}",
            ) from exc

    base = settings.S3_ENDPOINT_URL.rstrip("/") if settings.S3_ENDPOINT_URL else "https://s3.amazonaws.com"
    image_url = f"{base}/{settings.S3_BUCKET}/{key}"
    return UploadResponse(image_url=image_url)
