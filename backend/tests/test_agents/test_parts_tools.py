import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_hit(part_number: str, description: str, brand: str, unit_price: float, score: float = 0.95):
    hit = MagicMock()
    hit.score = score
    hit.payload = {
        "part_number": part_number,
        "description": description,
        "brand": brand,
        "category": "Brakes",
        "unit_price": unit_price,
    }
    return hit


@pytest.mark.asyncio
async def test_semantic_parts_search_returns_qdrant_results():
    from src.agents.tools.parts_tools import semantic_parts_search

    with patch("src.agents.tools.parts_tools.embed", new=AsyncMock(return_value=[0.1] * 1536)), \
         patch("src.agents.tools.parts_tools.qdrant") as mock_qdrant:
        mock_qdrant.search = AsyncMock(return_value=[
            _make_hit("BP-F-001", "Front Brake Pads", "Bosch", 89.99),
        ])
        result = await semantic_parts_search("front brake pads")

    assert len(result["results"]) == 1
    assert result["results"][0]["part_number"] == "BP-F-001"
    assert result["results"][0]["unit_price"] == 89.99


@pytest.mark.asyncio
async def test_semantic_parts_search_filters_by_make():
    from src.agents.tools.parts_tools import semantic_parts_search

    with patch("src.agents.tools.parts_tools.embed", new=AsyncMock(return_value=[0.1] * 1536)), \
         patch("src.agents.tools.parts_tools.qdrant") as mock_qdrant:
        mock_qdrant.search = AsyncMock(return_value=[])
        await semantic_parts_search("oil filter", make="BMW")
        call_kwargs = mock_qdrant.search.call_args.kwargs
        assert call_kwargs["query_filter"] is not None


@pytest.mark.asyncio
async def test_semantic_parts_search_falls_back_to_catalog_on_qdrant_failure():
    from src.agents.tools.parts_tools import semantic_parts_search

    with patch("src.agents.tools.parts_tools.embed", side_effect=Exception("down")), \
         patch("src.agents.tools.parts_tools.qdrant") as mock_qdrant:
        mock_qdrant.search = AsyncMock(side_effect=Exception("down"))
        result = await semantic_parts_search("brake pads")

    # Falls back to in-memory PARTS_CATALOG
    assert len(result["results"]) >= 1
    assert result["results"][0]["part_number"] in ("BP-F-001", "BP-R-001")


@pytest.mark.asyncio
async def test_semantic_parts_search_no_results_returns_empty():
    from src.agents.tools.parts_tools import semantic_parts_search

    with patch("src.agents.tools.parts_tools.embed", new=AsyncMock(return_value=[0.1] * 1536)), \
         patch("src.agents.tools.parts_tools.qdrant") as mock_qdrant:
        mock_qdrant.search = AsyncMock(return_value=[])
        result = await semantic_parts_search("unobtainium widget xyz")

    assert result["results"] == []
