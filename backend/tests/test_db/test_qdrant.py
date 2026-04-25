import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_embed_returns_list_of_floats():
    mock_result = {"embedding": [0.1, 0.2, 0.3]}

    with patch("src.db.qdrant.genai") as mock_genai:
        with patch("src.db.qdrant.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_result
            from src.db.qdrant import embed
            result = await embed("brake pads")

    assert isinstance(result, list)
    assert result == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_ensure_collections_creates_missing():
    with patch("src.db.qdrant._qdrant") as mock_qdrant:
        mock_qdrant.collection_exists = AsyncMock(return_value=False)
        mock_qdrant.create_collection = AsyncMock()
        from src.db.qdrant import ensure_collections
        await ensure_collections()

    assert mock_qdrant.create_collection.call_count == 3
    call_names = {c.kwargs["collection_name"] for c in mock_qdrant.create_collection.call_args_list}
    assert call_names == {"parts", "few_shots", "feedback_bank"}


@pytest.mark.asyncio
async def test_ensure_collections_skips_existing():
    with patch("src.db.qdrant._qdrant") as mock_qdrant:
        mock_qdrant.collection_exists = AsyncMock(return_value=True)
        mock_qdrant.create_collection = AsyncMock()
        from src.db.qdrant import ensure_collections
        await ensure_collections()

    mock_qdrant.create_collection.assert_not_called()
