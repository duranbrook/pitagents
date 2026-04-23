import pytest
from unittest.mock import patch, AsyncMock
from src.agents.tools.vin_tools import lookup_vin, extract_vin_from_image
from src.agents.tools.shop_tools import list_sessions, get_session_detail, get_report

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

@pytest.mark.asyncio
async def test_get_session_detail_returns_dict():
    import uuid as _uuid
    from unittest.mock import MagicMock
    from datetime import datetime, timezone
    mock_db = AsyncMock()
    mock_session = MagicMock()
    mock_session.id = _uuid.uuid4()
    mock_session.status = "completed"
    mock_session.vehicle = {"make": "Honda"}
    mock_session.transcript = "Front brakes worn"
    mock_session.created_at = datetime.now(timezone.utc)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_session
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await get_session_detail(mock_db, str(mock_session.id))
    assert result["status"] == "completed"
    assert result["transcript"] == "Front brakes worn"

@pytest.mark.asyncio
async def test_get_session_detail_invalid_uuid_returns_error():
    mock_db = AsyncMock()
    result = await get_session_detail(mock_db, "not-a-uuid")
    assert "error" in result

@pytest.mark.asyncio
async def test_lookup_vin_normalizes_lowercase():
    with patch("src.agents.tools.vin_tools.lookup_vehicle_by_vin", new_callable=AsyncMock) as mock:
        mock.return_value = {"make": "Toyota"}
        result = await lookup_vin("jtdkb20u993461337")  # 17 chars lowercase
    assert result["make"] == "Toyota"
    mock.assert_called_once_with("JTDKB20U993461337")
