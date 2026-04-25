import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_agent_state_importable():
    from src.agents.state import AgentState
    state: AgentState = {
        "messages": [],
        "tool_calls_log": [],
        "stop_reason": "",
        "intent": "",
        "assembled_prompt": "",
    }
    assert state["messages"] == []


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


def _make_haiku_response(text: str):
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


def _build_test_graph(tool_schemas=None, executor=None):
    from src.agents.graph_factory import build_react_graph
    return build_react_graph(
        system_prompt="Be helpful.",
        tool_schemas=tool_schemas or [],
        tool_executor=executor,
        intent_labels=["GENERAL"],
        prompt_blocks={"base": "Be helpful."},
    )


@pytest.mark.asyncio
async def test_factory_streams_tokens():
    """Graph emits token events for each text chunk."""
    ctx = _make_stream_ctx(["Hello", " world"])
    graph = _build_test_graph()

    events = []
    with patch("src.agents.llm.client") as mock_client, \
         patch("src.agents.nodes.classify_intent.client") as mock_haiku_ci, \
         patch("src.agents.nodes.validate_response.client") as mock_haiku_vr, \
         patch("src.agents.nodes.validate_response._feedback_critic", new=AsyncMock(return_value=False)), \
         patch("src.agents.nodes.assemble_prompt.qdrant") as mock_qdrant, \
         patch("src.agents.nodes.assemble_prompt.embed", new=AsyncMock(return_value=[0.1] * 1536)):
        mock_client.messages.stream.return_value = ctx
        mock_haiku_ci.messages.create = AsyncMock(return_value=_make_haiku_response("GENERAL"))
        mock_haiku_vr.messages.create = AsyncMock(return_value=_make_haiku_response("PASS"))
        mock_qdrant.search = AsyncMock(return_value=[])

        async for event in graph.astream(
            {
                "messages": [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
                "tool_calls_log": [],
                "stop_reason": "",
                "intent": "",
                "assembled_prompt": "",
            },
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

    graph = _build_test_graph(
        tool_schemas=[{"name": "lookup_vin", "input_schema": {"type": "object", "properties": {}}}],
        executor=fake_executor,
    )

    events = []
    with patch("src.agents.llm.client") as mock_client, \
         patch("src.agents.nodes.classify_intent.client") as mock_haiku_ci, \
         patch("src.agents.nodes.validate_response.client") as mock_haiku_vr, \
         patch("src.agents.nodes.validate_response._feedback_critic", new=AsyncMock(return_value=False)), \
         patch("src.agents.nodes.assemble_prompt.qdrant") as mock_qdrant, \
         patch("src.agents.nodes.assemble_prompt.embed", new=AsyncMock(return_value=[0.1] * 1536)):
        mock_client.messages.stream.side_effect = _stream_side_effect
        mock_haiku_ci.messages.create = AsyncMock(return_value=_make_haiku_response("GENERAL"))
        mock_haiku_vr.messages.create = AsyncMock(return_value=_make_haiku_response("PASS"))
        mock_qdrant.search = AsyncMock(return_value=[])

        async for event in graph.astream(
            {
                "messages": [{"role": "user", "content": [{"type": "text", "text": "What car?"}]}],
                "tool_calls_log": [],
                "stop_reason": "",
                "intent": "",
                "assembled_prompt": "",
            },
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
