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
