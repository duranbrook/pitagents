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


@pytest.mark.asyncio
async def test_validate_response_pass_emits_done():
    from src.agents.nodes.validate_response import make_validate_response_node
    from src.agents.state import AgentState

    node = make_validate_response_node("Be helpful.", [])
    state: AgentState = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "How much are brake pads?"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Brake pads cost $89.99."}]},
        ],
        "tool_calls_log": [],
        "stop_reason": "end_turn",
        "intent": "PARTS_LOOKUP",
        "assembled_prompt": "Be helpful.",
    }

    events = []
    with patch("src.agents.nodes.validate_response.client") as mock_client, \
         patch("src.agents.nodes.validate_response._feedback_critic", new=AsyncMock(return_value=False)):
        mock_client.messages.create = AsyncMock(return_value=_make_haiku_response("PASS"))
        result = await node(state, events.append, {})

    done_events = [e for e in events if e.get("type") == "done"]
    assert len(done_events) == 1
    assert "validation_warning" not in done_events[0]


@pytest.mark.asyncio
async def test_validate_response_fail_retries_and_emits_done():
    from src.agents.nodes.validate_response import make_validate_response_node
    from src.agents.state import AgentState

    node = make_validate_response_node("Be helpful.", [])
    state: AgentState = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "Build a quote"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Total: $500 (items: $100 + $200)."}]},
        ],
        "tool_calls_log": [],
        "stop_reason": "end_turn",
        "intent": "QUOTE_BUILD",
        "assembled_prompt": "Be helpful.",
    }

    corrected_block = MagicMock()
    corrected_block.text = "Corrected: $300 total."
    corrected_resp = MagicMock()
    corrected_resp.content = [corrected_block]

    call_count = 0

    async def mixed_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        # Call 1: QA check → FAIL
        # Call 2: correction LLM call → corrected response
        # Call 3: QA check on corrected → PASS
        if call_count == 1:
            return _make_haiku_response("FAIL: MATH_ERROR")
        elif call_count == 2:
            return corrected_resp
        else:
            return _make_haiku_response("PASS")

    events = []
    with patch("src.agents.nodes.validate_response.client") as mock_client, \
         patch("src.agents.nodes.validate_response._feedback_critic", new=AsyncMock(return_value=False)):
        mock_client.messages.create = AsyncMock(side_effect=mixed_side_effect)
        result = await node(state, events.append, {})

    done_events = [e for e in events if e.get("type") == "done"]
    assert len(done_events) == 1


@pytest.mark.asyncio
async def test_validate_response_double_fail_emits_warning():
    from src.agents.nodes.validate_response import make_validate_response_node
    from src.agents.state import AgentState

    node = make_validate_response_node("Be helpful.", [])
    state: AgentState = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "Build a quote"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Bad response."}]},
        ],
        "tool_calls_log": [],
        "stop_reason": "end_turn",
        "intent": "QUOTE_BUILD",
        "assembled_prompt": "Be helpful.",
    }

    corrected_block = MagicMock()
    corrected_block.text = "Still bad."
    corrected_resp = MagicMock()
    corrected_resp.content = [corrected_block]

    call_count = 0

    async def always_fail(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count in (1, 3):
            return _make_haiku_response("FAIL: INCOHERENT")
        return corrected_resp

    events = []
    with patch("src.agents.nodes.validate_response.client") as mock_client, \
         patch("src.agents.nodes.validate_response._feedback_critic", new=AsyncMock(return_value=False)):
        mock_client.messages.create = AsyncMock(side_effect=always_fail)
        result = await node(state, events.append, {})

    done_events = [e for e in events if e.get("type") == "done"]
    assert len(done_events) == 1
    assert done_events[0].get("validation_warning") is True
