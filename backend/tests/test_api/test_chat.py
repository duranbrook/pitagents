import pytest
import json
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.main import app
from src.db.base import get_db


def _make_mock_db():
    """Return a lightweight async mock that satisfies the get_db dependency."""
    mock_db = AsyncMock(spec=AsyncSession)
    # execute() returns a result whose scalars().all() gives an empty list
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    return mock_db


@pytest.mark.asyncio
async def test_chat_history_empty(auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/chat/assistant/history", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_chat_message_streams_sse(auth_headers):
    async def fake_stream(*args, **kwargs):
        yield {"type": "token", "content": "Hello"}
        yield {"type": "done", "tool_calls": [], "_messages": [
            {"role": "user", "content": [{"type": "text", "text": "Hi"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Hello"}]},
        ]}

    mock_db = _make_mock_db()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("src.api.chat.stream_assistant", return_value=fake_stream()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/chat/assistant/message",
                    json={"message": "Hi"},
                    headers=auth_headers,
                )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    lines = [l for l in resp.text.split("\n") if l.startswith("data: ")]
    events = [json.loads(l[6:]) for l in lines]
    assert any(e["type"] == "token" for e in events)
    assert any(e["type"] == "done" for e in events)


@pytest.mark.asyncio
async def test_chat_invalid_agent_returns_404(auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/chat/unknown/message",
            json={"message": "hi"},
            headers=auth_headers,
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_chat_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/chat/assistant/message",
            json={"message": "hi"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_history_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/chat/assistant/history")
    assert resp.status_code == 401
