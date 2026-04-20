import pytest
from unittest.mock import AsyncMock, patch

from src.tools.estimate import generate_estimate

VEHICLE = {"year": "2019", "make": "Honda", "model": "Civic", "trim": "LX"}
FINDINGS = [
    {"part": "Front brake pads", "severity": "urgent", "notes": "Metal on metal"},
    {"part": "Air filter", "severity": "low", "notes": "Clogged"},
]


@pytest.mark.asyncio
async def test_estimate_shop_flag_uses_labor_rate():
    result = await generate_estimate(
        vehicle=VEHICLE,
        findings=FINDINGS,
        labor_rate=120.0,
        pricing_flag="shop",
    )
    assert "line_items" in result
    assert "total" in result
    assert result["total"] > 0


@pytest.mark.asyncio
async def test_estimate_alldata_flag_calls_alldata():
    with patch(
        "src.tools.estimate.fetch_alldata_estimate", new_callable=AsyncMock
    ) as mock_alldata:
        mock_alldata.return_value = {"line_items": [], "total": 350.0}
        result = await generate_estimate(
            vehicle=VEHICLE,
            findings=FINDINGS,
            labor_rate=120.0,
            pricing_flag="alldata",
            alldata_api_key="test-key",
        )
    mock_alldata.assert_called_once()
    assert result["total"] == 350.0
