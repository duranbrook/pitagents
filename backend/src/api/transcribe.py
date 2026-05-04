import logging

import httpx
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

DEEPGRAM_URL = (
    "https://api.deepgram.com/v1/listen"
    "?model=nova-2&smart_format=true&punctuate=true&language=en-US"
)


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

    api_key = settings.DEEPGRAM_API_KEY.get_secret_value()
    timeout = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                DEEPGRAM_URL,
                content=audio_bytes,
                headers={
                    "Authorization": f"Token {api_key}",
                    "Content-Type": content_type,
                },
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Transcription timed out — try a shorter recording",
        )
    except Exception as exc:
        logger.exception("Deepgram request failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if resp.status_code != 200:
        logger.error("Deepgram error %s: %s", resp.status_code, resp.text[:200])
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Transcription failed ({resp.status_code})",
        )

    try:
        data = resp.json()
        transcript = data["results"]["channels"][0]["alternatives"][0]["transcript"]
    except (KeyError, IndexError):
        transcript = ""

    return TranscribeResponse(transcript=transcript)
