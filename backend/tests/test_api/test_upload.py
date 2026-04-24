import base64
import pytest
from httpx import AsyncClient, ASGITransport
from src.api.main import app


@pytest.mark.asyncio
async def test_upload_image_returns_base64_data_url(auth_headers):
    fake_image = b"\x89PNG\r\n\x1a\n"  # minimal PNG header

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/upload",
            files={"file": ("photo.png", fake_image, "image/png")},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    url = resp.json()["image_url"]
    assert url.startswith("data:image/png;base64,")
    decoded = base64.b64decode(url.split(",", 1)[1])
    assert decoded == fake_image


@pytest.mark.asyncio
async def test_upload_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/upload",
            files={"file": ("photo.png", b"\x89PNG\r\n\x1a\n", "image/png")},
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
    oversized = b"x" * (5 * 1024 * 1024 + 1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/upload",
            files={"file": ("big.png", oversized, "image/png")},
            headers=auth_headers,
        )
    assert resp.status_code == 413
