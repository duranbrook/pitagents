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


@pytest.mark.asyncio
async def test_stream_executes_tool_call_and_loops():
    """Verify the tool-call loop: Claude requests a tool → executor runs → Claude continues."""
    from src.agents.base import stream_response

    # First turn: Claude requests a tool (no text tokens, one tool_use block)
    tool_use_block = MagicMock()
    tool_use_block.type = "tool_use"
    tool_use_block.name = "lookup_vin"
    tool_use_block.input = {"vin": "2HGFB2F59DH123456"}
    tool_use_block.id = "toolu_01"
    tool_use_block.model_dump = MagicMock(return_value={
        "type": "tool_use", "id": "toolu_01", "name": "lookup_vin",
        "input": {"vin": "2HGFB2F59DH123456"},
    })

    first_final = MagicMock()
    first_final.content = [tool_use_block]

    first_stream = MagicMock()
    first_stream.__aenter__ = AsyncMock(return_value=first_stream)
    first_stream.__aexit__ = AsyncMock(return_value=False)
    first_stream.text_stream = aiter_from([])
    first_stream.get_final_message = AsyncMock(return_value=first_final)

    # Second turn: Claude responds with text after tool result
    text_block = MagicMock()
    text_block.type = "text"
    text_block.model_dump = MagicMock(return_value={"type": "text", "text": "2019 Honda Civic"})

    second_final = MagicMock()
    second_final.content = [text_block]

    second_stream = MagicMock()
    second_stream.__aenter__ = AsyncMock(return_value=second_stream)
    second_stream.__aexit__ = AsyncMock(return_value=False)
    second_stream.text_stream = aiter_from(["2019 Honda Civic"])
    second_stream.get_final_message = AsyncMock(return_value=second_final)

    async def fake_tool_executor(name: str, inp: dict) -> dict:
        return {"make": "Honda", "year": "2019"}

    events = []
    call_count = 0

    def side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        return first_stream if call_count == 1 else second_stream

    with patch("src.agents.base._anthropic_client") as mock_client:
        mock_client.messages.stream.side_effect = side_effect
        async for event in stream_response(
            system_prompt="You are helpful.",
            tool_schemas=[{"name": "lookup_vin", "input_schema": {}}],
            tool_executor=fake_tool_executor,
            history=[],
            user_content=[{"type": "text", "text": "What car is 2HGFB2F59DH123456?"}],
        ):
            events.append(event)

    assert call_count == 2, "Expected two Anthropic API calls (pre-tool and post-tool)"
    assert any(e["type"] == "tool_start" and e["tool"] == "lookup_vin" for e in events)
    assert any(e["type"] == "tool_end" for e in events)
    assert any(e["type"] == "token" and e["content"] == "2019 Honda Civic" for e in events)
    done = next(e for e in events if e["type"] == "done")
    assert len(done["tool_calls"]) == 1
    assert done["tool_calls"][0]["name"] == "lookup_vin"
