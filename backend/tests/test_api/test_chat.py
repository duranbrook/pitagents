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
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/chat/assistant/history", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_chat_message_streams_sse(auth_headers):
    """POST /chat/assistant/message returns SSE with token + done events."""
    mock_graph = MagicMock()

    async def fake_astream(*args, **kwargs):
        yield {"type": "token", "content": "Hello"}
        yield {"type": "done", "tool_calls": [], "_messages": [
            {"role": "user", "content": [{"type": "text", "text": "Hi"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Hello"}]},
        ]}

    mock_graph.astream = fake_astream

    mock_db = _make_mock_db()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch.dict("src.api.chat.AGENT_GRAPHS", {"assistant": mock_graph}), \
             patch("src.api.chat.AsyncSessionLocal") as mock_session_factory:
            mock_save_db = AsyncMock()
            mock_save_db.add = MagicMock()
            mock_save_db.commit = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_save_db)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

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


@pytest.mark.asyncio
async def test_save_messages_uses_user_content_not_thread_position():
    """_save_messages must use user_content arg, not final_messages[-2] (which is wrong when tools used)."""
    import uuid as _uuid
    from src.api.chat import _save_messages

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    user_id = _uuid.UUID("00000000-0000-0000-0000-000000000001")
    user_content = [{"type": "text", "text": "What car is this?"}]

    # final_messages simulates a thread with tool calls: user -> tool_use -> tool_result -> final_assistant
    final_messages = [
        {"role": "user", "content": user_content},
        {"role": "assistant", "content": [{"type": "tool_use", "name": "lookup_vin"}]},
        {"role": "user", "content": [{"type": "tool_result", "content": "Honda"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "It's a Honda Civic"}]},
    ]
    tool_calls = [{"name": "lookup_vin", "input": {}, "output": {}}]

    await _save_messages(user_id, "assistant", user_content, final_messages, tool_calls, mock_db)

    assert mock_db.add.call_count == 2
    calls = mock_db.add.call_args_list
    saved_user = calls[0][0][0]
    saved_assistant = calls[1][0][0]

    assert saved_user.role == "user"
    assert saved_user.content == user_content  # Must be the ORIGINAL user content
    assert saved_assistant.role == "assistant"
    assert saved_assistant.content == [{"type": "text", "text": "It's a Honda Civic"}]
    assert saved_assistant.tool_calls == tool_calls
