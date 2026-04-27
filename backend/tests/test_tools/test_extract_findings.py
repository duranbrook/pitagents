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
            {"part": "brake pads", "severity": "high", "notes": "Down to 2mm", "photo_url": None},
            {"part": "engine oil", "severity": "medium", "notes": "1 quart low", "photo_url": None},
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
    assert "photo_url" in result["findings"][0]
    mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_extract_with_photos_includes_photo_urls():
    """When photos are provided, the prompt includes their URLs and Claude can assign them to findings."""
    photo_url = "https://s3.example.com/session/photo1.jpg"
    expected = {
        "summary": "Brake rotor is visibly scored.",
        "findings": [
            {
                "part": "brake rotor",
                "severity": "high",
                "notes": "Deep scoring visible in photo",
                "photo_url": photo_url,
            }
        ],
    }

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(expected))]

    mock_create = MagicMock(return_value=mock_message)
    mock_client = MagicMock()
    mock_client.messages.create = mock_create

    with patch("src.tools.extract_findings._client", mock_client):
        result = await extract_repair_findings(
            "Brake rotor is scored.",
            image_urls=[photo_url],
        )

    assert result["findings"][0]["photo_url"] == photo_url
    # Verify the prompt included the URL list
    call_args = mock_create.call_args
    text_content = next(
        block["text"]
        for block in call_args.kwargs["messages"][0]["content"]
        if block["type"] == "text"
    )
    assert photo_url in text_content


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
