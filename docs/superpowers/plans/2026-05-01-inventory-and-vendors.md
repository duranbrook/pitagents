# Inventory + Vendors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build real-time parts inventory with multi-select filtering, a reorder queue with PartsTech integration, and a vendor directory with full contact profiles and purchase order history.

**Architecture:** New backend models (InventoryItem, Vendor, PurchaseOrder, PurchaseOrderLine) with CRUD routes. Inventory stock auto-decrements when parts are added to a job card via a new job card webhook. Frontend: inventory table with search + dropdown filters + active pills; vendor list + detail panel.

**Tech Stack:** FastAPI + SQLAlchemy async + PostgreSQL + Alembic; Next.js 16 + React 19 + TypeScript.

---

## File Structure

**Backend — new:**
- `backend/src/models/inventory.py` — InventoryItem model
- `backend/src/models/vendor.py` — Vendor + PurchaseOrder + PurchaseOrderLine models
- `backend/src/api/inventory.py` — inventory CRUD + stock adjustment
- `backend/src/api/vendors.py` — vendor CRUD + PO management
- `backend/tests/test_api/test_inventory.py`
- `backend/tests/test_api/test_vendors.py`

**Backend — modified:**
- `backend/src/models/__init__.py`
- `backend/src/api/main.py`
- `backend/src/api/job_cards.py` — auto-decrement stock when part added to job card

**Frontend — new:**
- `web/app/inventory/page.tsx`
- `web/app/vendors/page.tsx`
- `web/components/inventory/PartsTable.tsx`
- `web/components/inventory/FilterBar.tsx`
- `web/components/inventory/ReorderQueue.tsx`
- `web/components/vendors/VendorList.tsx`
- `web/components/vendors/VendorDetail.tsx`

**Frontend — modified:**
- `web/lib/types.ts`
- `web/lib/api.ts`
- `web/components/dashboard/tiles.tsx`

---

## Task 1: InventoryItem model + migration + API

**Files:**
- Create: `backend/src/models/inventory.py`
- Modify: `backend/src/models/__init__.py`
- Create: `backend/src/api/inventory.py`
- Modify: `backend/src/api/main.py`
- Test: `backend/tests/test_api/test_inventory.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_api/test_inventory.py
import uuid

SHOP_ID = "00000000-0000-0000-0000-000000000099"

def test_list_inventory_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/inventory", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

def test_create_inventory_item(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    item = MagicMock()
    item.id = uuid.uuid4()
    item.shop_id = uuid.UUID(SHOP_ID)
    item.name = "Mobil 1 5W-30 Quart"
    item.sku = "MOB-5W30-1"
    item.category = "Oils"
    item.quantity = 24
    item.reorder_at = 6
    item.cost_price = 8.50
    item.sell_price = 14.99
    item.vendor_id = None
    item.created_at = "2026-05-01T00:00:00+00:00"
    item.updated_at = "2026-05-01T00:00:00+00:00"
    mock_db.execute.return_value.scalar_one_or_none.return_value = item
    resp = client.post(
        "/inventory",
        json={
            "name": "Mobil 1 5W-30 Quart",
            "sku": "MOB-5W30-1",
            "category": "Oils",
            "quantity": 24,
            "reorder_at": 6,
            "cost_price": 8.50,
            "sell_price": 14.99,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Mobil 1 5W-30 Quart"

def test_adjust_stock(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    item = MagicMock()
    item.id = uuid.uuid4()
    item.shop_id = uuid.UUID(SHOP_ID)
    item.name = "Oil Filter"
    item.sku = "OF-001"
    item.category = "Filters"
    item.quantity = 10
    item.reorder_at = 3
    item.cost_price = 4.0
    item.sell_price = 9.99
    item.vendor_id = None
    item.created_at = "2026-05-01T00:00:00+00:00"
    item.updated_at = "2026-05-01T00:00:00+00:00"
    mock_db.execute.return_value.scalar_one_or_none.return_value = item
    resp = client.post(
        f"/inventory/{item.id}/adjust",
        json={"delta": -2, "reason": "used in JC-0001"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_inventory.py::test_list_inventory_empty -v
```
Expected: FAIL with `404`

- [ ] **Step 3: Create InventoryItem model**

```python
# backend/src/models/inventory.py
import uuid
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base

VALID_CATEGORIES = ["Oils", "Brakes", "Tires", "Filters", "Electrical", "Misc"]


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=True)
    category = Column(String(50), nullable=False, default="Misc")
    quantity = Column(Integer, default=0, nullable=False)
    reorder_at = Column(Integer, default=0, nullable=False)
    cost_price = Column(Numeric(10, 2), default=0)
    sell_price = Column(Numeric(10, 2), default=0)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
```

- [ ] **Step 4: Create inventory router**

```python
# backend/src/api/inventory.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.inventory import InventoryItem

router = APIRouter(prefix="/inventory", tags=["inventory"])


class InventoryItemCreate(BaseModel):
    name: str
    sku: Optional[str] = None
    category: str = "Misc"
    quantity: int = 0
    reorder_at: int = 0
    cost_price: float = 0.0
    sell_price: float = 0.0
    vendor_id: Optional[str] = None
    notes: Optional[str] = None


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[int] = None
    reorder_at: Optional[int] = None
    cost_price: Optional[float] = None
    sell_price: Optional[float] = None
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
    cost_price: float
    sell_price: float
    margin_pct: float
    stock_status: str  # ok | low | out
    vendor_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


def _item_to_response(item: InventoryItem) -> InventoryItemResponse:
    cost = float(item.cost_price or 0)
    sell = float(item.sell_price or 0)
    margin = round((sell - cost) / sell * 100, 1) if sell > 0 else 0.0
    qty = item.quantity or 0
    reorder = item.reorder_at or 0
    if qty == 0:
        stock_status = "out"
    elif qty <= reorder:
        stock_status = "low"
    else:
        stock_status = "ok"
    return InventoryItemResponse(
        id=str(item.id),
        shop_id=str(item.shop_id),
        name=item.name,
        sku=item.sku,
        category=item.category,
        quantity=qty,
        reorder_at=reorder,
        cost_price=cost,
        sell_price=sell,
        margin_pct=margin,
        stock_status=stock_status,
        vendor_id=str(item.vendor_id) if item.vendor_id else None,
        notes=item.notes,
        created_at=str(item.created_at),
        updated_at=str(item.updated_at),
    )


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
        like = f"%{search}%"
        q = q.where(or_(InventoryItem.name.ilike(like), InventoryItem.sku.ilike(like)))
    if category:
        q = q.where(InventoryItem.category == category)
    if vendor_id:
        q = q.where(InventoryItem.vendor_id == uuid.UUID(vendor_id))
    result = await db.execute(q.order_by(InventoryItem.name))
    items = result.scalars().all()
    responses = [_item_to_response(i) for i in items]
    # Filter by stock_status after computing it
    if stock_status:
        responses = [r for r in responses if r.stock_status == stock_status]
    return responses


@router.post("", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    body: InventoryItemCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    item = InventoryItem(
        shop_id=uuid.UUID(shop_id),
        name=body.name,
        sku=body.sku,
        category=body.category,
        quantity=body.quantity,
        reorder_at=body.reorder_at,
        cost_price=body.cost_price,
        sell_price=body.sell_price,
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
        select(InventoryItem).where(InventoryItem.id == iid, InventoryItem.shop_id == uuid.UUID(shop_id))
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
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
        select(InventoryItem).where(InventoryItem.id == iid, InventoryItem.shop_id == uuid.UUID(shop_id))
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    for field in ("name", "sku", "category", "quantity", "reorder_at", "cost_price", "sell_price", "notes"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(item, field, val)
    if body.vendor_id is not None:
        item.vendor_id = uuid.UUID(body.vendor_id) if body.vendor_id else None
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
        select(InventoryItem).where(InventoryItem.id == iid, InventoryItem.shop_id == uuid.UUID(shop_id))
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    item.quantity = max(0, (item.quantity or 0) + body.delta)
    await db.commit()
    await db.refresh(item)
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
        select(InventoryItem).where(InventoryItem.id == iid, InventoryItem.shop_id == uuid.UUID(shop_id))
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
```

- [ ] **Step 5: Register router**

```python
# backend/src/api/main.py — add:
from src.api.inventory import router as inventory_router
app.include_router(inventory_router)
```

- [ ] **Step 6: Update models __init__.py**

```python
from src.models.inventory import InventoryItem

# Add "InventoryItem" to __all__
```

- [ ] **Step 7: Generate migration**

Note: InventoryItem references `vendors.id` FK. Since Vendor model doesn't exist yet, create it as a nullable FK or remove the FK constraint for now — add it back in Task 2 migration.

Temporarily create the model without the vendor FK by commenting it out:
```python
# vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True)
vendor_id = Column(UUID(as_uuid=True), nullable=True)  # FK added in vendors migration
```

```bash
cd backend
alembic revision --autogenerate -m "add_inventory_items"
alembic upgrade head
```

- [ ] **Step 8: Run tests**

```bash
cd backend && python -m pytest tests/test_api/test_inventory.py -v
```
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add backend/src/models/inventory.py backend/src/models/__init__.py \
        backend/src/api/inventory.py backend/src/api/main.py \
        backend/tests/test_api/test_inventory.py backend/alembic/versions/
git commit -m "feat(backend): add InventoryItem model and inventory CRUD API"
```

---

## Task 2: Vendor + PurchaseOrder models + API

**Files:**
- Create: `backend/src/models/vendor.py`
- Modify: `backend/src/models/__init__.py`
- Modify: `backend/src/models/inventory.py` (restore vendor FK)
- Create: `backend/src/api/vendors.py`
- Modify: `backend/src/api/main.py`
- Test: `backend/tests/test_api/test_vendors.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_api/test_vendors.py
import uuid

SHOP_ID = "00000000-0000-0000-0000-000000000099"

def test_list_vendors_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/vendors", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

def test_create_vendor(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    v = MagicMock()
    v.id = uuid.uuid4()
    v.shop_id = uuid.UUID(SHOP_ID)
    v.name = "NAPA Auto Parts"
    v.category = "Parts"
    v.phone = "555-100-2000"
    v.email = "napa@example.com"
    v.website = "https://napaonline.com"
    v.address = "123 Main St"
    v.rep_name = "Mike"
    v.rep_phone = "555-100-2001"
    v.account_number = "NAPA-88421"
    v.notes = None
    v.source = "manual"
    v.ytd_spend = 0.0
    v.order_count = 0
    v.last_order_at = None
    v.created_at = "2026-05-01T00:00:00+00:00"
    mock_db.execute.return_value.scalar_one_or_none.return_value = v
    resp = client.post(
        "/vendors",
        json={"name": "NAPA Auto Parts", "category": "Parts", "phone": "555-100-2000"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "NAPA Auto Parts"

def test_get_vendor_404(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.get(f"/vendors/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_vendors.py::test_list_vendors_empty -v
```
Expected: FAIL with `404`

- [ ] **Step 3: Create Vendor and PurchaseOrder models**

```python
# backend/src/models/vendor.py
import uuid
from sqlalchemy import Column, String, Integer, Numeric, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name = Column(String(255), nullable=False)
    category = Column(String(50), default="Parts", nullable=False)  # Parts|Equipment|Utilities|Services
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    address = Column(String(500), nullable=True)
    rep_name = Column(String(255), nullable=True)
    rep_phone = Column(String(50), nullable=True)
    account_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    source = Column(String(20), default="manual", nullable=False)  # manual|partstech
    ytd_spend = Column(Numeric(10, 2), default=0)
    order_count = Column(Integer, default=0)
    last_order_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    po_number = Column(String(20), nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending|ordered|received
    items = Column(String, default="[]")  # JSON list of {name, sku, qty, unit_cost}
    total = Column(Numeric(10, 2), default=0)
    notes = Column(Text, nullable=True)
    ordered_at = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
```

- [ ] **Step 4: Create vendors router**

```python
# backend/src/api/vendors.py
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sql_func
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.vendor import Vendor, PurchaseOrder
from src.models.inventory import InventoryItem

router = APIRouter(prefix="/vendors", tags=["vendors"])


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
    items: list[dict]  # [{name, sku, qty, unit_cost}]
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


def _vendor_to_response(v: Vendor) -> VendorResponse:
    return VendorResponse(
        id=str(v.id),
        shop_id=str(v.shop_id),
        name=v.name,
        category=v.category,
        phone=v.phone,
        email=v.email,
        website=v.website,
        address=v.address,
        rep_name=v.rep_name,
        rep_phone=v.rep_phone,
        account_number=v.account_number,
        notes=v.notes,
        source=v.source,
        ytd_spend=float(v.ytd_spend or 0),
        order_count=v.order_count or 0,
        last_order_at=str(v.last_order_at) if v.last_order_at else None,
        created_at=str(v.created_at),
    )


def _po_to_response(po: PurchaseOrder) -> POResponse:
    return POResponse(
        id=str(po.id),
        vendor_id=str(po.vendor_id),
        po_number=po.po_number,
        status=po.status,
        items=json.loads(po.items or "[]"),
        total=float(po.total or 0),
        notes=po.notes,
        ordered_at=str(po.ordered_at) if po.ordered_at else None,
        received_at=str(po.received_at) if po.received_at else None,
        created_at=str(po.created_at),
    )


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
    result = await db.execute(q.order_by(Vendor.name))
    return [_vendor_to_response(v) for v in result.scalars().all()]


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    body: VendorCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    vendor = Vendor(shop_id=uuid.UUID(shop_id), **body.model_dump())
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
        select(Vendor).where(Vendor.id == vid, Vendor.shop_id == uuid.UUID(shop_id))
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
        select(Vendor).where(Vendor.id == vid, Vendor.shop_id == uuid.UUID(shop_id))
    )
    vendor = result.scalar_one_or_none()
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    for field in ("name", "category", "phone", "email", "website", "address",
                  "rep_name", "rep_phone", "account_number", "notes"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(vendor, field, val)
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
        select(Vendor).where(Vendor.id == vid, Vendor.shop_id == uuid.UUID(shop_id))
    )
    vendor = result.scalar_one_or_none()
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    await db.delete(vendor)
    await db.commit()


# ── Purchase Orders ────────────────────────────────────────────────────────

@router.get("/{vendor_id}/orders", response_model=list[POResponse])
async def list_purchase_orders(
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
            PurchaseOrder.vendor_id == vid, PurchaseOrder.shop_id == uuid.UUID(shop_id)
        ).order_by(PurchaseOrder.created_at.desc())
    )
    return [_po_to_response(po) for po in result.scalars().all()]


@router.post("/{vendor_id}/orders", response_model=POResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
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
    count_result = await db.execute(
        select(sql_func.count(PurchaseOrder.id)).where(PurchaseOrder.shop_id == sid)
    )
    count = count_result.scalar() or 0
    po_number = f"PO-{count + 1:04d}"
    total = sum(item.get("qty", 0) * item.get("unit_cost", 0) for item in body.items)
    po = PurchaseOrder(
        shop_id=sid,
        vendor_id=vid,
        po_number=po_number,
        status="pending",
        items=json.dumps(body.items),
        total=total,
        notes=body.notes,
    )
    db.add(po)
    await db.commit()
    await db.refresh(po)
    return _po_to_response(po)


@router.post("/{vendor_id}/orders/{po_id}/receive", response_model=POResponse)
async def receive_purchase_order(
    vendor_id: str,
    po_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark PO as received and update inventory stock for each item (matched by SKU)."""
    try:
        vid = uuid.UUID(vendor_id)
        pid = uuid.UUID(po_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid ID")
    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == pid, PurchaseOrder.vendor_id == vid,
            PurchaseOrder.shop_id == uuid.UUID(shop_id)
        )
    )
    po = result.scalar_one_or_none()
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status == "received":
        raise HTTPException(status_code=400, detail="Already received")

    items = json.loads(po.items or "[]")
    for po_item in items:
        sku = po_item.get("sku")
        qty = po_item.get("qty", 0)
        if sku:
            inv_result = await db.execute(
                select(InventoryItem).where(
                    InventoryItem.sku == sku,
                    InventoryItem.shop_id == uuid.UUID(shop_id)
                )
            )
            inv_item = inv_result.scalar_one_or_none()
            if inv_item:
                inv_item.quantity = (inv_item.quantity or 0) + qty

    po.status = "received"
    po.received_at = datetime.now(timezone.utc)

    vendor_result = await db.execute(select(Vendor).where(Vendor.id == vid))
    vendor = vendor_result.scalar_one_or_none()
    if vendor:
        vendor.ytd_spend = float(vendor.ytd_spend or 0) + float(po.total or 0)
        vendor.order_count = (vendor.order_count or 0) + 1
        vendor.last_order_at = po.received_at

    await db.commit()
    await db.refresh(po)
    return _po_to_response(po)
```

- [ ] **Step 5: Restore vendor FK in inventory.py**

```python
# backend/src/models/inventory.py — restore line (remove placeholder):
# Change: vendor_id = Column(UUID(as_uuid=True), nullable=True)
# To:
vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True)
```

- [ ] **Step 6: Register vendors router**

```python
# backend/src/api/main.py — add:
from src.api.vendors import router as vendors_router
app.include_router(vendors_router)
```

- [ ] **Step 7: Update models __init__.py**

```python
from src.models.vendor import Vendor, PurchaseOrder

# Add to __all__: "Vendor", "PurchaseOrder"
```

- [ ] **Step 8: Generate migration**

```bash
cd backend
alembic revision --autogenerate -m "add_vendors_and_purchase_orders"
alembic upgrade head
```

- [ ] **Step 9: Run tests**

```bash
cd backend && python -m pytest tests/test_api/test_vendors.py tests/test_api/test_inventory.py -v
```
Expected: all PASS

- [ ] **Step 10: Commit**

```bash
git add backend/src/models/vendor.py backend/src/models/inventory.py \
        backend/src/models/__init__.py backend/src/api/vendors.py \
        backend/src/api/main.py backend/tests/test_api/test_vendors.py \
        backend/alembic/versions/
git commit -m "feat(backend): add Vendor, PurchaseOrder models and vendor/PO API with receive flow"
```

---

## Task 3: Auto-decrement inventory when part added to job card

**Files:**
- Modify: `backend/src/api/job_cards.py`
- Test: `backend/tests/test_api/test_job_cards.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api/test_job_cards.py — append:

def test_adding_part_with_inventory_item_decrements_stock(client, auth_headers, mock_db):
    from unittest.mock import MagicMock, AsyncMock, patch
    import uuid as uuid_mod

    card_id = uuid_mod.uuid4()
    inv_id = uuid_mod.uuid4()

    card = MagicMock()
    card.id = card_id
    card.shop_id = uuid_mod.UUID(SHOP_ID)
    card.number = "JC-0001"
    card.customer_id = None
    card.vehicle_id = None
    card.column_id = None
    card.technician_ids = []
    card.services = []
    card.parts = []
    card.notes = None
    card.status = "active"
    card.created_at = "2026-05-01T00:00:00+00:00"
    card.updated_at = "2026-05-01T00:00:00+00:00"

    inv_item = MagicMock()
    inv_item.id = inv_id
    inv_item.quantity = 10

    execute_results = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=card)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=inv_item)),
    ]
    mock_db.execute.side_effect = execute_results

    resp = client.patch(
        f"/job-cards/{card_id}",
        json={"parts": [{"name": "Oil Filter", "sku": "OF-001", "qty": 2, "unit_cost": 4.0, "sell_price": 9.99, "inventory_item_id": str(inv_id)}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest "tests/test_api/test_job_cards.py::test_adding_part_with_inventory_item_decrements_stock" -v
```
Expected: test runs but stock is NOT decremented — we're adding the behavior next.

- [ ] **Step 3: Add stock decrement logic to update_job_card endpoint**

In `backend/src/api/job_cards.py`, import `InventoryItem` and add stock decrement when parts change:

```python
# backend/src/api/job_cards.py — at top of file, add import:
from src.models.inventory import InventoryItem

# Inside update_job_card endpoint, after "if body.parts is not None:" block:
    if body.parts is not None:
        old_parts = card.parts or []
        new_parts = body.parts
        # For each new part with inventory_item_id, decrement stock by qty
        for part in new_parts:
            inv_id = part.get("inventory_item_id")
            if not inv_id:
                continue
            # Check if this part wasn't in old_parts or qty increased
            old_match = next((p for p in old_parts if p.get("inventory_item_id") == inv_id), None)
            old_qty = float(old_match.get("qty", 0)) if old_match else 0
            new_qty = float(part.get("qty", 0))
            delta = int(new_qty - old_qty)
            if delta > 0:
                inv_result = await db.execute(
                    select(InventoryItem).where(
                        InventoryItem.id == uuid.UUID(inv_id),
                        InventoryItem.shop_id == uuid.UUID(shop_id)
                    )
                )
                inv_item = inv_result.scalar_one_or_none()
                if inv_item:
                    inv_item.quantity = max(0, (inv_item.quantity or 0) - delta)
        card.parts = body.parts
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_api/test_job_cards.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/job_cards.py backend/tests/test_api/test_job_cards.py
git commit -m "feat(backend): auto-decrement inventory stock when parts added to job card"
```

---

## Task 4: Frontend types + API client

**Files:**
- Modify: `web/lib/types.ts`
- Modify: `web/lib/api.ts`

- [ ] **Step 1: Add types**

```typescript
// Append to web/lib/types.ts:

// ── Inventory ─────────────────────────────────────────────────────────────

export interface InventoryItem {
  id: string
  shop_id: string
  name: string
  sku: string | null
  category: string
  quantity: number
  reorder_at: number
  cost_price: number
  sell_price: number
  margin_pct: number
  stock_status: 'ok' | 'low' | 'out'
  vendor_id: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

// ── Vendors ───────────────────────────────────────────────────────────────

export interface Vendor {
  id: string
  shop_id: string
  name: string
  category: string
  phone: string | null
  email: string | null
  website: string | null
  address: string | null
  rep_name: string | null
  rep_phone: string | null
  account_number: string | null
  notes: string | null
  source: string
  ytd_spend: number
  order_count: number
  last_order_at: string | null
  created_at: string
}

export interface PurchaseOrder {
  id: string
  vendor_id: string
  po_number: string
  status: 'pending' | 'ordered' | 'received'
  items: Array<{ name: string; sku: string | null; qty: number; unit_cost: number }>
  total: number
  notes: string | null
  ordered_at: string | null
  received_at: string | null
  created_at: string
}
```

- [ ] **Step 2: Add API functions**

```typescript
// Append to web/lib/api.ts:
import type { InventoryItem, Vendor, PurchaseOrder } from './types'

// ── Inventory ─────────────────────────────────────────────────────────────

export const getInventory = (params?: {
  search?: string; category?: string; stock_status?: string; vendor_id?: string
}): Promise<InventoryItem[]> =>
  api.get('/inventory', { params }).then(r => r.data)

export const createInventoryItem = (data: Partial<InventoryItem>): Promise<InventoryItem> =>
  api.post('/inventory', data).then(r => r.data)

export const updateInventoryItem = (id: string, data: Partial<InventoryItem>): Promise<InventoryItem> =>
  api.patch(`/inventory/${id}`, data).then(r => r.data)

export const adjustInventoryStock = (id: string, delta: number, reason?: string): Promise<InventoryItem> =>
  api.post(`/inventory/${id}/adjust`, { delta, reason }).then(r => r.data)

export const deleteInventoryItem = (id: string): Promise<void> =>
  api.delete(`/inventory/${id}`).then(() => undefined)

// ── Vendors ───────────────────────────────────────────────────────────────

export const getVendors = (params?: { category?: string }): Promise<Vendor[]> =>
  api.get('/vendors', { params }).then(r => r.data)

export const createVendor = (data: Partial<Vendor>): Promise<Vendor> =>
  api.post('/vendors', data).then(r => r.data)

export const updateVendor = (id: string, data: Partial<Vendor>): Promise<Vendor> =>
  api.patch(`/vendors/${id}`, data).then(r => r.data)

export const deleteVendor = (id: string): Promise<void> =>
  api.delete(`/vendors/${id}`).then(() => undefined)

export const getVendorOrders = (vendorId: string): Promise<PurchaseOrder[]> =>
  api.get(`/vendors/${vendorId}/orders`).then(r => r.data)

export const createPurchaseOrder = (vendorId: string, data: { items: PurchaseOrder['items']; notes?: string }): Promise<PurchaseOrder> =>
  api.post(`/vendors/${vendorId}/orders`, data).then(r => r.data)

export const receivePurchaseOrder = (vendorId: string, poId: string): Promise<PurchaseOrder> =>
  api.post(`/vendors/${vendorId}/orders/${poId}/receive`).then(r => r.data)
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd web && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add web/lib/types.ts web/lib/api.ts
git commit -m "feat(web): add Inventory, Vendor, PurchaseOrder types and API functions"
```

---

## Task 5: Inventory page

**Files:**
- Create: `web/app/inventory/page.tsx`
- Create: `web/components/inventory/FilterBar.tsx`
- Create: `web/components/inventory/ReorderQueue.tsx`

- [ ] **Step 1: Create FilterBar component**

```tsx
// web/components/inventory/FilterBar.tsx
'use client'
import { useState } from 'react'

const CATEGORIES = ['Oils', 'Brakes', 'Tires', 'Filters', 'Electrical', 'Misc']
const STOCK_OPTIONS = [
  { value: 'ok', label: 'In stock' },
  { value: 'low', label: 'Low' },
  { value: 'out', label: 'Out of stock' },
]

interface Filters {
  search: string
  categories: string[]
  stockStatuses: string[]
}

interface Props {
  filters: Filters
  onChange: (f: Filters) => void
}

function MultiSelectDropdown({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string
  options: { value: string; label?: string }[]
  selected: string[]
  onToggle: (v: string) => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          height: 32, padding: '0 12px', borderRadius: 7, cursor: 'pointer', fontSize: 12, fontWeight: 600,
          background: selected.length > 0 ? 'rgba(217,119,6,0.12)' : 'rgba(255,255,255,0.06)',
          border: `1px solid ${selected.length > 0 ? 'rgba(217,119,6,0.3)' : 'rgba(255,255,255,0.1)'}`,
          color: selected.length > 0 ? '#fbbf24' : 'rgba(255,255,255,0.65)',
          display: 'flex', alignItems: 'center', gap: 4,
        }}
      >
        {label}{selected.length > 0 ? ` (${selected.length})` : ''} ▾
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 4, zIndex: 20,
          background: '#1e1e1e', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8,
          padding: 6, minWidth: 160,
        }}>
          {options.map(opt => (
            <div
              key={opt.value}
              onClick={() => onToggle(opt.value)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px',
                cursor: 'pointer', borderRadius: 5, fontSize: 12,
                background: selected.includes(opt.value) ? 'rgba(217,119,6,0.1)' : 'transparent',
                color: selected.includes(opt.value) ? '#fbbf24' : 'rgba(255,255,255,0.7)',
              }}
            >
              <span style={{ width: 14, height: 14, borderRadius: 3, border: `1.5px solid ${selected.includes(opt.value) ? '#d97706' : 'rgba(255,255,255,0.25)'}`, background: selected.includes(opt.value) ? '#d97706' : 'transparent', display: 'inline-block', flexShrink: 0 }} />
              {opt.label ?? opt.value}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function FilterBar({ filters, onChange }: Props) {
  const toggleCategory = (v: string) =>
    onChange({ ...filters, categories: filters.categories.includes(v) ? filters.categories.filter(c => c !== v) : [...filters.categories, v] })
  const toggleStock = (v: string) =>
    onChange({ ...filters, stockStatuses: filters.stockStatuses.includes(v) ? filters.stockStatuses.filter(s => s !== v) : [...filters.stockStatuses, v] })

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
      <input
        placeholder="Search part name or SKU…"
        value={filters.search}
        onChange={e => onChange({ ...filters, search: e.target.value })}
        style={{
          height: 32, padding: '0 12px', borderRadius: 7, border: '1px solid rgba(255,255,255,0.1)',
          background: 'rgba(255,255,255,0.05)', color: '#fff', fontSize: 12, minWidth: 200,
        }}
      />
      <MultiSelectDropdown
        label="Category"
        options={CATEGORIES.map(c => ({ value: c }))}
        selected={filters.categories}
        onToggle={toggleCategory}
      />
      <MultiSelectDropdown
        label="Stock"
        options={STOCK_OPTIONS}
        selected={filters.stockStatuses}
        onToggle={toggleStock}
      />
      <button
        style={{
          height: 32, padding: '0 12px', borderRadius: 7, border: '1px solid rgba(255,255,255,0.1)',
          background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.5)', fontSize: 12, cursor: 'pointer',
        }}
      >
        More filters
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Create ReorderQueue component**

```tsx
// web/components/inventory/ReorderQueue.tsx
'use client'
import type { InventoryItem } from '@/lib/types'

interface Props {
  items: InventoryItem[]
}

export default function ReorderQueue({ items }: Props) {
  const reorderItems = items.filter(i => i.stock_status !== 'ok')

  return (
    <div style={{ width: 240, flexShrink: 0, borderLeft: '1px solid rgba(255,255,255,0.07)', padding: '16px 16px' }}>
      <div style={{ fontSize: 10, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>
        Reorder Queue ({reorderItems.length})
      </div>
      {reorderItems.length === 0 ? (
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.2)', textAlign: 'center', padding: '16px 0' }}>All stock OK</div>
      ) : reorderItems.map(item => (
        <div key={item.id} style={{ padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,0.8)', marginBottom: 2 }}>{item.name}</div>
          <div style={{ fontSize: 10, color: item.stock_status === 'out' ? '#f87171' : '#fbbf24', marginBottom: 6 }}>
            {item.stock_status === 'out' ? 'Out of stock' : `Low: ${item.quantity} left`}
          </div>
          <button
            onClick={() => {
              const sku = item.sku ? `&item=${encodeURIComponent(item.sku)}` : ''
              window.open(`https://shop.partstech.com/search?q=${encodeURIComponent(item.name)}${sku}`, '_blank')
            }}
            style={{
              width: '100%', height: 26, borderRadius: 6, border: '1px solid rgba(255,255,255,0.12)',
              background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.55)', fontSize: 10,
              fontWeight: 600, cursor: 'pointer',
            }}
          >
            Order via PartsTech
          </button>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Create Inventory page**

```tsx
// web/app/inventory/page.tsx
'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import FilterBar from '@/components/inventory/FilterBar'
import ReorderQueue from '@/components/inventory/ReorderQueue'
import type { InventoryItem } from '@/lib/types'
import { getInventory, adjustInventoryStock } from '@/lib/api'

const STOCK_COLORS = { ok: '#4ade80', low: '#fbbf24', out: '#f87171' }

export default function InventoryPage() {
  const qc = useQueryClient()
  const [filters, setFilters] = useState({ search: '', categories: [] as string[], stockStatuses: [] as string[] })

  const { data: allItems = [], isLoading } = useQuery({
    queryKey: ['inventory', filters.search, filters.categories, filters.stockStatuses],
    queryFn: () => getInventory({
      search: filters.search || undefined,
      category: filters.categories.length === 1 ? filters.categories[0] : undefined,
      stock_status: filters.stockStatuses.length === 1 ? filters.stockStatuses[0] : undefined,
    }),
  })

  // Client-side filter for multi-select
  const items = allItems.filter(item =>
    (filters.categories.length === 0 || filters.categories.includes(item.category)) &&
    (filters.stockStatuses.length === 0 || filters.stockStatuses.includes(item.stock_status))
  )

  const activePills = [
    ...filters.categories.map(c => ({ type: 'category', value: c })),
    ...filters.stockStatuses.map(s => ({ type: 'stock', value: s })),
  ]

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '20px 24px 14px', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Inventory</div>
          <button style={{ height: 32, padding: '0 14px', borderRadius: 7, border: 'none', background: '#d97706', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
            + Add Part
          </button>
        </div>
        <FilterBar filters={filters} onChange={setFilters} />
        {activePills.length > 0 && (
          <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
            {activePills.map(p => (
              <span
                key={`${p.type}-${p.value}`}
                onClick={() => {
                  if (p.type === 'category') setFilters(f => ({ ...f, categories: f.categories.filter(c => c !== p.value) }))
                  else setFilters(f => ({ ...f, stockStatuses: f.stockStatuses.filter(s => s !== p.value) }))
                }}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 4, height: 22, padding: '0 8px', borderRadius: 11, fontSize: 11, fontWeight: 600, background: 'rgba(217,119,6,0.1)', border: '1px solid rgba(217,119,6,0.2)', color: '#fbbf24', cursor: 'pointer' }}
              >
                {p.value} ×
              </span>
            ))}
          </div>
        )}
      </div>

      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        {/* Table */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 24px 20px' }}>
          {isLoading ? (
            <div style={{ color: 'rgba(255,255,255,0.3)' }}>Loading…</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  {['Part', 'SKU', 'Category', 'Stock', 'Reorder At', 'Cost', 'Sell', 'Margin'].map(h => (
                    <th key={h} style={{ textAlign: 'left', padding: '0 0 10px', fontWeight: 700 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '11px 0', fontWeight: 600, color: 'rgba(255,255,255,0.88)' }}>{item.name}</td>
                    <td style={{ padding: '11px 0', color: 'rgba(255,255,255,0.4)', fontSize: 11 }}>{item.sku ?? '—'}</td>
                    <td style={{ padding: '11px 0', color: 'rgba(255,255,255,0.55)' }}>{item.category}</td>
                    <td style={{ padding: '11px 0' }}>
                      <span style={{ color: STOCK_COLORS[item.stock_status], fontWeight: 700 }}>{item.quantity}</span>
                    </td>
                    <td style={{ padding: '11px 0', color: 'rgba(255,255,255,0.4)' }}>{item.reorder_at}</td>
                    <td style={{ padding: '11px 0', color: 'rgba(255,255,255,0.6)' }}>${item.cost_price.toFixed(2)}</td>
                    <td style={{ padding: '11px 0', color: 'rgba(255,255,255,0.8)' }}>${item.sell_price.toFixed(2)}</td>
                    <td style={{ padding: '11px 0', color: item.margin_pct >= 30 ? '#4ade80' : item.margin_pct >= 15 ? '#fbbf24' : '#f87171' }}>
                      {item.margin_pct.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Reorder queue */}
        <ReorderQueue items={allItems} />
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Verify inventory page**

Open http://localhost:3000/inventory — should show parts table with columns, filter bar with search + dropdowns, and reorder queue on the right. Multi-select Category dropdown should show 6 options; active selections appear as dismissible pills below filter bar.

- [ ] **Step 5: Commit**

```bash
git add web/app/inventory/page.tsx web/components/inventory/
git commit -m "feat(web): add Inventory page with filter bar, parts table, and reorder queue"
```

---

## Task 6: Vendors page

**Files:**
- Create: `web/app/vendors/page.tsx`
- Create: `web/components/vendors/VendorList.tsx`
- Create: `web/components/vendors/VendorDetail.tsx`

- [ ] **Step 1: Create VendorList component**

```tsx
// web/components/vendors/VendorList.tsx
'use client'
import type { Vendor } from '@/lib/types'

const CATEGORY_COLORS: Record<string, string> = {
  Parts: '#60a5fa', Equipment: '#c084fc', Utilities: '#4ade80', Services: '#fbbf24',
}

interface Props {
  vendors: Vendor[]
  selectedId: string | null
  onSelect: (v: Vendor) => void
}

export default function VendorList({ vendors, selectedId, onSelect }: Props) {
  return (
    <div style={{ width: 280, flexShrink: 0, borderRight: '1px solid rgba(255,255,255,0.07)', overflowY: 'auto', padding: '14px 0' }}>
      {vendors.map(v => (
        <div
          key={v.id}
          onClick={() => onSelect(v)}
          style={{
            padding: '12px 20px', cursor: 'pointer',
            background: v.id === selectedId ? 'rgba(255,255,255,0.06)' : 'transparent',
            borderRight: v.id === selectedId ? '2px solid #d97706' : '2px solid transparent',
          }}
          onMouseEnter={e => { if (v.id !== selectedId) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)' }}
          onMouseLeave={e => { if (v.id !== selectedId) (e.currentTarget as HTMLElement).style.background = 'transparent' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 3 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.88)' }}>{v.name}</div>
            <span style={{
              fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4,
              background: `${CATEGORY_COLORS[v.category] ?? '#94a3b8'}22`,
              color: CATEGORY_COLORS[v.category] ?? '#94a3b8',
            }}>
              {v.category}
            </span>
          </div>
          {v.phone && <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 4 }}>{v.phone}</div>}
          <div style={{ display: 'flex', gap: 12, fontSize: 11, color: 'rgba(255,255,255,0.35)' }}>
            <span>YTD ${v.ytd_spend.toFixed(0)}</span>
            <span>{v.order_count} orders</span>
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Create VendorDetail component**

```tsx
// web/components/vendors/VendorDetail.tsx
'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Vendor, PurchaseOrder } from '@/lib/types'
import { getVendorOrders, receivePurchaseOrder } from '@/lib/api'

interface Props {
  vendor: Vendor
}

const PO_STATUS_COLORS: Record<string, string> = {
  pending: '#fbbf24', ordered: '#60a5fa', received: '#4ade80',
}

export default function VendorDetail({ vendor }: Props) {
  const qc = useQueryClient()
  const { data: orders = [] } = useQuery({
    queryKey: ['vendor-orders', vendor.id],
    queryFn: () => getVendorOrders(vendor.id),
  })

  const receive = useMutation({
    mutationFn: (poId: string) => receivePurchaseOrder(vendor.id, poId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['vendor-orders', vendor.id] }),
  })

  const contactFields = [
    { label: 'Phone', value: vendor.phone },
    { label: 'Email', value: vendor.email },
    { label: 'Website', value: vendor.website, isLink: true },
    { label: 'Address', value: vendor.address },
    { label: 'Rep / Contact', value: vendor.rep_name ? `${vendor.rep_name}${vendor.rep_phone ? ` · ${vendor.rep_phone}` : ''}` : null },
    { label: 'Account #', value: vendor.account_number },
  ]

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{vendor.name}</div>
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>{vendor.category} vendor</div>
      </div>

      {/* Contact profile */}
      <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, padding: 16, marginBottom: 20 }}>
        <div style={{ fontSize: 10, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>Contact</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px 20px' }}>
          {contactFields.map(({ label, value, isLink }) => (
            <div key={label}>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginBottom: 2 }}>{label}</div>
              {value ? (
                isLink ? (
                  <a href={value} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: '#60a5fa', textDecoration: 'none' }}>{value}</a>
                ) : (
                  <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.75)' }}>{value}</div>
                )
              ) : (
                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.2)' }}>—</div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        {[
          { label: 'YTD Spend', value: `$${vendor.ytd_spend.toFixed(0)}` },
          { label: 'Orders', value: String(vendor.order_count) },
          { label: 'Last Order', value: vendor.last_order_at ? new Date(vendor.last_order_at).toLocaleDateString() : '—' },
        ].map(({ label, value }) => (
          <div key={label} style={{ flex: 1, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 9, padding: '10px 14px' }}>
            <div style={{ fontSize: 16, fontWeight: 700 }}>{value}</div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Purchase orders */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <div style={{ fontSize: 10, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Purchase Orders</div>
          <button style={{ height: 26, padding: '0 10px', borderRadius: 6, border: 'none', background: '#d97706', color: '#fff', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}>
            + New Order
          </button>
        </div>
        {orders.length === 0 ? (
          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.2)', padding: '12px 0' }}>No orders yet</div>
        ) : orders.map(po => (
          <div key={po.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600 }}>{po.po_number}</div>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{po.items.length} items · ${po.total.toFixed(2)}</div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 5, background: `${PO_STATUS_COLORS[po.status] ?? '#94a3b8'}22`, color: PO_STATUS_COLORS[po.status] ?? '#94a3b8' }}>
                {po.status}
              </span>
              {po.status !== 'received' && (
                <button
                  onClick={() => receive.mutate(po.id)}
                  style={{ height: 24, padding: '0 8px', borderRadius: 5, border: '1px solid rgba(74,222,128,0.3)', background: 'rgba(74,222,128,0.06)', color: '#4ade80', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}
                >
                  Mark received
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create Vendors page**

```tsx
// web/app/vendors/page.tsx
'use client'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import VendorList from '@/components/vendors/VendorList'
import VendorDetail from '@/components/vendors/VendorDetail'
import type { Vendor } from '@/lib/types'
import { getVendors } from '@/lib/api'

export default function VendorsPage() {
  const [selectedVendor, setSelectedVendor] = useState<Vendor | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)

  const { data: vendors = [], isLoading } = useQuery({
    queryKey: ['vendors', categoryFilter],
    queryFn: () => getVendors(categoryFilter ? { category: categoryFilter } : undefined),
  })

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px 14px', flexShrink: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Vendors</div>
        <div style={{ display: 'flex', gap: 8 }}>
          {[null, 'Parts', 'Equipment', 'Utilities', 'Services'].map(cat => (
            <button
              key={cat ?? 'all'}
              onClick={() => setCategoryFilter(cat)}
              style={{
                height: 28, padding: '0 10px', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 600,
                background: categoryFilter === cat ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.04)',
                color: categoryFilter === cat ? '#fff' : 'rgba(255,255,255,0.45)',
              }}
            >
              {cat ?? 'All'}
            </button>
          ))}
          <button style={{ height: 28, padding: '0 12px', borderRadius: 6, border: 'none', background: '#d97706', color: '#fff', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
            + Add Vendor
          </button>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {isLoading ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)' }}>Loading…</div>
        ) : vendors.length === 0 ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.25)', fontSize: 13 }}>No vendors yet</div>
        ) : (
          <>
            <VendorList vendors={vendors} selectedId={selectedVendor?.id ?? null} onSelect={setSelectedVendor} />
            {selectedVendor ? (
              <VendorDetail vendor={selectedVendor} />
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.2)', fontSize: 13 }}>
                Select a vendor
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Verify vendors page**

Open http://localhost:3000/vendors — left panel shows vendor list, right panel shows contact details + PO history when a vendor is selected. "Mark received" on a PO should update inventory stock for matched SKUs.

- [ ] **Step 5: Update dashboard tiles**

In `web/components/dashboard/tiles.tsx`, find Inventory and Vendors tiles and set `status: 'live'` with `href: '/inventory'` and `href: '/vendors'`.

- [ ] **Step 6: Commit**

```bash
git add web/app/vendors/page.tsx web/components/vendors/ \
        web/components/dashboard/tiles.tsx
git commit -m "feat(web): add Vendors page with contact profile and PO history; wire dashboard tiles"
```
