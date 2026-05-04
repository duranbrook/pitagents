import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from src.agents.tools.report_tools import create_report, add_report_item, list_report_items


@pytest.mark.asyncio
async def test_create_report_invalid_vehicle_id():
    db = AsyncMock()
    result = await create_report("not-a-uuid", db)
    assert "error" in result


@pytest.mark.asyncio
async def test_create_report_vehicle_not_found():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    result = await create_report(str(uuid.uuid4()), db)
    assert "error" in result


@pytest.mark.asyncio
async def test_add_report_item_invalid_report_id():
    db = AsyncMock()
    result = await add_report_item("not-a-uuid", "Brake job", 1.5, 120.0, 89.99, db)
    assert "error" in result


@pytest.mark.asyncio
async def test_list_report_items_invalid_report_id():
    db = AsyncMock()
    result = await list_report_items("not-a-uuid", db)
    assert "error" in result
