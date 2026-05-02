import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.tools.quote_tools import create_quote
import uuid


@pytest.mark.asyncio
async def test_create_quote_with_vehicle_id():
    mock_db = AsyncMock(spec=AsyncSession)
    vehicle_id = str(uuid.uuid4())

    fake_quote = MagicMock()
    fake_quote.id = uuid.uuid4()
    fake_quote.status = "draft"

    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("src.agents.tools.quote_tools.Quote") as MockQuote:
        MockQuote.return_value = fake_quote
        result = await create_quote(mock_db, vehicle_id=vehicle_id)

    call_kwargs = MockQuote.call_args.kwargs
    assert str(call_kwargs["vehicle_id"]) == vehicle_id
    assert result["status"] == "draft"


@pytest.mark.asyncio
async def test_create_quote_without_vehicle_id():
    mock_db = AsyncMock(spec=AsyncSession)
    fake_quote = MagicMock()
    fake_quote.id = uuid.uuid4()
    fake_quote.status = "draft"
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("src.agents.tools.quote_tools.Quote") as MockQuote:
        MockQuote.return_value = fake_quote
        result = await create_quote(mock_db)

    call_kwargs = MockQuote.call_args.kwargs
    assert call_kwargs.get("vehicle_id") is None
