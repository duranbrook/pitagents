import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.tools.vin_tools import find_vehicle_by_vin


@pytest.mark.asyncio
async def test_find_vehicle_by_vin_returns_vehicle_data():
    mock_db = AsyncMock(spec=AsyncSession)

    vehicle_row = MagicMock()
    vehicle_row.vehicle_id = "aaa-111"
    vehicle_row.customer_id = "ccc-333"
    vehicle_row.year = 2019
    vehicle_row.make = "Honda"
    vehicle_row.model = "Civic"
    vehicle_row.customer_name = "Sarah Chen"

    mock_result = MagicMock()
    mock_result.first.return_value = vehicle_row
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await find_vehicle_by_vin("1HGBH41JXMN109186", mock_db)

    assert result["vehicle_id"] == "aaa-111"
    assert result["customer_name"] == "Sarah Chen"
    assert result["make"] == "Honda"


@pytest.mark.asyncio
async def test_find_vehicle_by_vin_not_found():
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await find_vehicle_by_vin("00000000000000000", mock_db)
    assert "error" in result


@pytest.mark.asyncio
async def test_find_vehicle_by_vin_invalid_vin():
    mock_db = AsyncMock(spec=AsyncSession)
    result = await find_vehicle_by_vin("TOOSHORT", mock_db)
    assert "error" in result
    mock_db.execute.assert_not_called()
