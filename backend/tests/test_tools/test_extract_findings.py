import json
import pytest
from unittest.mock import MagicMock, patch

import src.tools.extract_findings  # ensure module is loaded before patching
from src.tools.extract_findings import extract_repair_findings


@pytest.mark.asyncio
async def test_extract_returns_structured_findings():
    """Returns parsed JSON with summary and findings when Claude responds with valid JSON."""
    expected = {
        "summary": "Brakes are worn and oil is low.",
        "findings": [
            {"part": "brake pads", "severity": "high", "notes": "Down to 2mm"},
            {"part": "engine oil", "severity": "medium", "notes": "1 quart low"},
        ],
    }

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(expected))]

    mock_create = MagicMock(return_value=mock_message)
    mock_client = MagicMock()
    mock_client.messages.create = mock_create

    with patch("src.tools.extract_findings._client", mock_client):
        result = await extract_repair_findings(
            "Technician noted brakes are worn and oil is low."
        )

    assert result["summary"] == expected["summary"]
    assert len(result["findings"]) == 2
    assert result["findings"][0]["part"] == "brake pads"
    assert result["findings"][1]["severity"] == "medium"
    mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_extract_empty_transcript_returns_empty():
    """Returns empty summary and findings immediately for blank/whitespace transcripts."""
    result = await extract_repair_findings("")
    assert result == {"summary": "", "findings": []}

    result = await extract_repair_findings("   ")
    assert result == {"summary": "", "findings": []}


@pytest.mark.asyncio
async def test_extract_transcript_with_curly_braces_does_not_raise():
    """Transcripts containing { or } must not raise KeyError during prompt formatting."""
    curly_transcript = 'Tech noted part number {ABC-123} and config {"key": "value"}.'

    expected = {
        "summary": "Part noted.",
        "findings": [],
    }

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(expected))]

    mock_create = MagicMock(return_value=mock_message)
    mock_client = MagicMock()
    mock_client.messages.create = mock_create

    with patch("src.tools.extract_findings._client", mock_client):
        result = await extract_repair_findings(curly_transcript)

    # Should not raise; result is either parsed JSON or the fallback dict
    assert isinstance(result, dict)
    assert "summary" in result
    assert "findings" in result
