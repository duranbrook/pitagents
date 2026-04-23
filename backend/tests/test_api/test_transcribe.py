import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from src.api.main import app


@pytest.mark.asyncio
async def test_transcribe_returns_transcript(auth_headers):
    fake_audio = b"RIFF....fake webm bytes"
    mock_response = MagicMock()
    mock_response.results.channels[0].alternatives[0].transcript = "front brakes are worn"

    with patch("src.api.transcribe._client") as mock_client:
        mock_client.listen.v1.media.transcribe_raw = AsyncMock(return_value=mock_response)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/transcribe",
                content=fake_audio,
                headers={**auth_headers, "Content-Type": "audio/webm"},
            )

    assert resp.status_code == 200
    assert resp.json() == {"transcript": "front brakes are worn"}


@pytest.mark.asyncio
async def test_transcribe_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/transcribe",
            content=b"fake audio",
            headers={"Content-Type": "audio/webm"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_transcribe_empty_body_returns_400(auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/transcribe",
            content=b"",
            headers={**auth_headers, "Content-Type": "audio/webm"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_transcribe_deepgram_failure_returns_502(auth_headers):
    with patch("src.api.transcribe._client") as mock_client:
        mock_client.listen.v1.media.transcribe_raw = AsyncMock(side_effect=Exception("network error"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/transcribe",
                content=b"fake audio",
                headers={**auth_headers, "Content-Type": "audio/webm"},
            )
    assert resp.status_code == 502
