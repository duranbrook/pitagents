import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import src.tools.transcribe  # ensure module is loaded before patching
from src.tools.transcribe import extract_audio_transcript


@pytest.mark.asyncio
async def test_extract_audio_transcript_returns_transcript():
    """Returns transcript text when Deepgram responds with speech."""
    mock_response = MagicMock()
    mock_response.results.channels[0].alternatives[0].transcript = "Hello world"

    mock_transcribe_url = AsyncMock(return_value=mock_response)
    mock_client = MagicMock()
    mock_client.listen.v1.media.transcribe_url = mock_transcribe_url

    with patch("src.tools.transcribe.AsyncDeepgramClient", return_value=mock_client):
        result = await extract_audio_transcript("https://example.com/audio.wav")

    assert result == "Hello world"
    mock_transcribe_url.assert_awaited_once_with(
        url="https://example.com/audio.wav",
        model="nova-3",
        smart_format=True,
        punctuate=True,
        language="en-US",
    )


@pytest.mark.asyncio
async def test_extract_audio_transcript_returns_empty_when_no_speech():
    """Returns empty string when channels list is empty (no speech detected)."""
    mock_response = MagicMock()
    mock_response.results.channels = []

    mock_transcribe_url = AsyncMock(return_value=mock_response)
    mock_client = MagicMock()
    mock_client.listen.v1.media.transcribe_url = mock_transcribe_url

    with patch("src.tools.transcribe.AsyncDeepgramClient", return_value=mock_client):
        result = await extract_audio_transcript("https://example.com/silence.wav")

    assert result == ""
