from deepgram import AsyncDeepgramClient

from src.config import settings

# Module-level client (created once)
_client = AsyncDeepgramClient(api_key=settings.DEEPGRAM_API_KEY.get_secret_value())


async def extract_audio_transcript(audio_url: str) -> str:
    """Transcribe audio at the given URL using Deepgram Nova-3.

    Returns the transcript as a string, or "" if no speech is detected
    or the response structure is unexpected.
    """
    try:
        response = await _client.listen.v1.media.transcribe_url(
            url=audio_url,
            model="nova-3",
            smart_format=True,
            punctuate=True,
            language="en-US",
        )
    except Exception as exc:
        raise RuntimeError(f"Deepgram transcription failed: {exc}") from exc
    try:
        return response.results.channels[0].alternatives[0].transcript
    except (IndexError, AttributeError):
        return ""
