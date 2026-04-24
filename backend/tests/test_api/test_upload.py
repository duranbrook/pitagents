import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from src.api.main import app
from src.api.upload import _storage as _storage_ref


@pytest.mark.asyncio
async def test_upload_image_returns_url(auth_headers):
    fake_image = b"\x89PNG\r\n..."

    with patch.object(_storage_ref, "upload", new_callable=AsyncMock) as mock_upload, \
         patch.object(_storage_ref, "presigned_url", new_callable=AsyncMock,
                      return_value="https://test.r2.dev/chat-uploads/abc.png") as mock_url:

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/upload",
                files={"file": ("photo.png", fake_image, "image/png")},
                headers=auth_headers,
            )

    assert resp.status_code == 200
    assert resp.json()["image_url"] == "https://test.r2.dev/chat-uploads/abc.png"
    mock_upload.assert_called_once()
    mock_url.assert_called_once()


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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/upload",
            files={"file": ("big.png", oversized, "image/png")},
            headers=auth_headers,
        )
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_upload_storage_failure_returns_502(auth_headers):
    fake_image = b"\x89PNG\r\n..."
    with patch("src.api.upload._storage.upload", new_callable=AsyncMock,
               side_effect=Exception("S3 error")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/upload",
                files={"file": ("photo.png", fake_image, "image/png")},
                headers=auth_headers,
            )
    assert resp.status_code == 502
