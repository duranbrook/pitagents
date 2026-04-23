from deepgram import AsyncDeepgramClient
from fastapi import APIRouter, Request, Depends, HTTPException
from src.api.deps import get_current_user
from src.config import settings

router = APIRouter(prefix="/transcribe", tags=["transcribe"])


@router.post("")
async def transcribe_audio(
    request: Request,
    _: dict = Depends(get_current_user),
):
    """Accept raw audio bytes (WebM/Opus or M4A), return transcript."""
    audio_bytes = await request.body()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio data")

    content_type = request.headers.get("content-type", "audio/webm")
    client = AsyncDeepgramClient(api_key=settings.DEEPGRAM_API_KEY.get_secret_value())

    try:
        response = await client.listen.v1.media.transcribe_raw(
            audio=audio_bytes,
            mimetype=content_type,
            model="nova-3",
            smart_format=True,
            punctuate=True,
            language="en-US",
        )
        transcript = response.results.channels[0].alternatives[0].transcript
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}")

    return {"transcript": transcript}
