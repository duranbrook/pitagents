import os
import pytest
from unittest.mock import patch

# Set required env vars before any src module is imported during collection
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_autoshop")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")
os.environ.setdefault("DEEPGRAM_API_KEY", "test-deepgram-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")

from src.config import Settings


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """Prevent tests from loading real .env file or env vars."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_autoshop")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-for-testing-only")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-deepgram-key")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("S3_ENDPOINT_URL", "https://test.r2.cloudflarestorage.com")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key-id")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("AWS_REGION", "auto")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "test-sid")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("TWILIO_FROM_PHONE", "+15555555555")
    monkeypatch.setenv("SENDGRID_API_KEY", "test-sg-key")


@pytest.fixture
def auth_headers():
    import jwt
    from src.config import settings
    from datetime import datetime, timedelta, timezone
    token = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000001", "role": "owner", "email": "owner@shop.com",
         "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}
