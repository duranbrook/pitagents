import pytest
from unittest.mock import MagicMock, patch


FRAME_URLS = ["https://example.com/frame1.jpg"]


def _make_mock_response(text: str) -> MagicMock:
    """Build a mock anthropic response with a single text content block."""
    mock_block = MagicMock()
    mock_block.text = text
    mock_resp = MagicMock()
    mock_resp.content = [mock_block]
    return mock_resp


@pytest.mark.asyncio
async def test_extract_vin_from_frames():
    from src.tools.vision import extract_vin_from_frames

    with patch("src.tools.vision._client.messages.create",
               return_value=_make_mock_response('{"vin": "1HGBH41JXMN109186"}')):
        result = await extract_vin_from_frames(FRAME_URLS)

    assert result == "1HGBH41JXMN109186"


@pytest.mark.asyncio
async def test_read_odometer():
    from src.tools.vision import read_odometer

    with patch("src.tools.vision._client.messages.create",
               return_value=_make_mock_response('{"mileage": 67420}')):
        result = await read_odometer(FRAME_URLS)

    assert result == 67420


@pytest.mark.asyncio
async def test_read_tire_size():
    from src.tools.vision import read_tire_size

    with patch("src.tools.vision._client.messages.create",
               return_value=_make_mock_response('{"tire_size": "215/55R16"}')):
        result = await read_tire_size(FRAME_URLS)

    assert result == "215/55R16"


@pytest.mark.asyncio
async def test_analyze_damage_returns_list():
    from src.tools.vision import analyze_damage

    with patch("src.tools.vision._client.messages.create",
               return_value=_make_mock_response('{"damage": ["Rust on rear quarter panel"]}')):
        result = await analyze_damage(FRAME_URLS)

    assert len(result) == 1


@pytest.mark.asyncio
async def test_lookup_vehicle_invalid_vin_returns_empty():
    from src.tools.vin_lookup import lookup_vehicle_by_vin

    result = await lookup_vehicle_by_vin("INVALID")
    assert result == {}
