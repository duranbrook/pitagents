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
