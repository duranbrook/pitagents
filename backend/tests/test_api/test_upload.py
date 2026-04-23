import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from src.api.main import app


@pytest.mark.asyncio
async def test_upload_image_returns_url(auth_headers):
    fake_image = b"\x89PNG\r\n..."

    mock_s3 = MagicMock()
    mock_s3.__aenter__ = AsyncMock(return_value=mock_s3)
    mock_s3.__aexit__ = AsyncMock(return_value=False)
    mock_s3.put_object = AsyncMock()

    with patch("src.api.upload.aioboto3.Session") as MockSession:
        MockSession.return_value.client.return_value = mock_s3

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/upload",
                files={"file": ("photo.png", fake_image, "image/png")},
                headers=auth_headers,
            )

    assert resp.status_code == 200
    assert "image_url" in resp.json()
    assert resp.json()["image_url"].startswith("https://")


@pytest.mark.asyncio
async def test_upload_requires_auth():
    fake_image = b"\x89PNG\r\n..."
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/upload",
            files={"file": ("photo.png", fake_image, "image/png")},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_rejects_non_image(auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/upload",
            files={"file": ("doc.pdf", b"%PDF...", "application/pdf")},
            headers=auth_headers,
        )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_oversized_image_returns_413(auth_headers):
    oversized = b"x" * (10 * 1024 * 1024 + 1)
    mock_s3 = MagicMock()
    mock_s3.__aenter__ = AsyncMock(return_value=mock_s3)
    mock_s3.__aexit__ = AsyncMock(return_value=False)
    mock_s3.put_object = AsyncMock()

    with patch("src.api.upload.aioboto3.Session") as MockSession:
        MockSession.return_value.client.return_value = mock_s3
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/upload",
                files={"file": ("big.png", oversized, "image/png")},
                headers=auth_headers,
            )
    assert resp.status_code == 413
