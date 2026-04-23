import pytest
from unittest.mock import patch, MagicMock, AsyncMock


async def aiter_from(items):
    for item in items:
        yield item


@pytest.mark.asyncio
async def test_stream_yields_token_events():
    from src.agents.base import stream_response

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_stream_ctx.text_stream = aiter_from(["Hello", " world"])

    final_msg = MagicMock()
    final_msg.content = [MagicMock(type="text", text="Hello world")]
    mock_stream_ctx.get_final_message = AsyncMock(return_value=final_msg)

    events = []
    with patch("src.agents.base._anthropic_client") as mock_client:
        mock_client.messages.stream.return_value = mock_stream_ctx
        async for event in stream_response(
            system_prompt="You are helpful.",
            tool_schemas=[],
            tool_executor=None,
            history=[],
            user_content=[{"type": "text", "text": "Hello"}],
        ):
            events.append(event)

    token_events = [e for e in events if e["type"] == "token"]
    assert len(token_events) == 2
    assert token_events[0]["content"] == "Hello"
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 1
