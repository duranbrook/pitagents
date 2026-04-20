import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.storage.s3 import StorageService


def make_mock_session(mock_client):
    """Return a mock aioboto3 Session that yields mock_client as the async context manager."""
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    return mock_session


def make_mock_client():
    """Return an async-context-manager-compatible mock S3 client."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.mark.asyncio
async def test_upload_returns_url_containing_key():
    """upload() should return a URL in the format '{bucket}/{key}'."""
    mock_client = make_mock_client()
    mock_client.put_object = AsyncMock(return_value={})
    mock_session = make_mock_session(mock_client)

    with (
        patch("aioboto3.Session", return_value=mock_session),
        patch("src.storage.s3.settings") as mock_settings,
    ):
        mock_settings.S3_BUCKET = "test-bucket"
        mock_settings.S3_ENDPOINT_URL = "https://test.r2.cloudflarestorage.com"
        mock_settings.AWS_ACCESS_KEY_ID = "test-key-id"
        mock_settings.AWS_SECRET_ACCESS_KEY.get_secret_value.return_value = "test-secret"

        service = StorageService()
        url = await service.upload(
            data=b"fake image bytes",
            key="inspections/123/photo.jpg",
            content_type="image/jpeg",
        )

    assert "inspections/123/photo.jpg" in url


@pytest.mark.asyncio
async def test_upload_calls_put_object_with_correct_args():
    """upload() should call put_object with the right bucket, key, body, and content type."""
    mock_client = make_mock_client()
    mock_client.put_object = AsyncMock(return_value={})
    mock_session = make_mock_session(mock_client)

    with (
        patch("aioboto3.Session", return_value=mock_session),
        patch("src.storage.s3.settings") as mock_settings,
    ):
        mock_settings.S3_BUCKET = "test-bucket"
        mock_settings.S3_ENDPOINT_URL = "https://test.r2.cloudflarestorage.com"
        mock_settings.AWS_ACCESS_KEY_ID = "test-key-id"
        mock_settings.AWS_SECRET_ACCESS_KEY.get_secret_value.return_value = "test-secret"

        service = StorageService()
        await service.upload(
            data=b"content",
            key="reports/abc.pdf",
            content_type="application/pdf",
        )

    mock_client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="reports/abc.pdf",
        Body=b"content",
        ContentType="application/pdf",
    )


@pytest.mark.asyncio
async def test_presigned_url_returns_signed_url():
    """presigned_url() should return the URL produced by generate_presigned_url."""
    expected_url = "https://test.r2.cloudflarestorage.com/test-bucket/key.jpg?sig=abc"
    mock_client = make_mock_client()
    mock_client.generate_presigned_url = AsyncMock(return_value=expected_url)
    mock_session = make_mock_session(mock_client)

    with (
        patch("aioboto3.Session", return_value=mock_session),
        patch("src.storage.s3.settings") as mock_settings,
    ):
        mock_settings.S3_BUCKET = "test-bucket"
        mock_settings.S3_ENDPOINT_URL = "https://test.r2.cloudflarestorage.com"
        mock_settings.AWS_ACCESS_KEY_ID = "test-key-id"
        mock_settings.AWS_SECRET_ACCESS_KEY.get_secret_value.return_value = "test-secret"

        service = StorageService()
        url = await service.presigned_url(key="key.jpg")

    assert url == expected_url


@pytest.mark.asyncio
async def test_presigned_url_calls_generate_with_correct_params():
    """presigned_url() should call generate_presigned_url with correct bucket/key/expiry."""
    expected_url = "https://example.com/signed"
    mock_client = make_mock_client()
    mock_client.generate_presigned_url = AsyncMock(return_value=expected_url)
    mock_session = make_mock_session(mock_client)

    with (
        patch("aioboto3.Session", return_value=mock_session),
        patch("src.storage.s3.settings") as mock_settings,
    ):
        mock_settings.S3_BUCKET = "test-bucket"
        mock_settings.S3_ENDPOINT_URL = "https://test.r2.cloudflarestorage.com"
        mock_settings.AWS_ACCESS_KEY_ID = "test-key-id"
        mock_settings.AWS_SECRET_ACCESS_KEY.get_secret_value.return_value = "test-secret"

        service = StorageService()
        await service.presigned_url(key="docs/report.pdf", expires=3600)

    mock_client.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": "test-bucket", "Key": "docs/report.pdf"},
        ExpiresIn=3600,
    )
