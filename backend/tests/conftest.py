import os
import pytest
from unittest.mock import patch

# Set required env vars before any src module is imported during collection
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_autoshop")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")
os.environ.setdefault("DEEPGRAM_API_KEY", "test-deepgram-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("GEMINI_API_KEY", "test-openai-key")

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
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "+14155238886")
    monkeypatch.setenv("SENDGRID_API_KEY", "test-sg-key")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("GEMINI_API_KEY", "test-openai-key")


@pytest.fixture
def mock_db(mock_settings):
    """AsyncSession mock that returns no rows from any execute() call."""
    from unittest.mock import AsyncMock, MagicMock
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    session.add = MagicMock()  # add() is sync in SQLAlchemy; avoid AsyncMock coroutine warning
    return session


@pytest.fixture
def client(mock_settings, mock_db):
    from fastapi.testclient import TestClient
    from src.api.main import app
    from src.db.base import get_db

    async def _override():
        yield mock_db

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def auth_headers(mock_settings):
    import jwt
    from src.config import settings
    from datetime import datetime, timedelta, timezone
    token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "shop_id": "00000000-0000-0000-0000-000000000099",
            "role": "owner",
            "email": "owner@shop.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}
