import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_assistant_stream_calls_base():
    from src.agents.assistant import stream_assistant

    events = []
    with patch("src.agents.assistant.stream_response") as mock_stream:
        async def fake_stream(*args, **kwargs):
            yield {"type": "token", "content": "Found: "}
            yield {"type": "done", "tool_calls": [], "_messages": []}
        mock_stream.return_value = fake_stream()

        async for event in stream_assistant(
            history=[],
            user_content=[{"type": "text", "text": "What car is VIN 2HGFB2F59DH123456?"}],
        ):
            events.append(event)

    assert any(e["type"] == "token" for e in events)
    assert any(e["type"] == "done" for e in events)


@pytest.mark.asyncio
async def test_tom_stream_calls_base():
    from src.agents.tom import stream_tom

    mock_db = AsyncMock()
    events = []
    with patch("src.agents.tom.stream_response") as mock_stream:
        async def fake_stream(*args, **kwargs):
            yield {"type": "token", "content": "2 active sessions: "}
            yield {"type": "done", "tool_calls": [], "_messages": []}
        mock_stream.return_value = fake_stream()

        async for event in stream_tom(
            history=[],
            user_content=[{"type": "text", "text": "What jobs are active?"}],
            db=mock_db,
        ):
            events.append(event)

    assert any(e["type"] == "done" for e in events)
