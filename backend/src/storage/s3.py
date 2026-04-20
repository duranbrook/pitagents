import aioboto3

from src.config import settings


class StorageService:
    """Async S3/R2 storage service using aioboto3."""

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
        """Upload bytes to S3/R2 and return the object URL as '{bucket}/{key}'."""
        session = self._make_session()
        async with session.client(**self._client_kwargs()) as client:
            await client.put_object(
                Bucket=settings.S3_BUCKET,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        return f"{settings.S3_BUCKET}/{key}"

    async def presigned_url(self, key: str, expires: int = 86400 * 30) -> str:
        """Generate a presigned GET URL for the given key."""
        session = self._make_session()
        async with session.client(**self._client_kwargs()) as client:
            url: str = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.S3_BUCKET, "Key": key},
                ExpiresIn=expires,
            )
        return url
