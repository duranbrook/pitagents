import pytest
from unittest.mock import patch, AsyncMock
from src.agents.tools.vin_tools import lookup_vin, extract_vin_from_image
from src.agents.tools.shop_tools import list_sessions, get_session_detail

@pytest.mark.asyncio
async def test_lookup_vin_returns_vehicle_info():
    with patch("src.agents.tools.vin_tools.lookup_vehicle_by_vin", new_callable=AsyncMock) as mock:
        mock.return_value = {"vin": "2HGFB2F59DH123456", "year": "2019", "make": "Honda", "model": "Civic", "trim": "EX"}
        result = await lookup_vin("2HGFB2F59DH123456")
    assert result["make"] == "Honda"
    assert result["year"] == "2019"

@pytest.mark.asyncio
async def test_lookup_vin_invalid_returns_error():
    result = await lookup_vin("TOOSHORT")
    assert "error" in result

@pytest.mark.asyncio
async def test_extract_vin_from_image_calls_vision():
    with patch("src.agents.tools.vin_tools.extract_vin_from_frames", new_callable=AsyncMock) as mock:
        mock.return_value = "1HGBH41JXMN109186"
        result = await extract_vin_from_image("https://example.com/photo.jpg")
    assert result["vin"] == "1HGBH41JXMN109186"

@pytest.mark.asyncio
async def test_list_sessions_returns_list():
    from unittest.mock import MagicMock
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)
    result = await list_sessions(mock_db)
    assert isinstance(result, list)
