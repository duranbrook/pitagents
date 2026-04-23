import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from src.api.main import app

@pytest.mark.asyncio
async def test_transcribe_returns_transcript(auth_headers):
    fake_audio = b"RIFF....fake webm bytes"
    mock_response = AsyncMock()
    mock_response.results.channels = [
        type("ch", (), {"alternatives": [type("alt", (), {"transcript": "front brakes are worn"})()]})()
    ]

    with patch("src.api.transcribe.AsyncDeepgramClient") as MockClient:
        instance = MockClient.return_value
        instance.listen.v1.media.transcribe_raw = AsyncMock(return_value=mock_response)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/transcribe",
                content=fake_audio,
                headers={**auth_headers, "Content-Type": "audio/webm"},
            )

    assert resp.status_code == 200
    assert resp.json() == {"transcript": "front brakes are worn"}
