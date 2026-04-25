import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_haiku_response(text: str):
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


@pytest.mark.asyncio
async def test_classify_intent_returns_matching_label():
    from src.agents.nodes.classify_intent import make_classify_intent_node
    from src.agents.state import AgentState

    node = make_classify_intent_node(["VIN_LOOKUP", "QUOTE_BUILD", "GENERAL"])
    state: AgentState = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": "Look up VIN 1HGBH41J"}]}],
        "tool_calls_log": [],
        "stop_reason": "",
        "intent": "",
        "assembled_prompt": "",
    }

    with patch("src.agents.nodes.classify_intent.client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=_make_haiku_response("VIN_LOOKUP"))
        result = await node(state, lambda e: None, {})

    assert result["intent"] == "VIN_LOOKUP"


@pytest.mark.asyncio
async def test_classify_intent_falls_back_to_general_on_unknown_label():
    from src.agents.nodes.classify_intent import make_classify_intent_node
    from src.agents.state import AgentState

    node = make_classify_intent_node(["VIN_LOOKUP", "GENERAL"])
    state: AgentState = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        "tool_calls_log": [],
        "stop_reason": "",
        "intent": "",
        "assembled_prompt": "",
    }

    with patch("src.agents.nodes.classify_intent.client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=_make_haiku_response("UNKNOWN_LABEL"))
        result = await node(state, lambda e: None, {})

    assert result["intent"] == "GENERAL"


@pytest.mark.asyncio
async def test_classify_intent_falls_back_on_exception():
    from src.agents.nodes.classify_intent import make_classify_intent_node
    from src.agents.state import AgentState

    node = make_classify_intent_node(["VIN_LOOKUP", "GENERAL"])
    state: AgentState = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        "tool_calls_log": [],
        "stop_reason": "",
        "intent": "",
        "assembled_prompt": "",
    }

    with patch("src.agents.nodes.classify_intent.client") as mock_client:
        mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))
        result = await node(state, lambda e: None, {})

    assert result["intent"] == "GENERAL"


@pytest.mark.asyncio
async def test_classify_intent_no_user_message():
    from src.agents.nodes.classify_intent import make_classify_intent_node
    from src.agents.state import AgentState

    node = make_classify_intent_node(["VIN_LOOKUP", "GENERAL"])
    state: AgentState = {
        "messages": [],
        "tool_calls_log": [],
        "stop_reason": "",
        "intent": "",
        "assembled_prompt": "",
    }

    with patch("src.agents.nodes.classify_intent.client") as mock_client:
        mock_client.messages.create = AsyncMock()
        result = await node(state, lambda e: None, {})

    mock_client.messages.create.assert_not_called()
    assert result["intent"] == "GENERAL"


@pytest.mark.asyncio
async def test_assemble_prompt_includes_base_and_intent_block():
    from src.agents.nodes.assemble_prompt import make_assemble_prompt_node
    from src.agents.state import AgentState

    blocks = {
        "base": "You are PitAgents.",
        "QUOTE_BUILD": "QUOTING: always call semantic_parts_search first.",
    }
    node = make_assemble_prompt_node(blocks)
    state: AgentState = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": "Build me a quote"}]}],
        "tool_calls_log": [],
        "stop_reason": "",
        "intent": "QUOTE_BUILD",
        "assembled_prompt": "",
    }

    with patch("src.agents.nodes.assemble_prompt.qdrant") as mock_qdrant, \
         patch("src.agents.nodes.assemble_prompt.embed") as mock_embed:
        mock_embed.return_value = [0.1] * 1536
        mock_qdrant.search = AsyncMock(return_value=[])
        result = await node(state, lambda e: None, {})

    assert "You are PitAgents." in result["assembled_prompt"]
    assert "QUOTING:" in result["assembled_prompt"]


@pytest.mark.asyncio
async def test_assemble_prompt_includes_few_shots():
    from src.agents.nodes.assemble_prompt import make_assemble_prompt_node
    from src.agents.state import AgentState

    hit = MagicMock()
    hit.payload = {"question": "How much for brake pads?", "ideal_response": "Let me look that up."}

    blocks = {"base": "You are helpful."}
    node = make_assemble_prompt_node(blocks)
    state: AgentState = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": "brake pads"}]}],
        "tool_calls_log": [],
        "stop_reason": "",
        "intent": "PARTS_LOOKUP",
        "assembled_prompt": "",
    }

    with patch("src.agents.nodes.assemble_prompt.qdrant") as mock_qdrant, \
         patch("src.agents.nodes.assemble_prompt.embed") as mock_embed:
        mock_embed.return_value = [0.1] * 1536
        mock_qdrant.search = AsyncMock(return_value=[hit])
        result = await node(state, lambda e: None, {})

    assert "How much for brake pads?" in result["assembled_prompt"]


@pytest.mark.asyncio
async def test_assemble_prompt_qdrant_failure_does_not_crash():
    from src.agents.nodes.assemble_prompt import make_assemble_prompt_node
    from src.agents.state import AgentState

    blocks = {"base": "You are helpful."}
    node = make_assemble_prompt_node(blocks)
    state: AgentState = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": "help"}]}],
        "tool_calls_log": [],
        "stop_reason": "",
        "intent": "GENERAL",
        "assembled_prompt": "",
    }

    with patch("src.agents.nodes.assemble_prompt.qdrant") as mock_qdrant, \
         patch("src.agents.nodes.assemble_prompt.embed") as mock_embed:
        mock_embed.side_effect = Exception("Qdrant down")
        mock_qdrant.search = AsyncMock(side_effect=Exception("down"))
        result = await node(state, lambda e: None, {})

    assert "You are helpful." in result["assembled_prompt"]
