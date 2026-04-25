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


def _make_haiku_response(text: str):
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


@pytest.mark.asyncio
async def test_assistant_graph_importable():
    from src.agents.assistant import assistant_graph
    assert callable(getattr(assistant_graph, "astream", None))


@pytest.mark.asyncio
async def test_assistant_graph_streams_events():
    from src.agents.assistant import assistant_graph

    ctx = _make_stream_ctx(["Hello"])
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
        async for event in assistant_graph.astream(
            {
                "messages": [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
                "tool_calls_log": [],
                "stop_reason": "",
                "intent": "",
                "assembled_prompt": "",
            },
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
        async for event in tom_graph.astream(
            {
                "messages": [{"role": "user", "content": [{"type": "text", "text": "How many sessions?"}]}],
                "tool_calls_log": [],
                "stop_reason": "",
                "intent": "",
                "assembled_prompt": "",
            },
            config={"configurable": {"db": AsyncMock()}},
            stream_mode="custom",
        ):
            events.append(event)

    assert any(e.get("type") == "token" for e in events)
    assert any(e.get("type") == "done" for e in events)
