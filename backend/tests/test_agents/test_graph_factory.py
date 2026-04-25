import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_agent_state_has_intent_and_assembled_prompt():
    from src.agents.state import AgentState
    state: AgentState = {
        "messages": [],
        "tool_calls_log": [],
        "stop_reason": "",
        "intent": "QUOTE_BUILD",
        "assembled_prompt": "You are helpful.",
    }
    assert state["intent"] == "QUOTE_BUILD"
    assert state["assembled_prompt"] == "You are helpful."


def test_agent_state_importable():
    from src.agents.state import AgentState
    state: AgentState = {
        "messages": [],
        "tool_calls_log": [],
        "stop_reason": "",
    }
    assert state["messages"] == []
    assert state["tool_calls_log"] == []
    assert state["stop_reason"] == ""


def _make_stream_ctx(text_chunks: list[str], tool_use_blocks: list = None):
    final_content = []
    for chunk in text_chunks:
        block = MagicMock()
        block.type = "text"
        block.text = chunk
        final_content.append(block)

    if tool_use_blocks:
        final_content.extend(tool_use_blocks)

    stop_reason = "tool_use" if tool_use_blocks else "end_turn"

    final_msg = MagicMock()
    final_msg.content = final_content
    final_msg.stop_reason = stop_reason

    async def _text_stream():
        for chunk in text_chunks:
            yield chunk

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=ctx)
    ctx.__aexit__ = AsyncMock(return_value=False)
    ctx.text_stream = _text_stream()
    ctx.get_final_message = AsyncMock(return_value=final_msg)
    return ctx


def _make_tool_use_block(name: str, tool_id: str, inp: dict):
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.id = tool_id
    block.input = inp
    return block


@pytest.mark.asyncio
async def test_factory_streams_tokens():
    """Graph emits token events for each text chunk."""
    from src.agents.graph_factory import build_react_graph

    ctx = _make_stream_ctx(["Hello", " world"])
    graph = build_react_graph("Be helpful.", [], None)

    events = []
    with patch("src.agents.graph_factory._anthropic_client") as mock_client:
        mock_client.messages.stream.return_value = ctx
        async for event in graph.astream(
            {"messages": [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
             "tool_calls_log": [], "stop_reason": ""},
            stream_mode="custom",
        ):
            events.append(event)

    token_events = [e for e in events if e.get("type") == "token"]
    assert [e["content"] for e in token_events] == ["Hello", " world"]
    done_events = [e for e in events if e.get("type") == "done"]
    assert len(done_events) == 1
    assert done_events[0]["tool_calls"] == []


@pytest.mark.asyncio
async def test_factory_executes_tool_and_loops():
    """Graph calls executor, emits tool_start/tool_end, then loops back to LLM."""
    from src.agents.graph_factory import build_react_graph

    tool_block = _make_tool_use_block("lookup_vin", "toolu_01", {"vin": "2HGFB2F59DH123456"})
    first_ctx = _make_stream_ctx([], tool_use_blocks=[tool_block])
    second_ctx = _make_stream_ctx(["2019 Honda Civic"])

    call_count = 0

    def _stream_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        return first_ctx if call_count == 1 else second_ctx

    async def fake_executor(name: str, inp: dict, db) -> dict:
        return {"make": "Honda", "year": "2019"}

    graph = build_react_graph(
        "Be helpful.",
        [{"name": "lookup_vin", "input_schema": {"type": "object", "properties": {}}}],
        fake_executor,
    )

    events = []
    with patch("src.agents.graph_factory._anthropic_client") as mock_client:
        mock_client.messages.stream.side_effect = _stream_side_effect
        async for event in graph.astream(
            {"messages": [{"role": "user", "content": [{"type": "text", "text": "What car?"}]}],
             "tool_calls_log": [], "stop_reason": ""},
            config={"configurable": {"db": None}},
            stream_mode="custom",
        ):
            events.append(event)

    assert call_count == 2
    assert any(e.get("type") == "tool_start" and e["tool"] == "lookup_vin" for e in events)
    assert any(e.get("type") == "tool_end" and e["tool"] == "lookup_vin" for e in events)
    assert any(e.get("type") == "token" and e["content"] == "2019 Honda Civic" for e in events)
    done = next(e for e in events if e.get("type") == "done")
    assert len(done["tool_calls"]) == 1
    assert done["tool_calls"][0]["name"] == "lookup_vin"
    assert done["tool_calls"][0]["output"] == {"make": "Honda", "year": "2019"}
