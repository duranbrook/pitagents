"""Tests for quote tool functions."""
import os
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.agents.tools.quote_tools import (
    lookup_part_price,
    estimate_labor,
    create_quote,
    create_quote_item,
    list_quote_items,
    finalize_quote,
    TEST_SHOP_ID,
    FALLBACK_LABOR_RATE,
)
from src.db.base import Base

TEST_DB = os.environ["DATABASE_URL"]


# ---------------------------------------------------------------------------
# DB fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session():
    """Provide an async DB session with a test shop row."""
    engine = create_async_engine(TEST_DB)
    shop_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        await s.execute(
            text(
                "INSERT INTO shops (id, name, labor_rate, pricing_flag) "
                "VALUES (:id, :name, 95.00, :flag)"
            ),
            {"id": str(shop_id), "name": f"Test Shop {shop_id}", "flag": "shop"},
        )
        await s.commit()

        s.info["shop_id"] = shop_id
        yield s

        # Cleanup: quotes don't have FK to shop, just delete shop
        await s.execute(text("DELETE FROM shops WHERE id = :sid"), {"sid": str(shop_id)})
        await s.commit()

    await engine.dispose()


@pytest.fixture
async def db_session_with_test_shop():
    """Provide a DB session that includes the hard-coded TEST_SHOP_ID row used by estimate_labor."""
    engine = create_async_engine(TEST_DB)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        # Insert the canonical TEST_SHOP_ID used by estimate_labor
        await s.execute(
            text(
                "INSERT INTO shops (id, name, labor_rate, pricing_flag) "
                "VALUES (:id, :name, 150.00, :flag) "
                "ON CONFLICT (id) DO UPDATE SET labor_rate = EXCLUDED.labor_rate"
            ),
            {"id": TEST_SHOP_ID, "name": "Test Shop Canonical", "flag": "shop"},
        )
        await s.commit()
        yield s

        await s.execute(
            text("UPDATE shops SET labor_rate = 120.00 WHERE id = :sid"),
            {"sid": TEST_SHOP_ID},
        )
        await s.commit()

    await engine.dispose()


# ---------------------------------------------------------------------------
# lookup_part_price tests (no DB required)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lookup_part_price_returns_known_part():
    result = await lookup_part_price("brake pads")
    assert "unit_price" in result
    assert result["unit_price"] > 0
    assert "part" in result
    assert "part_number" in result


@pytest.mark.asyncio
async def test_lookup_part_price_case_insensitive():
    lower = await lookup_part_price("brake pads")
    upper = await lookup_part_price("BRAKE PADS")
    assert "unit_price" in upper
    assert upper["unit_price"] == lower["unit_price"]


@pytest.mark.asyncio
async def test_lookup_part_price_not_found():
    result = await lookup_part_price("nonexistent part xyz")
    assert "error" in result


# ---------------------------------------------------------------------------
# estimate_labor tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_estimate_labor_fallback_rate(db_session):
    """When the TEST_SHOP_ID is not in the DB, falls back to FALLBACK_LABOR_RATE."""
    # db_session does NOT have TEST_SHOP_ID, so estimate_labor will use the fallback
    result = await estimate_labor("Replace front brake pads", 2.0, db_session)
    assert result["rate"] == FALLBACK_LABOR_RATE
    assert result["total"] == round(2.0 * FALLBACK_LABOR_RATE, 2)
    assert result["task"] == "Replace front brake pads"
    assert result["hours"] == 2.0


@pytest.mark.asyncio
async def test_estimate_labor_uses_shop_rate(db_session_with_test_shop):
    """When TEST_SHOP_ID exists, uses the shop's labor_rate."""
    result = await estimate_labor("Oil change", 1.5, db_session_with_test_shop)
    assert result["rate"] == 150.00
    assert result["total"] == round(1.5 * 150.00, 2)


# ---------------------------------------------------------------------------
# create_quote tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_quote_returns_draft(db_session):
    result = await create_quote(db_session, session_id=None)
    assert result["status"] == "draft"
    assert "quote_id" in result
    # Validate it's a valid UUID
    uuid.UUID(result["quote_id"])


# ---------------------------------------------------------------------------
# create_quote_item tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_quote_item_updates_total(db_session):
    create_result = await create_quote(db_session, session_id=None)
    quote_id = create_result["quote_id"]

    item_result = await create_quote_item(
        quote_id=quote_id,
        item_type="part",
        description="Brake Pads",
        qty=1,
        unit_price=89.99,
        db=db_session,
    )
    assert "total" in item_result
    assert item_result["total"] == 89.99
    assert len(item_result["line_items"]) == 1


# ---------------------------------------------------------------------------
# list_quote_items tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_quote_items_returns_items(db_session):
    create_result = await create_quote(db_session, session_id=None)
    quote_id = create_result["quote_id"]

    await create_quote_item(
        quote_id=quote_id,
        item_type="part",
        description="Brake Pads",
        qty=2,
        unit_price=89.99,
        db=db_session,
    )

    list_result = await list_quote_items(quote_id=quote_id, db=db_session)
    assert "line_items" in list_result
    assert len(list_result["line_items"]) == 1
    assert list_result["line_items"][0]["description"] == "Brake Pads"
    assert list_result["line_items"][0]["qty"] == 2


# ---------------------------------------------------------------------------
# finalize_quote tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_finalize_quote_sets_status(db_session):
    create_result = await create_quote(db_session, session_id=None)
    quote_id = create_result["quote_id"]

    await create_quote_item(
        quote_id=quote_id,
        item_type="part",
        description="Oil Filter",
        qty=1,
        unit_price=12.99,
        db=db_session,
    )

    finalize_result = await finalize_quote(quote_id=quote_id, db=db_session)
    assert finalize_result["status"] == "final"
    assert finalize_result["quote_id"] == quote_id
