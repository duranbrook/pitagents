import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock


def test_rate_message_invalid_rating_returns_400(client, auth_headers):
    resp = client.post(
        "/chat/assistant/feedback",
        json={"message_id": str(uuid.uuid4()), "rating": 99},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_rate_message_invalid_uuid_returns_400(client, auth_headers):
    resp = client.post(
        "/chat/assistant/feedback",
        json={"message_id": "not-a-uuid", "rating": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_rate_message_wrong_owner_returns_403(client, auth_headers):
    """Users can only rate their own messages — rating another user's message returns 403."""
    from unittest.mock import MagicMock, AsyncMock
    import uuid
    from src.models.chat_message import ChatMessage

    msg_id = str(uuid.uuid4())
    # Message owned by a DIFFERENT user (not the auth_headers user 00000000-0000-0000-0000-000000000001)
    fake_msg = MagicMock(spec=ChatMessage)
    fake_msg.id = uuid.UUID(msg_id)
    fake_msg.user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")  # different user
    fake_msg.role = "assistant"
    fake_msg.content = [{"type": "text", "text": "Some response."}]

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_msg

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    from src.api.main import app
    from src.db.base import get_db
    from fastapi.testclient import TestClient

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        test_client = TestClient(app)
        resp = test_client.post(
            "/chat/assistant/feedback",
            json={"message_id": msg_id, "rating": 1},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 403
