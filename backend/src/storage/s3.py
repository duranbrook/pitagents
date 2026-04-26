import asyncio
import logging
import os

import aioboto3

from src.config import settings

logger = logging.getLogger(__name__)


def _s3_configured() -> bool:
    return bool(
        settings.AWS_ACCESS_KEY_ID
        and settings.AWS_SECRET_ACCESS_KEY.get_secret_value()
        and settings.S3_BUCKET
    )


class StorageService:
    """Async S3/R2 storage service using aioboto3.

    Falls back to local /tmp storage when S3 credentials are not configured so
    the app remains functional in dev / demo deployments without object storage.
    """

    def _make_session(self) -> aioboto3.Session:
        return aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY.get_secret_value(),
            region_name=settings.AWS_REGION,
        )

    def _client_kwargs(self) -> dict:
        kwargs: dict = {"service_name": "s3"}
        if settings.S3_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
        return kwargs

    async def upload(self, data: bytes, key: str, content_type: str) -> str:
        """Upload bytes to S3/R2 and return the object URL.

        When S3 is not configured, writes to /tmp and returns a local path so
        callers never receive a 500 due to missing credentials.
        """
        if not _s3_configured():
            return await self._upload_local(data, key)

        try:
            session = self._make_session()
            async with session.client(**self._client_kwargs()) as client:
                await client.put_object(
                    Bucket=settings.S3_BUCKET,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                )
            region = settings.AWS_REGION or "us-east-1"
            if settings.S3_ENDPOINT_URL:
                return f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET}/{key}"
            return f"https://{settings.S3_BUCKET}.s3.{region}.amazonaws.com/{key}"
        except Exception as exc:
            logger.warning("S3 upload failed (%s); falling back to local storage", exc)
            return await self._upload_local(data, key)

    async def presigned_url(self, key: str, expires: int = 86400 * 30) -> str:
        """Generate a presigned GET URL for the given key.

        Returns a local file path when S3 is not configured.
        """
        if not _s3_configured():
            return f"local://{key}"

        session = self._make_session()
        async with session.client(**self._client_kwargs()) as client:
            url: str = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.S3_BUCKET, "Key": key},
                ExpiresIn=expires,
            )
        return url

    @staticmethod
    async def _upload_local(data: bytes, key: str) -> str:
        """Write bytes to /tmp and return a local:// URI."""
        safe_key = key.replace("/", "_")
        path = f"/tmp/{safe_key}"
        await asyncio.to_thread(lambda: open(path, "wb").write(data))
        logger.info("StorageService: saved %d bytes to %s", len(data), path)
        return f"local://{key}"
