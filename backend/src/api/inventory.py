import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.inventory import InventoryItem, VALID_CATEGORIES

router = APIRouter(prefix="/inventory", tags=["inventory"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class InventoryItemCreate(BaseModel):
    name: str
    sku: Optional[str] = None
    category: str = "Misc"
    quantity: int = 0
    reorder_at: int = 0
    cost_price: Optional[str] = None
    sell_price: Optional[str] = None
    vendor_id: Optional[str] = None
    notes: Optional[str] = None


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[int] = None
    reorder_at: Optional[int] = None
    cost_price: Optional[str] = None
    sell_price: Optional[str] = None
    vendor_id: Optional[str] = None
    notes: Optional[str] = None


class StockAdjustment(BaseModel):
    delta: int
    reason: Optional[str] = None


class InventoryItemResponse(BaseModel):
    id: str
    shop_id: str
    name: str
    sku: Optional[str] = None
    category: str
    quantity: int
    reorder_at: int
    cost_price: Optional[str] = None
    sell_price: Optional[str] = None
    vendor_id: Optional[str] = None
    notes: Optional[str] = None
    margin_pct: float
    stock_status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_margin(cost_price, sell_price) -> float:
    try:
        sell = float(sell_price) if sell_price is not None else 0.0
        cost = float(cost_price) if cost_price is not None else 0.0
        if sell > 0:
            return round((sell - cost) / sell * 100, 1)
        return 0.0
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def _compute_stock_status(quantity: int, reorder_at: int) -> str:
    if quantity == 0:
        return "out"
    if quantity <= reorder_at:
        return "low"
    return "ok"


def _dt(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return val.isoformat()


def _item_to_response(item: InventoryItem) -> InventoryItemResponse:
    qty = item.quantity if item.quantity is not None else 0
    reorder = item.reorder_at if item.reorder_at is not None else 0
    return InventoryItemResponse(
        id=str(item.id),
        shop_id=str(item.shop_id),
        name=item.name,
        sku=item.sku,
        category=item.category or "Misc",
        quantity=qty,
        reorder_at=reorder,
        cost_price=str(item.cost_price) if item.cost_price is not None else None,
        sell_price=str(item.sell_price) if item.sell_price is not None else None,
        vendor_id=str(item.vendor_id) if item.vendor_id else None,
        notes=item.notes,
        margin_pct=_compute_margin(item.cost_price, item.sell_price),
        stock_status=_compute_stock_status(qty, reorder),
        created_at=_dt(item.created_at),
        updated_at=_dt(item.updated_at),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=list[InventoryItemResponse])
async def list_inventory(
    search: Optional[str] = None,
    category: Optional[str] = None,
    stock_status: Optional[str] = None,
    vendor_id: Optional[str] = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    q = select(InventoryItem).where(InventoryItem.shop_id == sid)

    if search:
        pattern = f"%{search}%"
        q = q.where(
            or_(
                InventoryItem.name.ilike(pattern),
                InventoryItem.sku.ilike(pattern),
            )
        )
    if category:
        q = q.where(InventoryItem.category == category)
    if vendor_id:
        try:
            vid = uuid.UUID(vendor_id)
            q = q.where(InventoryItem.vendor_id == vid)
        except ValueError:
            pass

    q = q.order_by(InventoryItem.name.asc())
    result = await db.execute(q)
    items = result.scalars().all()

    # Apply stock_status post-filter (computed field)
    if stock_status:
        items = [i for i in items if _compute_stock_status(
            i.quantity if i.quantity is not None else 0,
            i.reorder_at if i.reorder_at is not None else 0,
        ) == stock_status]

    return [_item_to_response(i) for i in items]


@router.post("", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    body: InventoryItemCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    if body.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"category must be one of {VALID_CATEGORIES}",
        )

    sid = uuid.UUID(shop_id)
    item = InventoryItem(
        shop_id=sid,
        name=body.name,
        sku=body.sku,
        category=body.category,
        quantity=body.quantity,
        reorder_at=body.reorder_at,
        cost_price=Decimal(body.cost_price) if body.cost_price else None,
        sell_price=Decimal(body.sell_price) if body.sell_price else None,
        vendor_id=uuid.UUID(body.vendor_id) if body.vendor_id else None,
        notes=body.notes,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _item_to_response(item)


@router.get("/{item_id}", response_model=InventoryItemResponse)
async def get_inventory_item(
    item_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        iid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid item_id")

    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == iid,
            InventoryItem.shop_id == uuid.UUID(shop_id),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return _item_to_response(item)


@router.patch("/{item_id}", response_model=InventoryItemResponse)
async def update_inventory_item(
    item_id: str,
    body: InventoryItemUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        iid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid item_id")

    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == iid,
            InventoryItem.shop_id == uuid.UUID(shop_id),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if body.name is not None:
        item.name = body.name
    if body.sku is not None:
        item.sku = body.sku
    if body.category is not None:
        if body.category not in VALID_CATEGORIES:
            raise HTTPException(
                status_code=422,
                detail=f"category must be one of {VALID_CATEGORIES}",
            )
        item.category = body.category
    if body.quantity is not None:
        item.quantity = body.quantity
    if body.reorder_at is not None:
        item.reorder_at = body.reorder_at
    if body.cost_price is not None:
        item.cost_price = Decimal(body.cost_price)
    if body.sell_price is not None:
        item.sell_price = Decimal(body.sell_price)
    if body.vendor_id is not None:
        item.vendor_id = uuid.UUID(body.vendor_id) if body.vendor_id else None
    if body.notes is not None:
        item.notes = body.notes

    await db.commit()
    await db.refresh(item)
    return _item_to_response(item)


@router.post("/{item_id}/adjust", response_model=InventoryItemResponse)
async def adjust_stock(
    item_id: str,
    body: StockAdjustment,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        iid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid item_id")

    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == iid,
            InventoryItem.shop_id == uuid.UUID(shop_id),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    current_qty = item.quantity if item.quantity is not None else 0
    item.quantity = max(0, current_qty + body.delta)

    await db.commit()
    return _item_to_response(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    item_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        iid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid item_id")

    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == iid,
            InventoryItem.shop_id == uuid.UUID(shop_id),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    await db.delete(item)
    await db.commit()
