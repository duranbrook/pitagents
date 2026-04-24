import logging

from deepgram import AsyncDeepgramClient
from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from src.api.deps import get_current_user
from src.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transcribe", tags=["transcribe"])

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB

ALLOWED_MIMETYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/x-m4a",
}

_client = AsyncDeepgramClient(api_key=settings.DEEPGRAM_API_KEY.get_secret_value())


class TranscribeResponse(BaseModel):
    transcript: str


@router.post("", response_model=TranscribeResponse)
async def transcribe_audio(
    request: Request,
    _: dict = Depends(get_current_user),
):
    """Accept raw audio bytes (WebM/Opus or M4A), return transcript."""
    audio_bytes = await request.body()
    if not audio_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No audio data")

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file too large (max 25 MB)",
        )

    content_type = request.headers.get("content-type", "audio/webm").split(";")[0].strip()
    if content_type not in ALLOWED_MIMETYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported media type: {content_type}",
        )

    try:
        response = await _client.listen.v1.media.transcribe_file(
            request=audio_bytes,
            model="nova-3",
            smart_format=True,
            punctuate=True,
            language="en-US",
        )
    except Exception as exc:
        logger.exception("Deepgram transcription failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Transcription failed: {exc}",
        ) from exc

    try:
        transcript = response.results.channels[0].alternatives[0].transcript
    except (IndexError, AttributeError):
        transcript = ""

    return TranscribeResponse(transcript=transcript)
