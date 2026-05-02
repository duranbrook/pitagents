import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from src.api.main import app


@pytest.mark.asyncio
async def test_upload_video_returns_video_url(auth_headers):
    fake_video = b"\x00\x00\x00\x18ftypmp42"  # minimal MP4 header
    with patch("src.api.upload.storage.upload", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = "https://bucket.s3.amazonaws.com/videos/test.mp4"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/upload/video",
                files={"file": ("clip.mp4", fake_video, "video/mp4")},
                headers=auth_headers,
            )
    assert resp.status_code == 200
    assert resp.json()["video_url"].startswith("https://")


@pytest.mark.asyncio
async def test_upload_video_rejects_non_video(auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/upload/video",
            files={"file": ("image.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            headers=auth_headers,
        )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_video_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/upload/video",
            files={"file": ("clip.mp4", b"\x00\x00", "video/mp4")},
        )
    assert resp.status_code == 401
