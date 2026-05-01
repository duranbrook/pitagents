import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sql_func, text
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.vendor import Vendor, PurchaseOrder
from src.models.inventory import InventoryItem

router = APIRouter(prefix="/vendors", tags=["vendors"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class VendorCreate(BaseModel):
    name: str
    category: str = "Parts"
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    rep_name: Optional[str] = None
    rep_phone: Optional[str] = None
    account_number: Optional[str] = None
    notes: Optional[str] = None


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    rep_name: Optional[str] = None
    rep_phone: Optional[str] = None
    account_number: Optional[str] = None
    notes: Optional[str] = None


class POCreate(BaseModel):
    items: list[dict]
    notes: Optional[str] = None


class VendorResponse(BaseModel):
    id: str
    shop_id: str
    name: str
    category: str
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    rep_name: Optional[str] = None
    rep_phone: Optional[str] = None
    account_number: Optional[str] = None
    notes: Optional[str] = None
    source: str
    ytd_spend: float
    order_count: int
    last_order_at: Optional[str] = None
    created_at: str


class POResponse(BaseModel):
    id: str
    vendor_id: str
    po_number: str
    status: str
    items: list[dict]
    total: float
    notes: Optional[str] = None
    ordered_at: Optional[str] = None
    received_at: Optional[str] = None
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return val.isoformat()


def _vendor_to_response(vendor: Vendor) -> VendorResponse:
    return VendorResponse(
        id=str(vendor.id),
        shop_id=str(vendor.shop_id),
        name=vendor.name,
        category=vendor.category or "Parts",
        phone=vendor.phone,
        email=vendor.email,
        website=vendor.website,
        address=vendor.address,
        rep_name=vendor.rep_name,
        rep_phone=vendor.rep_phone,
        account_number=vendor.account_number,
        notes=vendor.notes,
        source=vendor.source or "manual",
        ytd_spend=float(vendor.ytd_spend) if vendor.ytd_spend is not None else 0.0,
        order_count=int(vendor.order_count) if vendor.order_count is not None else 0,
        last_order_at=_dt(vendor.last_order_at),
        created_at=_dt(vendor.created_at) or "",
    )


def _po_to_response(po: PurchaseOrder) -> POResponse:
    return POResponse(
        id=str(po.id),
        vendor_id=str(po.vendor_id),
        po_number=po.po_number,
        status=po.status or "pending",
        items=json.loads(po.items or "[]"),
        total=float(po.total) if po.total is not None else 0.0,
        notes=po.notes,
        ordered_at=_dt(po.ordered_at),
        received_at=_dt(po.received_at),
        created_at=_dt(po.created_at) or "",
    )


async def _next_po_number(shop_id: uuid.UUID, db: AsyncSession) -> str:
    result = await db.execute(
        text("SELECT MAX(CAST(split_part(po_number, '-', 2) AS INTEGER)) FROM purchase_orders WHERE shop_id = :sid"),
        {"sid": str(shop_id)},
    )
    max_n = result.scalar() or 0
    return f"PO-{max_n + 1:04d}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=list[VendorResponse])
async def list_vendors(
    category: Optional[str] = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    q = select(Vendor).where(Vendor.shop_id == sid)
    if category:
        q = q.where(Vendor.category == category)
    q = q.order_by(Vendor.name.asc())
    result = await db.execute(q)
    vendors = result.scalars().all()
    return [_vendor_to_response(v) for v in vendors]


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    body: VendorCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    vendor = Vendor(shop_id=sid, **body.model_dump())
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)
    return _vendor_to_response(vendor)


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        vid = uuid.UUID(vendor_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid vendor_id")

    result = await db.execute(
        select(Vendor).where(
            Vendor.id == vid,
            Vendor.shop_id == uuid.UUID(shop_id),
        )
    )
    vendor = result.scalar_one_or_none()
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return _vendor_to_response(vendor)


@router.patch("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: str,
    body: VendorUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        vid = uuid.UUID(vendor_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid vendor_id")

    result = await db.execute(
        select(Vendor).where(
            Vendor.id == vid,
            Vendor.shop_id == uuid.UUID(shop_id),
        )
    )
    vendor = result.scalar_one_or_none()
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)

    await db.commit()
    await db.refresh(vendor)
    return _vendor_to_response(vendor)


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        vid = uuid.UUID(vendor_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid vendor_id")

    result = await db.execute(
        select(Vendor).where(
            Vendor.id == vid,
            Vendor.shop_id == uuid.UUID(shop_id),
        )
    )
    vendor = result.scalar_one_or_none()
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")

    await db.delete(vendor)
    await db.commit()


@router.get("/{vendor_id}/orders", response_model=list[POResponse])
async def list_vendor_orders(
    vendor_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        vid = uuid.UUID(vendor_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid vendor_id")

    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.vendor_id == vid,
            PurchaseOrder.shop_id == uuid.UUID(shop_id),
        )
    )
    orders = result.scalars().all()
    return [_po_to_response(po) for po in orders]


@router.post("/{vendor_id}/orders", response_model=POResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor_order(
    vendor_id: str,
    body: POCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        vid = uuid.UUID(vendor_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid vendor_id")

    sid = uuid.UUID(shop_id)

    # Verify vendor belongs to shop
    result = await db.execute(
        select(Vendor).where(Vendor.id == vid, Vendor.shop_id == sid)
    )
    vendor = result.scalar_one_or_none()
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")

    po_number = await _next_po_number(sid, db)
    total = sum(
        item.get("qty", 0) * item.get("unit_cost", 0)
        for item in body.items
    )

    po = PurchaseOrder(
        shop_id=sid,
        vendor_id=vid,
        po_number=po_number,
        items=json.dumps(body.items),
        total=total,
        notes=body.notes,
    )
    db.add(po)
    await db.commit()
    await db.refresh(po)
    return _po_to_response(po)


@router.post("/{vendor_id}/orders/{po_id}/receive", response_model=POResponse)
async def receive_order(
    vendor_id: str,
    po_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        vid = uuid.UUID(vendor_id)
        pid = uuid.UUID(po_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid vendor_id or po_id")

    sid = uuid.UUID(shop_id)

    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == pid,
            PurchaseOrder.vendor_id == vid,
            PurchaseOrder.shop_id == sid,
        )
    )
    po = result.scalar_one_or_none()
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    now = datetime.now(timezone.utc)
    items = json.loads(po.items or "[]")

    # Update inventory stock by SKU match
    for item in items:
        sku = item.get("sku")
        qty = item.get("qty", 0)
        if sku and qty > 0:
            inv_result = await db.execute(
                select(InventoryItem).where(
                    InventoryItem.shop_id == sid,
                    InventoryItem.sku == sku,
                )
            )
            inv_item = inv_result.scalar_one_or_none()
            if inv_item is not None:
                current_qty = inv_item.quantity if inv_item.quantity is not None else 0
                inv_item.quantity = current_qty + qty

    # Update vendor stats
    result_v = await db.execute(
        select(Vendor).where(Vendor.id == vid, Vendor.shop_id == sid)
    )
    vendor = result_v.scalar_one_or_none()
    if vendor is not None:
        current_spend = float(vendor.ytd_spend) if vendor.ytd_spend is not None else 0.0
        vendor.ytd_spend = current_spend + float(po.total or 0)
        current_count = int(vendor.order_count) if vendor.order_count is not None else 0
        vendor.order_count = current_count + 1
        vendor.last_order_at = now

    # Mark PO received
    po.status = "received"
    po.received_at = now

    await db.commit()
    await db.refresh(po)
    return _po_to_response(po)
