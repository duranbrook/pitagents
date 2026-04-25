import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_stream_ctx(text_chunks):
    async def _text():
        for c in text_chunks:
            yield c

    final_msg = MagicMock()
    final_msg.content = [MagicMock(type="text", text="".join(text_chunks))]
    final_msg.stop_reason = "end_turn"

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=ctx)
    ctx.__aexit__ = AsyncMock(return_value=False)
    ctx.text_stream = _text()
    ctx.get_final_message = AsyncMock(return_value=final_msg)
    return ctx


@pytest.mark.asyncio
async def test_assistant_graph_importable():
    from src.agents.assistant import assistant_graph
    assert callable(getattr(assistant_graph, "astream", None))


@pytest.mark.asyncio
async def test_assistant_graph_streams_events():
    from src.agents.assistant import assistant_graph

    ctx = _make_stream_ctx(["Hello"])
    events = []
    with patch("src.agents.graph_factory._anthropic_client") as mock_client:
        mock_client.messages.stream.return_value = ctx
        async for event in assistant_graph.astream(
            {"messages": [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
             "tool_calls_log": [], "stop_reason": ""},
            config={"configurable": {"db": AsyncMock()}},
            stream_mode="custom",
        ):
            events.append(event)

    assert any(e.get("type") == "token" for e in events)
    assert any(e.get("type") == "done" for e in events)


@pytest.mark.asyncio
async def test_tom_graph_importable():
    from src.agents.tom import tom_graph
    assert callable(getattr(tom_graph, "astream", None))


@pytest.mark.asyncio
async def test_tom_graph_streams_events():
    from src.agents.tom import tom_graph

    ctx = _make_stream_ctx(["2 sessions"])
    events = []
    with patch("src.agents.graph_factory._anthropic_client") as mock_client:
        mock_client.messages.stream.return_value = ctx
        async for event in tom_graph.astream(
            {"messages": [{"role": "user", "content": [{"type": "text", "text": "How many sessions?"}]}],
             "tool_calls_log": [], "stop_reason": ""},
            config={"configurable": {"db": AsyncMock()}},
            stream_mode="custom",
        ):
            events.append(event)

    assert any(e.get("type") == "token" for e in events)
    assert any(e.get("type") == "done" for e in events)
