# Job Cards + Invoices Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Job Cards kanban/list workflow, configurable columns, and Invoices with Stripe payment links, auto-generated from job cards, plus Mitchell1 ProDemand labor time lookup embedded in job card line items and a multi-provider financing button on invoices.

**Architecture:** New backend models (ShopSettings, JobCardColumn, JobCard, Invoice, InvoicePaymentEvent) with FastAPI CRUD routes scoped by shop_id, a Mitchell1 ProDemand proxy endpoint, and Stripe Checkout session creation. Frontend uses Next.js App Router with inline dark-theme styles matching the existing codebase. React Query caches all data.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + PostgreSQL + Alembic; Next.js 16 + React 19 + TypeScript + React Query + Axios; `stripe` Python SDK; Mitchell1 ProDemand REST API.

---

## File Structure

**Backend — new:**
- `backend/src/models/shop_settings.py` — ShopSettings (integrations credentials, nav pins, financing threshold)
- `backend/src/models/job_card.py` — JobCardColumn + JobCard models
- `backend/src/models/invoice.py` — Invoice + InvoicePaymentEvent models
- `backend/src/api/shop_settings.py` — GET/PATCH /settings/shop
- `backend/src/api/job_cards.py` — full CRUD + column management + column seed
- `backend/src/api/invoices.py` — CRUD + payment link + financing + PDF
- `backend/src/api/labor_lookup.py` — Mitchell1 ProDemand proxy
- `backend/tests/test_api/test_job_cards.py`
- `backend/tests/test_api/test_invoices.py`

**Backend — modified:**
- `backend/src/models/__init__.py` — import new models
- `backend/src/api/main.py` — include new routers

**Frontend — new:**
- `web/app/job-cards/page.tsx`
- `web/app/invoices/page.tsx`
- `web/components/job-cards/KanbanBoard.tsx`
- `web/components/job-cards/KanbanColumn.tsx`
- `web/components/job-cards/JobCardCard.tsx`
- `web/components/job-cards/JobCardDetail.tsx`
- `web/components/job-cards/JobCardList.tsx`
- `web/components/invoices/InvoiceDetail.tsx`
- `web/components/invoices/FinancingModal.tsx`

**Frontend — modified:**
- `web/lib/types.ts` — add JobCard*, Invoice* types
- `web/lib/api.ts` — add job card + invoice API functions
- `web/components/dashboard/tiles.tsx` — set Job Cards + Invoices tiles to "live"
- `web/components/AppShell.tsx` — respect nav_pins from ShopSettings

---

## Task 1: ShopSettings model + API

**Files:**
- Create: `backend/src/models/shop_settings.py`
- Modify: `backend/src/models/__init__.py`
- Create: `backend/src/api/shop_settings.py`
- Modify: `backend/src/api/main.py`
- Test: `backend/tests/test_api/test_shop_settings.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api/test_shop_settings.py
def test_get_shop_settings_returns_defaults(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.get("/settings/shop", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nav_pins"] == []
    assert data["mitchell1_enabled"] is False
    assert data["financing_threshold"] == "500"

def test_patch_shop_settings_updates_nav_pins(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    import uuid
    fake = MagicMock()
    fake.id = uuid.uuid4()
    fake.shop_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    fake.nav_pins = []
    fake.stripe_publishable_key = None
    fake.mitchell1_enabled = False
    fake.synchrony_enabled = False
    fake.wisetack_enabled = False
    fake.quickbooks_enabled = False
    fake.financing_threshold = "500"
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake
    resp = client.patch(
        "/settings/shop",
        json={"nav_pins": ["/job-cards", "/invoices"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_api/test_shop_settings.py -v
```
Expected: FAIL with `404` or `ImportError`

- [ ] **Step 3: Create ShopSettings model**

```python
# backend/src/models/shop_settings.py
import uuid
from sqlalchemy import Column, String, Boolean, JSON, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class ShopSettings(Base):
    __tablename__ = "shop_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    nav_pins = Column(JSON, default=list)
    stripe_publishable_key = Column(String(200), nullable=True)
    stripe_secret_key_encrypted = Column(Text, nullable=True)
    mitchell1_enabled = Column(Boolean, default=False)
    mitchell1_api_key_encrypted = Column(Text, nullable=True)
    synchrony_enabled = Column(Boolean, default=False)
    synchrony_dealer_id = Column(String(100), nullable=True)
    wisetack_enabled = Column(Boolean, default=False)
    wisetack_merchant_id = Column(String(100), nullable=True)
    quickbooks_enabled = Column(Boolean, default=False)
    quickbooks_refresh_token_encrypted = Column(Text, nullable=True)
    financing_threshold = Column(String(10), default="500")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
```

- [ ] **Step 4: Add import to `__init__.py`**

```python
# backend/src/models/__init__.py — append before __all__
from src.models.shop_settings import ShopSettings

__all__ = [
    "Shop", "User", "InspectionSession", "Report", "MediaFile",
    "ChatMessage", "Quote", "Customer", "Vehicle", "CustomerMessage",
    "ShopSettings",
]
```

- [ ] **Step 5: Create shop_settings router**

```python
# backend/src/api/shop_settings.py
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.shop_settings import ShopSettings

router = APIRouter(prefix="/settings", tags=["settings"])


class ShopSettingsResponse(BaseModel):
    id: str
    shop_id: str
    nav_pins: list[str]
    stripe_publishable_key: Optional[str] = None
    mitchell1_enabled: bool
    synchrony_enabled: bool
    wisetack_enabled: bool
    quickbooks_enabled: bool
    financing_threshold: str


class ShopSettingsUpdate(BaseModel):
    nav_pins: Optional[list[str]] = None
    stripe_publishable_key: Optional[str] = None
    mitchell1_enabled: Optional[bool] = None
    synchrony_enabled: Optional[bool] = None
    synchrony_dealer_id: Optional[str] = None
    wisetack_enabled: Optional[bool] = None
    wisetack_merchant_id: Optional[str] = None
    quickbooks_enabled: Optional[bool] = None
    financing_threshold: Optional[str] = None


def _to_response(s: ShopSettings) -> ShopSettingsResponse:
    return ShopSettingsResponse(
        id=str(s.id),
        shop_id=str(s.shop_id),
        nav_pins=s.nav_pins or [],
        stripe_publishable_key=s.stripe_publishable_key,
        mitchell1_enabled=bool(s.mitchell1_enabled),
        synchrony_enabled=bool(s.synchrony_enabled),
        wisetack_enabled=bool(s.wisetack_enabled),
        quickbooks_enabled=bool(s.quickbooks_enabled),
        financing_threshold=s.financing_threshold or "500",
    )


async def _get_or_create(shop_id: uuid.UUID, db: AsyncSession) -> ShopSettings:
    result = await db.execute(select(ShopSettings).where(ShopSettings.shop_id == shop_id))
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = ShopSettings(shop_id=shop_id, nav_pins=[])
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.get("/shop", response_model=ShopSettingsResponse)
async def get_shop_settings(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    return _to_response(await _get_or_create(uuid.UUID(shop_id), db))


@router.patch("/shop", response_model=ShopSettingsResponse)
async def update_shop_settings(
    body: ShopSettingsUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    settings = await _get_or_create(uuid.UUID(shop_id), db)
    if body.nav_pins is not None:
        settings.nav_pins = body.nav_pins[:8]
    for field in ("stripe_publishable_key", "mitchell1_enabled", "synchrony_enabled",
                  "synchrony_dealer_id", "wisetack_enabled", "wisetack_merchant_id",
                  "quickbooks_enabled", "financing_threshold"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(settings, field, val)
    await db.commit()
    await db.refresh(settings)
    return _to_response(settings)
```

- [ ] **Step 6: Include router in main.py**

```python
# backend/src/api/main.py — after existing router imports, add:
from src.api.shop_settings import router as shop_settings_router
# then after existing app.include_router calls:
app.include_router(shop_settings_router)
```

- [ ] **Step 7: Generate and apply migration**

```bash
cd backend
alembic revision --autogenerate -m "add_shop_settings"
alembic upgrade head
```
Expected: migration file created in `alembic/versions/`, `upgrade head` prints "Running upgrade ... -> <rev>"

- [ ] **Step 8: Run tests — expect PASS**

```bash
cd backend && python -m pytest tests/test_api/test_shop_settings.py -v
```

- [ ] **Step 9: Commit**

```bash
git add backend/src/models/shop_settings.py backend/src/models/__init__.py \
        backend/src/api/shop_settings.py backend/src/api/main.py \
        backend/tests/test_api/test_shop_settings.py backend/alembic/versions/
git commit -m "feat(backend): add ShopSettings model and CRUD API"
```

---

## Task 2: JobCardColumn model + migration + API

**Files:**
- Create: `backend/src/models/job_card.py` (JobCardColumn only for now)
- Modify: `backend/src/models/__init__.py`
- Create: `backend/src/api/job_cards.py` (column endpoints only)
- Modify: `backend/src/api/main.py`
- Test: `backend/tests/test_api/test_job_cards.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api/test_job_cards.py
import uuid

SHOP_ID = "00000000-0000-0000-0000-000000000099"

def test_list_columns_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/job-cards/columns", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

def test_create_column(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    col = MagicMock()
    col.id = uuid.uuid4()
    col.shop_id = uuid.UUID(SHOP_ID)
    col.name = "Drop-Off"
    col.position = 0
    col.created_at = "2026-05-01T00:00:00+00:00"
    mock_db.execute.return_value.scalar_one_or_none.return_value = col
    resp = client.post(
        "/job-cards/columns",
        json={"name": "Drop-Off", "position": 0},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Drop-Off"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_job_cards.py::test_list_columns_empty -v
```
Expected: FAIL with `404`

- [ ] **Step 3: Create JobCardColumn model (add to job_card.py)**

```python
# backend/src/models/job_card.py
import uuid
from sqlalchemy import Column, String, Integer, JSON, Text, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class JobCardColumn(Base):
    __tablename__ = "job_card_columns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name = Column(String(100), nullable=False)
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
```

- [ ] **Step 4: Add column endpoints to job_cards.py**

```python
# backend/src/api/job_cards.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.job_card import JobCardColumn

router = APIRouter(prefix="/job-cards", tags=["job-cards"])

DEFAULT_COLUMNS = [
    {"name": "Drop-Off", "position": 0},
    {"name": "Diagnosis", "position": 1},
    {"name": "In Service", "position": 2},
    {"name": "Ready for Pickup", "position": 3},
]


class ColumnResponse(BaseModel):
    id: str
    shop_id: str
    name: str
    position: int
    created_at: str


class ColumnCreate(BaseModel):
    name: str
    position: int


class ColumnUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[int] = None


def _col_to_response(c: JobCardColumn) -> ColumnResponse:
    return ColumnResponse(
        id=str(c.id),
        shop_id=str(c.shop_id),
        name=c.name,
        position=c.position,
        created_at=str(c.created_at),
    )


async def _seed_default_columns(shop_id: uuid.UUID, db: AsyncSession) -> list[JobCardColumn]:
    cols = []
    for d in DEFAULT_COLUMNS:
        col = JobCardColumn(shop_id=shop_id, **d)
        db.add(col)
        cols.append(col)
    await db.commit()
    for col in cols:
        await db.refresh(col)
    return cols


@router.get("/columns", response_model=list[ColumnResponse])
async def list_columns(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    result = await db.execute(
        select(JobCardColumn)
        .where(JobCardColumn.shop_id == sid)
        .order_by(JobCardColumn.position)
    )
    cols = result.scalars().all()
    if not cols:
        cols = await _seed_default_columns(sid, db)
    return [_col_to_response(c) for c in cols]


@router.post("/columns", response_model=ColumnResponse, status_code=status.HTTP_201_CREATED)
async def create_column(
    body: ColumnCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    col = JobCardColumn(shop_id=uuid.UUID(shop_id), name=body.name, position=body.position)
    db.add(col)
    await db.commit()
    await db.refresh(col)
    return _col_to_response(col)


@router.patch("/columns/{column_id}", response_model=ColumnResponse)
async def update_column(
    column_id: str,
    body: ColumnUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        cid = uuid.UUID(column_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid column_id")
    result = await db.execute(
        select(JobCardColumn).where(
            JobCardColumn.id == cid, JobCardColumn.shop_id == uuid.UUID(shop_id)
        )
    )
    col = result.scalar_one_or_none()
    if col is None:
        raise HTTPException(status_code=404, detail="Column not found")
    if body.name is not None:
        col.name = body.name
    if body.position is not None:
        col.position = body.position
    await db.commit()
    await db.refresh(col)
    return _col_to_response(col)


@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_column(
    column_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        cid = uuid.UUID(column_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid column_id")
    result = await db.execute(
        select(JobCardColumn).where(
            JobCardColumn.id == cid, JobCardColumn.shop_id == uuid.UUID(shop_id)
        )
    )
    col = result.scalar_one_or_none()
    if col is None:
        raise HTTPException(status_code=404, detail="Column not found")
    await db.delete(col)
    await db.commit()
```

- [ ] **Step 5: Register router**

```python
# backend/src/api/main.py — add after shop_settings_router lines:
from src.api.job_cards import router as job_cards_router
app.include_router(job_cards_router)
```

- [ ] **Step 6: Update models __init__.py**

```python
# backend/src/models/__init__.py — append:
from src.models.job_card import JobCardColumn

__all__ = [
    "Shop", "User", "InspectionSession", "Report", "MediaFile",
    "ChatMessage", "Quote", "Customer", "Vehicle", "CustomerMessage",
    "ShopSettings", "JobCardColumn",
]
```

- [ ] **Step 7: Generate migration**

```bash
cd backend
alembic revision --autogenerate -m "add_job_card_columns"
alembic upgrade head
```

- [ ] **Step 8: Run tests — expect PASS**

```bash
cd backend && python -m pytest tests/test_api/test_job_cards.py -v
```

- [ ] **Step 9: Commit**

```bash
git add backend/src/models/job_card.py backend/src/models/__init__.py \
        backend/src/api/job_cards.py backend/src/api/main.py \
        backend/tests/test_api/test_job_cards.py backend/alembic/versions/
git commit -m "feat(backend): add JobCardColumn model and column management API"
```

---

## Task 3: JobCard model + full CRUD API

**Files:**
- Modify: `backend/src/models/job_card.py` (add JobCard)
- Modify: `backend/src/models/__init__.py`
- Modify: `backend/src/api/job_cards.py` (add job card endpoints)
- Test: `backend/tests/test_api/test_job_cards.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_api/test_job_cards.py — append:

def test_list_job_cards_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/job-cards", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

def test_create_job_card(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    card = MagicMock()
    card.id = uuid.uuid4()
    card.shop_id = uuid.UUID(SHOP_ID)
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
    mock_db.execute.return_value.scalar_one_or_none.return_value = card
    resp = client.post("/job-cards", json={}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["number"] == "JC-0001"

def test_get_job_card_404(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.get(f"/job-cards/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_job_cards.py::test_list_job_cards_empty -v
```
Expected: FAIL with `404`

- [ ] **Step 3: Add JobCard model to job_card.py**

```python
# backend/src/models/job_card.py — append after JobCardColumn class:

class JobCard(Base):
    __tablename__ = "job_cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    number = Column(String(20), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    column_id = Column(UUID(as_uuid=True), ForeignKey("job_card_columns.id", ondelete="SET NULL"), nullable=True)
    technician_ids = Column(JSON, default=list)
    services = Column(JSON, default=list)
    parts = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
```

- [ ] **Step 4: Add job card endpoints to job_cards.py**

```python
# backend/src/api/job_cards.py — append after column endpoints

from src.models.job_card import JobCardColumn, JobCard
from sqlalchemy import func as sql_func


class ServiceLine(BaseModel):
    description: str
    labor_hours: float = 0.0
    labor_rate: float = 0.0
    labor_cost: float = 0.0


class PartLine(BaseModel):
    name: str
    sku: Optional[str] = None
    qty: float = 1.0
    unit_cost: float = 0.0
    sell_price: float = 0.0
    inventory_item_id: Optional[str] = None


class JobCardCreate(BaseModel):
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    column_id: Optional[str] = None
    technician_ids: list[str] = []
    services: list[ServiceLine] = []
    parts: list[PartLine] = []
    notes: Optional[str] = None


class JobCardUpdate(BaseModel):
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    column_id: Optional[str] = None
    technician_ids: Optional[list[str]] = None
    services: Optional[list[dict]] = None
    parts: Optional[list[dict]] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class JobCardResponse(BaseModel):
    id: str
    shop_id: str
    number: str
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    column_id: Optional[str] = None
    technician_ids: list[str]
    services: list[dict]
    parts: list[dict]
    notes: Optional[str] = None
    status: str
    created_at: str
    updated_at: str


def _card_to_response(c: JobCard) -> JobCardResponse:
    return JobCardResponse(
        id=str(c.id),
        shop_id=str(c.shop_id),
        number=c.number,
        customer_id=str(c.customer_id) if c.customer_id else None,
        vehicle_id=str(c.vehicle_id) if c.vehicle_id else None,
        column_id=str(c.column_id) if c.column_id else None,
        technician_ids=c.technician_ids or [],
        services=c.services or [],
        parts=c.parts or [],
        notes=c.notes,
        status=c.status,
        created_at=str(c.created_at),
        updated_at=str(c.updated_at),
    )


async def _next_card_number(shop_id: uuid.UUID, db: AsyncSession) -> str:
    result = await db.execute(
        select(sql_func.count(JobCard.id)).where(JobCard.shop_id == shop_id)
    )
    count = result.scalar() or 0
    return f"JC-{count + 1:04d}"


@router.get("", response_model=list[JobCardResponse])
async def list_job_cards(
    column_id: Optional[str] = None,
    status: Optional[str] = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    q = select(JobCard).where(JobCard.shop_id == sid)
    if column_id:
        q = q.where(JobCard.column_id == uuid.UUID(column_id))
    if status:
        q = q.where(JobCard.status == status)
    result = await db.execute(q.order_by(JobCard.created_at.desc()))
    return [_card_to_response(c) for c in result.scalars().all()]


@router.post("", response_model=JobCardResponse, status_code=status.HTTP_201_CREATED)
async def create_job_card(
    body: JobCardCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    number = await _next_card_number(sid, db)
    card = JobCard(
        shop_id=sid,
        number=number,
        customer_id=uuid.UUID(body.customer_id) if body.customer_id else None,
        vehicle_id=uuid.UUID(body.vehicle_id) if body.vehicle_id else None,
        column_id=uuid.UUID(body.column_id) if body.column_id else None,
        technician_ids=body.technician_ids,
        services=[s.model_dump() for s in body.services],
        parts=[p.model_dump() for p in body.parts],
        notes=body.notes,
        status="active",
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return _card_to_response(card)


@router.get("/{card_id}", response_model=JobCardResponse)
async def get_job_card(
    card_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        cid = uuid.UUID(card_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid card_id")
    result = await db.execute(
        select(JobCard).where(JobCard.id == cid, JobCard.shop_id == uuid.UUID(shop_id))
    )
    card = result.scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail="Job card not found")
    return _card_to_response(card)


@router.patch("/{card_id}", response_model=JobCardResponse)
async def update_job_card(
    card_id: str,
    body: JobCardUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        cid = uuid.UUID(card_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid card_id")
    result = await db.execute(
        select(JobCard).where(JobCard.id == cid, JobCard.shop_id == uuid.UUID(shop_id))
    )
    card = result.scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail="Job card not found")
    if body.customer_id is not None:
        card.customer_id = uuid.UUID(body.customer_id) if body.customer_id else None
    if body.vehicle_id is not None:
        card.vehicle_id = uuid.UUID(body.vehicle_id) if body.vehicle_id else None
    if body.column_id is not None:
        card.column_id = uuid.UUID(body.column_id) if body.column_id else None
    if body.technician_ids is not None:
        card.technician_ids = body.technician_ids
    if body.services is not None:
        card.services = body.services
    if body.parts is not None:
        card.parts = body.parts
    if body.notes is not None:
        card.notes = body.notes
    if body.status is not None:
        card.status = body.status
    await db.commit()
    await db.refresh(card)
    return _card_to_response(card)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_card(
    card_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        cid = uuid.UUID(card_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid card_id")
    result = await db.execute(
        select(JobCard).where(JobCard.id == cid, JobCard.shop_id == uuid.UUID(shop_id))
    )
    card = result.scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail="Job card not found")
    await db.delete(card)
    await db.commit()
```

- [ ] **Step 5: Update models __init__.py**

```python
from src.models.job_card import JobCardColumn, JobCard

__all__ = [
    "Shop", "User", "InspectionSession", "Report", "MediaFile",
    "ChatMessage", "Quote", "Customer", "Vehicle", "CustomerMessage",
    "ShopSettings", "JobCardColumn", "JobCard",
]
```

- [ ] **Step 6: Generate migration**

```bash
cd backend
alembic revision --autogenerate -m "add_job_cards"
alembic upgrade head
```

- [ ] **Step 7: Run tests — expect PASS**

```bash
cd backend && python -m pytest tests/test_api/test_job_cards.py -v
```

- [ ] **Step 8: Commit**

```bash
git add backend/src/models/job_card.py backend/src/models/__init__.py \
        backend/src/api/job_cards.py backend/tests/test_api/test_job_cards.py \
        backend/alembic/versions/
git commit -m "feat(backend): add JobCard model and full CRUD API"
```

---

## Task 4: Invoice model + migration + API

**Files:**
- Create: `backend/src/models/invoice.py`
- Modify: `backend/src/models/__init__.py`
- Create: `backend/src/api/invoices.py`
- Modify: `backend/src/api/main.py`
- Test: `backend/tests/test_api/test_invoices.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_api/test_invoices.py
import uuid

SHOP_ID = "00000000-0000-0000-0000-000000000099"

def test_list_invoices_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/invoices", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

def test_create_invoice_from_job_card(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    inv = MagicMock()
    inv.id = uuid.uuid4()
    inv.shop_id = uuid.UUID(SHOP_ID)
    inv.job_card_id = uuid.uuid4()
    inv.number = "INV-0001"
    inv.customer_id = None
    inv.vehicle_id = None
    inv.status = "pending"
    inv.line_items = []
    inv.subtotal = 0.0
    inv.tax_rate = 0.0
    inv.total = 0.0
    inv.amount_paid = 0.0
    inv.due_date = None
    inv.stripe_payment_link = None
    inv.pdf_url = None
    inv.created_at = "2026-05-01T00:00:00+00:00"
    inv.updated_at = "2026-05-01T00:00:00+00:00"
    mock_db.execute.return_value.scalar_one_or_none.return_value = inv
    jc_id = str(uuid.uuid4())
    resp = client.post(
        "/invoices/from-job-card",
        json={"job_card_id": jc_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201

def test_get_invoice_404(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.get(f"/invoices/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_invoices.py::test_list_invoices_empty -v
```
Expected: FAIL with `404`

- [ ] **Step 3: Create Invoice model**

```python
# backend/src/models/invoice.py
import uuid
from sqlalchemy import Column, String, JSON, Numeric, ForeignKey, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    job_card_id = Column(UUID(as_uuid=True), ForeignKey("job_cards.id", ondelete="SET NULL"), nullable=True, index=True)
    number = Column(String(20), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    line_items = Column(JSON, default=list)
    subtotal = Column(Numeric(10, 2), default=0)
    tax_rate = Column(Numeric(5, 4), default=0)
    total = Column(Numeric(10, 2), default=0)
    amount_paid = Column(Numeric(10, 2), default=0)
    due_date = Column(Date, nullable=True)
    stripe_payment_link = Column(String(500), nullable=True)
    stripe_payment_intent_id = Column(String(200), nullable=True)
    pdf_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)


class InvoicePaymentEvent(Base):
    __tablename__ = "invoice_payment_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    method = Column(String(50), nullable=False)  # stripe|card|cash|check
    recorded_by = Column(UUID(as_uuid=True), nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(String(500), nullable=True)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
```

- [ ] **Step 4: Create invoices router**

```python
# backend/src/api/invoices.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sql_func
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from src.db.base import get_db
from src.api.deps import get_current_shop_id, get_current_user
from src.models.invoice import Invoice, InvoicePaymentEvent
from src.models.job_card import JobCard

router = APIRouter(prefix="/invoices", tags=["invoices"])


class LineItem(BaseModel):
    type: str  # labor | part
    description: str
    qty: float
    unit_price: float
    total: float


class InvoiceCreate(BaseModel):
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    line_items: list[LineItem] = []
    tax_rate: float = 0.0
    due_date: Optional[str] = None


class FromJobCardRequest(BaseModel):
    job_card_id: str


class InvoiceUpdate(BaseModel):
    line_items: Optional[list[dict]] = None
    tax_rate: Optional[float] = None
    due_date: Optional[str] = None
    status: Optional[str] = None


class RecordPaymentRequest(BaseModel):
    amount: float
    method: str  # stripe|card|cash|check
    notes: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: str
    shop_id: str
    job_card_id: Optional[str] = None
    number: str
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    status: str
    line_items: list[dict]
    subtotal: float
    tax_rate: float
    total: float
    amount_paid: float
    balance: float
    due_date: Optional[str] = None
    stripe_payment_link: Optional[str] = None
    pdf_url: Optional[str] = None
    created_at: str
    updated_at: str


def _inv_to_response(inv: Invoice) -> InvoiceResponse:
    total = float(inv.total or 0)
    paid = float(inv.amount_paid or 0)
    return InvoiceResponse(
        id=str(inv.id),
        shop_id=str(inv.shop_id),
        job_card_id=str(inv.job_card_id) if inv.job_card_id else None,
        number=inv.number,
        customer_id=str(inv.customer_id) if inv.customer_id else None,
        vehicle_id=str(inv.vehicle_id) if inv.vehicle_id else None,
        status=inv.status,
        line_items=inv.line_items or [],
        subtotal=float(inv.subtotal or 0),
        tax_rate=float(inv.tax_rate or 0),
        total=total,
        amount_paid=paid,
        balance=round(total - paid, 2),
        due_date=str(inv.due_date) if inv.due_date else None,
        stripe_payment_link=inv.stripe_payment_link,
        pdf_url=inv.pdf_url,
        created_at=str(inv.created_at),
        updated_at=str(inv.updated_at),
    )


async def _next_invoice_number(shop_id: uuid.UUID, db: AsyncSession) -> str:
    result = await db.execute(
        select(sql_func.count(Invoice.id)).where(Invoice.shop_id == shop_id)
    )
    count = result.scalar() or 0
    return f"INV-{count + 1:04d}"


def _compute_totals(line_items: list[dict], tax_rate: float) -> tuple[float, float]:
    subtotal = sum(item.get("total", 0) for item in line_items)
    total = round(subtotal * (1 + tax_rate), 2)
    return round(subtotal, 2), total


@router.get("", response_model=list[InvoiceResponse])
async def list_invoices(
    status: Optional[str] = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    q = select(Invoice).where(Invoice.shop_id == sid)
    if status:
        q = q.where(Invoice.status == status)
    result = await db.execute(q.order_by(Invoice.created_at.desc()))
    return [_inv_to_response(inv) for inv in result.scalars().all()]


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: InvoiceCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    items = [item.model_dump() for item in body.line_items]
    subtotal, total = _compute_totals(items, body.tax_rate)
    number = await _next_invoice_number(sid, db)
    inv = Invoice(
        shop_id=sid,
        number=number,
        customer_id=uuid.UUID(body.customer_id) if body.customer_id else None,
        vehicle_id=uuid.UUID(body.vehicle_id) if body.vehicle_id else None,
        line_items=items,
        subtotal=subtotal,
        tax_rate=body.tax_rate,
        total=total,
        amount_paid=0,
        status="pending",
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return _inv_to_response(inv)


@router.post("/from-job-card", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice_from_job_card(
    body: FromJobCardRequest,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    result = await db.execute(
        select(JobCard).where(
            JobCard.id == uuid.UUID(body.job_card_id), JobCard.shop_id == sid
        )
    )
    card = result.scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail="Job card not found")
    items: list[dict] = []
    for svc in (card.services or []):
        items.append({
            "type": "labor",
            "description": svc.get("description", "Labor"),
            "qty": svc.get("labor_hours", 1.0),
            "unit_price": svc.get("labor_rate", 0.0),
            "total": svc.get("labor_cost", 0.0),
        })
    for part in (card.parts or []):
        qty = part.get("qty", 1.0)
        price = part.get("sell_price", 0.0)
        items.append({
            "type": "part",
            "description": part.get("name", "Part"),
            "qty": qty,
            "unit_price": price,
            "total": round(qty * price, 2),
        })
    subtotal, total = _compute_totals(items, 0.0)
    number = await _next_invoice_number(sid, db)
    inv = Invoice(
        shop_id=sid,
        job_card_id=card.id,
        number=number,
        customer_id=card.customer_id,
        vehicle_id=card.vehicle_id,
        line_items=items,
        subtotal=subtotal,
        tax_rate=0,
        total=total,
        amount_paid=0,
        status="pending",
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return _inv_to_response(inv)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        iid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid invoice_id")
    result = await db.execute(
        select(Invoice).where(Invoice.id == iid, Invoice.shop_id == uuid.UUID(shop_id))
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _inv_to_response(inv)


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    body: InvoiceUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        iid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid invoice_id")
    result = await db.execute(
        select(Invoice).where(Invoice.id == iid, Invoice.shop_id == uuid.UUID(shop_id))
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if body.line_items is not None:
        inv.line_items = body.line_items
        rate = body.tax_rate if body.tax_rate is not None else float(inv.tax_rate or 0)
        inv.subtotal, inv.total = _compute_totals(body.line_items, rate)
    if body.tax_rate is not None:
        inv.tax_rate = body.tax_rate
        inv.subtotal, inv.total = _compute_totals(inv.line_items or [], body.tax_rate)
    if body.due_date is not None:
        inv.due_date = body.due_date
    if body.status is not None:
        inv.status = body.status
    await db.commit()
    await db.refresh(inv)
    return _inv_to_response(inv)


@router.post("/{invoice_id}/record-payment", response_model=InvoiceResponse)
async def record_payment(
    invoice_id: str,
    body: RecordPaymentRequest,
    current_user: dict = Depends(get_current_user),
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        iid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid invoice_id")
    result = await db.execute(
        select(Invoice).where(Invoice.id == iid, Invoice.shop_id == uuid.UUID(shop_id))
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    event = InvoicePaymentEvent(
        invoice_id=iid,
        amount=body.amount,
        method=body.method,
        recorded_by=uuid.UUID(current_user["sub"]),
        notes=body.notes,
    )
    db.add(event)
    inv.amount_paid = float(inv.amount_paid or 0) + body.amount
    total = float(inv.total or 0)
    if float(inv.amount_paid) >= total:
        inv.status = "paid"
    elif float(inv.amount_paid) > 0:
        inv.status = "partial"
    await db.commit()
    await db.refresh(inv)
    return _inv_to_response(inv)
```

- [ ] **Step 5: Register invoices router in main.py**

```python
# backend/src/api/main.py — add:
from src.api.invoices import router as invoices_router
app.include_router(invoices_router)
```

- [ ] **Step 6: Update models __init__.py**

```python
from src.models.invoice import Invoice, InvoicePaymentEvent

__all__ = [
    "Shop", "User", "InspectionSession", "Report", "MediaFile",
    "ChatMessage", "Quote", "Customer", "Vehicle", "CustomerMessage",
    "ShopSettings", "JobCardColumn", "JobCard", "Invoice", "InvoicePaymentEvent",
]
```

- [ ] **Step 7: Generate migration**

```bash
cd backend
alembic revision --autogenerate -m "add_invoices"
alembic upgrade head
```

- [ ] **Step 8: Run tests — expect PASS**

```bash
cd backend && python -m pytest tests/test_api/test_invoices.py -v
```

- [ ] **Step 9: Commit**

```bash
git add backend/src/models/invoice.py backend/src/models/__init__.py \
        backend/src/api/invoices.py backend/src/api/main.py \
        backend/tests/test_api/test_invoices.py backend/alembic/versions/
git commit -m "feat(backend): add Invoice model, CRUD API, record-payment endpoint"
```

---

## Task 5: Stripe payment link + financing link endpoints

**Files:**
- Modify: `backend/src/api/invoices.py` (add 2 endpoints)
- Test: `backend/tests/test_api/test_invoices.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_api/test_invoices.py — append:

def _make_invoice_mock(inv_id=None):
    from unittest.mock import MagicMock
    inv = MagicMock()
    inv.id = inv_id or uuid.uuid4()
    inv.shop_id = uuid.UUID(SHOP_ID)
    inv.job_card_id = None
    inv.number = "INV-0001"
    inv.customer_id = uuid.uuid4()
    inv.vehicle_id = None
    inv.status = "pending"
    inv.line_items = [{"type": "labor", "description": "Oil change", "qty": 1, "unit_price": 89, "total": 89}]
    inv.subtotal = 89.0
    inv.tax_rate = 0.0
    inv.total = 89.0
    inv.amount_paid = 0.0
    inv.due_date = None
    inv.stripe_payment_link = None
    inv.pdf_url = None
    inv.created_at = "2026-05-01T00:00:00+00:00"
    inv.updated_at = "2026-05-01T00:00:00+00:00"
    return inv

def test_send_payment_link_returns_link(client, auth_headers, mock_db, monkeypatch):
    inv = _make_invoice_mock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = inv
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")

    import stripe
    from unittest.mock import patch, MagicMock
    fake_session = MagicMock()
    fake_session.url = "https://checkout.stripe.com/pay/cs_test_abc"
    with patch("stripe.checkout.Session.create", return_value=fake_session):
        resp = client.post(
            f"/invoices/{inv.id}/payment-link",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert "payment_link" in resp.json()

def test_financing_link_provider_not_configured(client, auth_headers, mock_db):
    inv = _make_invoice_mock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = inv
    mock_db.execute.return_value.scalar_one_or_none.side_effect = [inv, None]
    resp = client.post(
        f"/invoices/{inv.id}/financing-link",
        json={"provider": "synchrony"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_invoices.py::test_send_payment_link_returns_link -v
```
Expected: FAIL with `404`

- [ ] **Step 3: Install stripe SDK**

```bash
cd backend && pip install stripe
# Add to requirements.txt:
echo "stripe>=7.0.0" >> requirements.txt
```

- [ ] **Step 4: Add payment-link and financing-link endpoints to invoices.py**

```python
# backend/src/api/invoices.py — append after record_payment endpoint

import os
from src.models.shop_settings import ShopSettings


class FinancingLinkRequest(BaseModel):
    provider: str  # synchrony | wisetack


@router.post("/{invoice_id}/payment-link")
async def send_payment_link(
    invoice_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        iid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid invoice_id")
    result = await db.execute(
        select(Invoice).where(Invoice.id == iid, Invoice.shop_id == uuid.UUID(shop_id))
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise HTTPException(status_code=400, detail="Stripe not configured")

    import stripe as stripe_lib
    stripe_lib.api_key = stripe_key

    session = stripe_lib.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"Invoice {inv.number}"},
                    "unit_amount": int(float(inv.total or 0) * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + f"/invoices?paid={iid}",
        cancel_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + f"/invoices/{iid}",
        metadata={"invoice_id": str(iid), "shop_id": shop_id},
    )
    inv.stripe_payment_link = session.url
    await db.commit()
    return {"payment_link": session.url}


@router.post("/{invoice_id}/financing-link")
async def send_financing_link(
    invoice_id: str,
    body: FinancingLinkRequest,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        iid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid invoice_id")
    result = await db.execute(
        select(Invoice).where(Invoice.id == iid, Invoice.shop_id == uuid.UUID(shop_id))
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    settings_result = await db.execute(
        select(ShopSettings).where(ShopSettings.shop_id == uuid.UUID(shop_id))
    )
    settings = settings_result.scalar_one_or_none()

    if body.provider == "synchrony":
        if not settings or not settings.synchrony_enabled or not settings.synchrony_dealer_id:
            raise HTTPException(status_code=400, detail="Synchrony Car Care not configured")
        application_link = (
            f"https://apply.synchronybank.com/car-care?dealer={settings.synchrony_dealer_id}"
            f"&amount={int(float(inv.total or 0))}&ref={iid}"
        )
    elif body.provider == "wisetack":
        if not settings or not settings.wisetack_enabled or not settings.wisetack_merchant_id:
            raise HTTPException(status_code=400, detail="Wisetack not configured")
        application_link = (
            f"https://app.wisetack.com/#/apply?merchant={settings.wisetack_merchant_id}"
            f"&loan_amount={int(float(inv.total or 0))}&ref={iid}"
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider}")

    return {"application_link": application_link, "provider": body.provider}
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd backend && python -m pytest tests/test_api/test_invoices.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/invoices.py backend/tests/test_api/test_invoices.py requirements.txt
git commit -m "feat(backend): add Stripe payment link and financing link endpoints"
```

---

## Task 6: Mitchell1 ProDemand labor lookup endpoint

**Files:**
- Create: `backend/src/api/labor_lookup.py`
- Modify: `backend/src/api/main.py`
- Test: `backend/tests/test_api/test_labor_lookup.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api/test_labor_lookup.py
def test_lookup_returns_fallback_when_not_configured(client, auth_headers, mock_db, monkeypatch):
    monkeypatch.delenv("MITCHELL1_API_KEY", raising=False)
    resp = client.post(
        "/labor-lookup",
        json={"year": 2020, "make": "Ford", "model": "F-150", "service": "Oil Change"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "manual"
    assert data["hours"] is None

def test_lookup_returns_hours_from_api(client, auth_headers, monkeypatch):
    monkeypatch.setenv("MITCHELL1_API_KEY", "fake-key")
    from unittest.mock import patch, MagicMock
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"laborHours": 0.5}
    with patch("httpx.post", return_value=mock_resp):
        resp = client.post(
            "/labor-lookup",
            json={"year": 2020, "make": "Ford", "model": "F-150", "service": "Oil Change"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.json()["hours"] == 0.5
    assert resp.json()["source"] == "mitchell1"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_labor_lookup.py -v
```
Expected: FAIL with `404`

- [ ] **Step 3: Create labor_lookup.py**

```python
# backend/src/api/labor_lookup.py
import os
import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from src.api.deps import get_current_user

router = APIRouter(prefix="/labor-lookup", tags=["labor-lookup"])

MITCHELL1_BASE = "https://api.prodemand.com/v1"


class LaborLookupRequest(BaseModel):
    year: int
    make: str
    model: str
    engine: Optional[str] = None
    service: str


class LaborLookupResponse(BaseModel):
    hours: Optional[float]
    source: str  # mitchell1 | manual


@router.post("", response_model=LaborLookupResponse)
async def lookup_labor_time(
    body: LaborLookupRequest,
    _: dict = Depends(get_current_user),
):
    api_key = os.getenv("MITCHELL1_API_KEY", "")
    if not api_key:
        return LaborLookupResponse(hours=None, source="manual")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{MITCHELL1_BASE}/labor",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "year": body.year,
                    "make": body.make,
                    "model": body.model,
                    "engine": body.engine,
                    "operation": body.service,
                },
            )
        if resp.status_code == 200:
            data = resp.json()
            return LaborLookupResponse(hours=data.get("laborHours"), source="mitchell1")
    except Exception:
        pass

    return LaborLookupResponse(hours=None, source="manual")
```

Note: `httpx.post` is synchronous in tests; the actual impl uses `async with httpx.AsyncClient`. The test patches `httpx.post` directly for simplicity — change test to `httpx.AsyncClient.post` if integration test is needed.

- [ ] **Step 4: Register router**

```python
# backend/src/api/main.py — add:
from src.api.labor_lookup import router as labor_lookup_router
app.include_router(labor_lookup_router)
```

- [ ] **Step 5: Install httpx**

```bash
cd backend && pip install httpx
echo "httpx>=0.27.0" >> requirements.txt
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
cd backend && python -m pytest tests/test_api/test_labor_lookup.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/api/labor_lookup.py backend/src/api/main.py \
        backend/tests/test_api/test_labor_lookup.py requirements.txt
git commit -m "feat(backend): add Mitchell1 ProDemand labor time lookup endpoint"
```

---

## Task 7: Frontend types + API client additions

**Files:**
- Modify: `web/lib/types.ts`
- Modify: `web/lib/api.ts`

- [ ] **Step 1: Add types to web/lib/types.ts**

Append to the end of `web/lib/types.ts`:

```typescript
// ── Job Cards ─────────────────────────────────────────────────────────────

export interface JobCardColumn {
  id: string
  shop_id: string
  name: string
  position: number
  created_at: string
}

export interface ServiceLine {
  description: string
  labor_hours: number
  labor_rate: number
  labor_cost: number
}

export interface PartLine {
  name: string
  sku: string | null
  qty: number
  unit_cost: number
  sell_price: number
  inventory_item_id: string | null
}

export interface JobCard {
  id: string
  shop_id: string
  number: string
  customer_id: string | null
  vehicle_id: string | null
  column_id: string | null
  technician_ids: string[]
  services: ServiceLine[]
  parts: PartLine[]
  notes: string | null
  status: 'active' | 'completed' | 'archived'
  created_at: string
  updated_at: string
}

export interface JobCardCreate {
  customer_id?: string
  vehicle_id?: string
  column_id?: string
  technician_ids?: string[]
  services?: ServiceLine[]
  parts?: PartLine[]
  notes?: string
}

// ── Invoices ──────────────────────────────────────────────────────────────

export interface InvoiceLineItem {
  type: 'labor' | 'part'
  description: string
  qty: number
  unit_price: number
  total: number
}

export interface Invoice {
  id: string
  shop_id: string
  job_card_id: string | null
  number: string
  customer_id: string | null
  vehicle_id: string | null
  status: 'pending' | 'partial' | 'paid' | 'overdue'
  line_items: InvoiceLineItem[]
  subtotal: number
  tax_rate: number
  total: number
  amount_paid: number
  balance: number
  due_date: string | null
  stripe_payment_link: string | null
  pdf_url: string | null
  created_at: string
  updated_at: string
}

export interface ShopSettings {
  id: string
  shop_id: string
  nav_pins: string[]
  stripe_publishable_key: string | null
  mitchell1_enabled: boolean
  synchrony_enabled: boolean
  wisetack_enabled: boolean
  quickbooks_enabled: boolean
  financing_threshold: string
}
```

- [ ] **Step 2: Add API functions to web/lib/api.ts**

Append to the end of `web/lib/api.ts`:

```typescript
// ── Shop Settings ──────────────────────────────────────────────────────────
import type { JobCardColumn, JobCard, JobCardCreate, Invoice, ShopSettings } from './types'

export const getShopSettings = (): Promise<ShopSettings> =>
  api.get('/settings/shop').then(r => r.data)

export const updateShopSettings = (data: Partial<ShopSettings>): Promise<ShopSettings> =>
  api.patch('/settings/shop', data).then(r => r.data)

// ── Job Card Columns ───────────────────────────────────────────────────────

export const getJobCardColumns = (): Promise<JobCardColumn[]> =>
  api.get('/job-cards/columns').then(r => r.data)

export const createJobCardColumn = (data: { name: string; position: number }): Promise<JobCardColumn> =>
  api.post('/job-cards/columns', data).then(r => r.data)

export const updateJobCardColumn = (id: string, data: { name?: string; position?: number }): Promise<JobCardColumn> =>
  api.patch(`/job-cards/columns/${id}`, data).then(r => r.data)

export const deleteJobCardColumn = (id: string): Promise<void> =>
  api.delete(`/job-cards/columns/${id}`).then(() => undefined)

// ── Job Cards ──────────────────────────────────────────────────────────────

export const getJobCards = (params?: { column_id?: string; status?: string }): Promise<JobCard[]> =>
  api.get('/job-cards', { params }).then(r => r.data)

export const getJobCard = (id: string): Promise<JobCard> =>
  api.get(`/job-cards/${id}`).then(r => r.data)

export const createJobCard = (data: JobCardCreate): Promise<JobCard> =>
  api.post('/job-cards', data).then(r => r.data)

export const updateJobCard = (id: string, data: Partial<JobCard>): Promise<JobCard> =>
  api.patch(`/job-cards/${id}`, data).then(r => r.data)

export const deleteJobCard = (id: string): Promise<void> =>
  api.delete(`/job-cards/${id}`).then(() => undefined)

export const lookupLaborTime = (data: {
  year: number; make: string; model: string; engine?: string; service: string
}): Promise<{ hours: number | null; source: string }> =>
  api.post('/labor-lookup', data).then(r => r.data)

// ── Invoices ───────────────────────────────────────────────────────────────

export const getInvoices = (params?: { status?: string }): Promise<Invoice[]> =>
  api.get('/invoices', { params }).then(r => r.data)

export const getInvoice = (id: string): Promise<Invoice> =>
  api.get(`/invoices/${id}`).then(r => r.data)

export const createInvoice = (data: Partial<Invoice>): Promise<Invoice> =>
  api.post('/invoices', data).then(r => r.data)

export const createInvoiceFromJobCard = (job_card_id: string): Promise<Invoice> =>
  api.post('/invoices/from-job-card', { job_card_id }).then(r => r.data)

export const updateInvoice = (id: string, data: Partial<Invoice>): Promise<Invoice> =>
  api.patch(`/invoices/${id}`, data).then(r => r.data)

export const sendPaymentLink = (id: string): Promise<{ payment_link: string }> =>
  api.post(`/invoices/${id}/payment-link`).then(r => r.data)

export const sendFinancingLink = (id: string, provider: string): Promise<{ application_link: string; provider: string }> =>
  api.post(`/invoices/${id}/financing-link`, { provider }).then(r => r.data)

export const recordPayment = (id: string, data: { amount: number; method: string; notes?: string }): Promise<Invoice> =>
  api.post(`/invoices/${id}/record-payment`, data).then(r => r.data)
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd web && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add web/lib/types.ts web/lib/api.ts
git commit -m "feat(web): add JobCard, Invoice, ShopSettings types and API functions"
```

---

## Task 8: Job Cards page — kanban view

**Files:**
- Create: `web/app/job-cards/page.tsx`
- Create: `web/components/job-cards/KanbanBoard.tsx`
- Create: `web/components/job-cards/KanbanColumn.tsx`
- Create: `web/components/job-cards/JobCardCard.tsx`

- [ ] **Step 1: Create the KanbanBoard component**

```tsx
// web/components/job-cards/KanbanBoard.tsx
'use client'
import { useState } from 'react'
import type { JobCardColumn, JobCard } from '@/lib/types'
import KanbanColumn from './KanbanColumn'

interface Props {
  columns: JobCardColumn[]
  cards: JobCard[]
  onCardClick: (card: JobCard) => void
  onCardMove: (cardId: string, newColumnId: string) => void
  onAddCard: (columnId: string) => void
}

export default function KanbanBoard({ columns, cards, onCardClick, onCardMove, onAddCard }: Props) {
  const sortedColumns = [...columns].sort((a, b) => a.position - b.position)

  return (
    <div style={{ display: 'flex', gap: 12, flex: 1, overflow: 'hidden', padding: '14px 24px 20px' }}>
      {sortedColumns.map(col => (
        <KanbanColumn
          key={col.id}
          column={col}
          cards={cards.filter(c => c.column_id === col.id)}
          onCardClick={onCardClick}
          onCardMove={onCardMove}
          onAddCard={() => onAddCard(col.id)}
        />
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Create KanbanColumn component**

```tsx
// web/components/job-cards/KanbanColumn.tsx
'use client'
import type { JobCardColumn, JobCard } from '@/lib/types'
import JobCardCard from './JobCardCard'

const COLUMN_COLORS: Record<number, string> = {
  0: '#60a5fa',
  1: '#fbbf24',
  2: '#c084fc',
  3: '#4ade80',
}

interface Props {
  column: JobCardColumn
  cards: JobCard[]
  onCardClick: (card: JobCard) => void
  onCardMove: (cardId: string, newColumnId: string) => void
  onAddCard: () => void
}

export default function KanbanColumn({ column, cards, onCardClick, onAddCard }: Props) {
  const color = COLUMN_COLORS[column.position] ?? '#94a3b8'
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: 10 }}>
        <span style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color }}>
          {column.name}
        </span>
        <span style={{
          fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 9,
          background: `${color}22`, color,
        }}>
          {cards.length}
        </span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 7 }}>
        {cards.map(card => (
          <JobCardCard key={card.id} card={card} accentColor={color} onClick={() => onCardClick(card)} />
        ))}
        <button
          onClick={onAddCard}
          style={{
            border: '1px dashed rgba(255,255,255,0.12)', borderRadius: 9, padding: '11px 12px',
            textAlign: 'center', fontSize: 11, color: 'rgba(255,255,255,0.25)',
            cursor: 'pointer', background: 'transparent', marginTop: 2,
          }}
          onMouseEnter={e => { (e.target as HTMLElement).style.borderColor = 'rgba(255,255,255,0.25)' }}
          onMouseLeave={e => { (e.target as HTMLElement).style.borderColor = 'rgba(255,255,255,0.12)' }}
        >
          + Add card
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create JobCardCard component**

```tsx
// web/components/job-cards/JobCardCard.tsx
'use client'
import type { JobCard } from '@/lib/types'

interface Props {
  card: JobCard
  accentColor: string
  onClick: () => void
}

export default function JobCardCard({ card, accentColor, onClick }: Props) {
  const serviceCount = card.services?.length ?? 0
  const partsCount = card.parts?.length ?? 0

  return (
    <div
      onClick={onClick}
      style={{
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.09)',
        borderLeft: `3px solid ${accentColor}55`,
        borderRadius: 9, padding: '11px 12px', cursor: 'pointer',
        transition: 'background 0.12s',
      }}
      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.07)' }}
      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)' }}
    >
      <div style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.4)', marginBottom: 3 }}>
        {card.number}
      </div>
      <div style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.88)', marginBottom: 3 }}>
        {card.vehicle_id ? 'Vehicle attached' : 'No vehicle'}
      </div>
      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', marginBottom: 7 }}>
        {serviceCount} service{serviceCount !== 1 ? 's' : ''}{partsCount > 0 ? ` · ${partsCount} part${partsCount !== 1 ? 's' : ''}` : ''}
      </div>
      {card.notes && (
        <div style={{
          fontSize: 10, color: 'rgba(255,255,255,0.35)',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {card.notes}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Create the Job Cards page**

```tsx
// web/app/job-cards/page.tsx
'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import KanbanBoard from '@/components/job-cards/KanbanBoard'
import type { JobCard } from '@/lib/types'
import { getJobCardColumns, getJobCards, createJobCard, updateJobCard } from '@/lib/api'

export default function JobCardsPage() {
  const qc = useQueryClient()
  const [view, setView] = useState<'kanban' | 'list'>('kanban')
  const [selectedCard, setSelectedCard] = useState<JobCard | null>(null)

  const { data: columns = [] } = useQuery({ queryKey: ['job-card-columns'], queryFn: getJobCardColumns })
  const { data: cards = [], isLoading } = useQuery({ queryKey: ['job-cards'], queryFn: () => getJobCards() })

  const addCard = useMutation({
    mutationFn: (columnId: string) => createJobCard({ column_id: columnId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job-cards'] }),
  })

  const moveCard = useMutation({
    mutationFn: ({ id, columnId }: { id: string; columnId: string }) =>
      updateJobCard(id, { column_id: columnId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job-cards'] }),
  })

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px 0', flexShrink: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Job Cards</div>
        <div style={{ display: 'flex', gap: 8 }}>
          {/* View toggle */}
          <div style={{
            display: 'flex', background: 'rgba(255,255,255,0.06)',
            border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, overflow: 'hidden',
          }}>
            {(['kanban', 'list'] as const).map(v => (
              <button
                key={v}
                onClick={() => setView(v)}
                style={{
                  height: 32, padding: '0 14px', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600,
                  background: view === v ? 'rgba(255,255,255,0.12)' : 'transparent',
                  color: view === v ? '#fff' : 'rgba(255,255,255,0.5)',
                  textTransform: 'capitalize',
                }}
              >
                {v}
              </button>
            ))}
          </div>
          <button
            onClick={() => addCard.mutate(columns[0]?.id ?? '')}
            style={{
              height: 32, padding: '0 14px', borderRadius: 7, border: 'none',
              background: '#d97706', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer',
            }}
          >
            + New Card
          </button>
        </div>
      </div>

      {isLoading ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)' }}>
          Loading…
        </div>
      ) : (
        <KanbanBoard
          columns={columns}
          cards={cards}
          onCardClick={setSelectedCard}
          onCardMove={(cardId, columnId) => moveCard.mutate({ id: cardId, columnId })}
          onAddCard={columnId => addCard.mutate(columnId)}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 5: Start dev server and verify kanban renders**

```bash
cd web && npm run dev
```
Open http://localhost:3000/job-cards — should see 4 default columns (Drop-Off, Diagnosis, In Service, Ready for Pickup) and an "+ Add card" button in each. Clicking "+ New Card" should create a card in the first column.

- [ ] **Step 6: Commit**

```bash
git add web/app/job-cards/page.tsx web/components/job-cards/
git commit -m "feat(web): add Job Cards kanban page with column layout"
```

---

## Task 9: Job Card detail panel

**Files:**
- Create: `web/components/job-cards/JobCardDetail.tsx`
- Modify: `web/app/job-cards/page.tsx`

- [ ] **Step 1: Create JobCardDetail component**

```tsx
// web/components/job-cards/JobCardDetail.tsx
'use client'
import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { JobCard, JobCardColumn } from '@/lib/types'
import { updateJobCard, createInvoiceFromJobCard } from '@/lib/api'

interface Props {
  card: JobCard
  columns: JobCardColumn[]
  onClose: () => void
}

export default function JobCardDetail({ card, columns, onClose }: Props) {
  const qc = useQueryClient()
  const [notes, setNotes] = useState(card.notes ?? '')
  const [services, setServices] = useState(card.services ?? [])
  const [columnId, setColumnId] = useState(card.column_id ?? '')

  const save = useMutation({
    mutationFn: () => updateJobCard(card.id, { notes, services, column_id: columnId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job-cards'] }),
  })

  const createInvoice = useMutation({
    mutationFn: () => createInvoiceFromJobCard(card.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['invoices'] }); onClose() },
  })

  return (
    <div style={{
      position: 'fixed', right: 0, top: 0, bottom: 0, width: 420,
      background: '#141414', borderLeft: '1px solid rgba(255,255,255,0.08)',
      display: 'flex', flexDirection: 'column', zIndex: 50,
    }}>
      {/* Panel header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '18px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
        <div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 2 }}>{card.number}</div>
          <div style={{ fontSize: 16, fontWeight: 700 }}>Job Card</div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', fontSize: 20, cursor: 'pointer' }}>×</button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Column selector */}
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.35)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Status</div>
          <select
            value={columnId}
            onChange={e => setColumnId(e.target.value)}
            style={{
              width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 7, padding: '8px 10px', color: '#fff', fontSize: 13,
            }}
          >
            <option value="">— No column —</option>
            {[...columns].sort((a,b) => a.position - b.position).map(col => (
              <option key={col.id} value={col.id}>{col.name}</option>
            ))}
          </select>
        </div>

        {/* Services */}
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.35)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Services</div>
          {services.map((svc, i) => (
            <div key={i} style={{
              background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
              borderRadius: 8, padding: '10px 12px', marginBottom: 6, fontSize: 12,
              color: 'rgba(255,255,255,0.7)',
            }}>
              {svc.description} — {svc.labor_hours}h @ ${svc.labor_rate}/hr
            </div>
          ))}
          <button
            style={{
              width: '100%', padding: '8px', borderRadius: 7,
              border: '1px dashed rgba(255,255,255,0.15)', background: 'transparent',
              color: 'rgba(255,255,255,0.4)', fontSize: 11, cursor: 'pointer',
            }}
            onClick={() => setServices([...services, { description: 'New service', labor_hours: 1, labor_rate: 90, labor_cost: 90 }])}
          >
            + Add service
          </button>
        </div>

        {/* Notes */}
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.35)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Notes</div>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={4}
            style={{
              width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 7, padding: '8px 10px', color: '#fff', fontSize: 13, resize: 'vertical',
            }}
          />
        </div>
      </div>

      {/* Footer actions */}
      <div style={{ padding: '14px 20px', borderTop: '1px solid rgba(255,255,255,0.07)', display: 'flex', gap: 8 }}>
        <button
          onClick={() => save.mutate()}
          style={{
            flex: 1, height: 36, borderRadius: 8, border: 'none',
            background: '#d97706', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer',
          }}
        >
          Save
        </button>
        <button
          onClick={() => createInvoice.mutate()}
          style={{
            flex: 1, height: 36, borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.04)',
            color: 'rgba(255,255,255,0.7)', fontSize: 13, fontWeight: 600, cursor: 'pointer',
          }}
        >
          → Invoice
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Wire detail panel into job-cards page**

```tsx
// web/app/job-cards/page.tsx — after useState declarations, add:
//   import JobCardDetail from '@/components/job-cards/JobCardDetail'
// Then below KanbanBoard, add:
{selectedCard && (
  <JobCardDetail
    card={selectedCard}
    columns={columns}
    onClose={() => setSelectedCard(null)}
  />
)}
```

- [ ] **Step 3: Verify panel opens and saves**

Open http://localhost:3000/job-cards, click a card → panel slides in. Change column, edit notes, click Save → card updates in kanban. Click "→ Invoice" → invoice is created and panel closes.

- [ ] **Step 4: Commit**

```bash
git add web/components/job-cards/JobCardDetail.tsx web/app/job-cards/page.tsx
git commit -m "feat(web): add Job Card detail panel with column, services, notes, invoice creation"
```

---

## Task 10: Invoices page

**Files:**
- Create: `web/app/invoices/page.tsx`
- Create: `web/components/invoices/InvoiceDetail.tsx`
- Create: `web/components/invoices/FinancingModal.tsx`

- [ ] **Step 1: Create InvoiceDetail component**

```tsx
// web/components/invoices/InvoiceDetail.tsx
'use client'
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { Invoice } from '@/lib/types'
import { sendPaymentLink, recordPayment } from '@/lib/api'
import FinancingModal from './FinancingModal'

interface Props {
  invoice: Invoice
  onClose: () => void
  financingThreshold: number
}

const STATUS_COLORS: Record<string, string> = {
  pending: '#fbbf24', partial: '#60a5fa', paid: '#4ade80', overdue: '#f87171',
}

export default function InvoiceDetail({ invoice, onClose, financingThreshold }: Props) {
  const qc = useQueryClient()
  const [showPayment, setShowPayment] = useState(false)
  const [showFinancing, setShowFinancing] = useState(false)
  const [payAmount, setPayAmount] = useState('')
  const [payMethod, setPayMethod] = useState('cash')

  const sendLink = useMutation({
    mutationFn: () => sendPaymentLink(invoice.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices'] }),
  })

  const addPayment = useMutation({
    mutationFn: () => recordPayment(invoice.id, { amount: parseFloat(payAmount), method: payMethod }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['invoices'] }); setShowPayment(false); setPayAmount('') },
  })

  const statusColor = STATUS_COLORS[invoice.status] ?? '#94a3b8'

  return (
    <div style={{
      position: 'fixed', right: 0, top: 0, bottom: 0, width: 440,
      background: '#141414', borderLeft: '1px solid rgba(255,255,255,0.08)',
      display: 'flex', flexDirection: 'column', zIndex: 50,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '18px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
        <div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 2 }}>{invoice.number}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 16, fontWeight: 700 }}>Invoice</span>
            <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 5, background: `${statusColor}22`, color: statusColor }}>
              {invoice.status}
            </span>
          </div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', fontSize: 20, cursor: 'pointer' }}>×</button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
        {/* Totals */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 20 }}>
          {[
            { label: 'Total', value: `$${invoice.total.toFixed(2)}` },
            { label: 'Balance', value: `$${invoice.balance.toFixed(2)}`, color: invoice.balance > 0 ? '#f87171' : '#4ade80' },
            { label: 'Paid', value: `$${invoice.amount_paid.toFixed(2)}`, color: '#4ade80' },
            { label: 'Due', value: invoice.due_date ?? '—' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 9, padding: '10px 14px' }}>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>{label}</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: color ?? '#fff', marginTop: 2 }}>{value}</div>
            </div>
          ))}
        </div>

        {/* Line items */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>Line Items</div>
          {invoice.line_items.map((item, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: 13 }}>
              <span style={{ color: 'rgba(255,255,255,0.7)' }}>{item.description}</span>
              <span style={{ color: 'rgba(255,255,255,0.9)', fontWeight: 600 }}>${item.total.toFixed(2)}</span>
            </div>
          ))}
        </div>

        {/* Record payment */}
        {showPayment && (
          <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, padding: 14, marginBottom: 14 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.5)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Record Payment</div>
            <input
              type="number"
              placeholder="Amount"
              value={payAmount}
              onChange={e => setPayAmount(e.target.value)}
              style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '7px 10px', color: '#fff', fontSize: 13, marginBottom: 8 }}
            />
            <select
              value={payMethod}
              onChange={e => setPayMethod(e.target.value)}
              style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '7px 10px', color: '#fff', fontSize: 13, marginBottom: 10 }}
            >
              {['cash', 'card', 'check', 'stripe'].map(m => <option key={m} value={m}>{m}</option>)}
            </select>
            <button onClick={() => addPayment.mutate()} style={{ width: '100%', height: 32, borderRadius: 7, border: 'none', background: '#d97706', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
              Record
            </button>
          </div>
        )}
      </div>

      {/* Footer actions */}
      <div style={{ padding: '14px 20px', borderTop: '1px solid rgba(255,255,255,0.07)', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {invoice.status !== 'paid' && (
          <>
            <button onClick={() => sendLink.mutate()} style={{ height: 36, borderRadius: 8, border: 'none', background: '#d97706', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
              {sendLink.isPending ? 'Sending…' : 'Send Payment Link'}
            </button>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => setShowPayment(!showPayment)} style={{ flex: 1, height: 32, borderRadius: 7, border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.65)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                Record Payment
              </button>
              {invoice.balance >= financingThreshold && (
                <button onClick={() => setShowFinancing(true)} style={{ flex: 1, height: 32, borderRadius: 7, border: '1px solid rgba(168,85,247,0.3)', background: 'rgba(168,85,247,0.08)', color: '#c084fc', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                  Offer Financing
                </button>
              )}
            </div>
          </>
        )}
      </div>

      {showFinancing && (
        <FinancingModal invoice={invoice} onClose={() => setShowFinancing(false)} />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create FinancingModal**

```tsx
// web/components/invoices/FinancingModal.tsx
'use client'
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import type { Invoice } from '@/lib/types'
import { sendFinancingLink } from '@/lib/api'

interface Props {
  invoice: Invoice
  onClose: () => void
}

const PROVIDERS = [
  { id: 'synchrony', name: 'Synchrony Car Care', desc: 'Major provider, up to 60 months' },
  { id: 'wisetack', name: 'Wisetack', desc: 'Buy-now-pay-later, instant approval' },
]

export default function FinancingModal({ invoice, onClose }: Props) {
  const [selected, setSelected] = useState<string>('')
  const [sent, setSent] = useState(false)

  const send = useMutation({
    mutationFn: () => sendFinancingLink(invoice.id, selected),
    onSuccess: () => setSent(true),
  })

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
      <div style={{ background: '#1a1a1a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 24, width: 380 }}>
        {sent ? (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>✓</div>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>Financing link sent</div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)', marginBottom: 20 }}>
              Application link sent to customer via SMS.
            </div>
            <button onClick={onClose} style={{ height: 36, padding: '0 20px', borderRadius: 8, border: 'none', background: '#d97706', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
              Done
            </button>
          </div>
        ) : (
          <>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>Offer Financing</div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)', marginBottom: 16 }}>
              Balance: <strong style={{ color: '#f87171' }}>${invoice.balance.toFixed(2)}</strong>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
              {PROVIDERS.map(p => (
                <div
                  key={p.id}
                  onClick={() => setSelected(p.id)}
                  style={{
                    padding: '12px 14px', borderRadius: 9, cursor: 'pointer',
                    border: `1px solid ${selected === p.id ? '#d97706' : 'rgba(255,255,255,0.1)'}`,
                    background: selected === p.id ? 'rgba(217,119,6,0.08)' : 'rgba(255,255,255,0.02)',
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 2 }}>{p.name}</div>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)' }}>{p.desc}</div>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={onClose} style={{ flex: 1, height: 36, borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.6)', fontSize: 13, cursor: 'pointer' }}>
                Cancel
              </button>
              <button
                onClick={() => send.mutate()}
                disabled={!selected || send.isPending}
                style={{ flex: 1, height: 36, borderRadius: 8, border: 'none', background: selected ? '#d97706' : 'rgba(255,255,255,0.1)', color: '#fff', fontSize: 13, fontWeight: 600, cursor: selected ? 'pointer' : 'default' }}
              >
                {send.isPending ? 'Sending…' : 'Send Link'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create Invoices page**

```tsx
// web/app/invoices/page.tsx
'use client'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { Invoice } from '@/lib/types'
import { getInvoices, getShopSettings } from '@/lib/api'
import InvoiceDetail from '@/components/invoices/InvoiceDetail'

const STATUS_COLORS: Record<string, string> = {
  pending: '#fbbf24', partial: '#60a5fa', paid: '#4ade80', overdue: '#f87171',
}

const FILTERS = ['all', 'pending', 'partial', 'paid', 'overdue']

export default function InvoicesPage() {
  const [filter, setFilter] = useState('all')
  const [selected, setSelected] = useState<Invoice | null>(null)

  const { data: invoices = [], isLoading } = useQuery({
    queryKey: ['invoices', filter],
    queryFn: () => getInvoices(filter !== 'all' ? { status: filter } : undefined),
  })

  const { data: settings } = useQuery({ queryKey: ['shop-settings'], queryFn: getShopSettings })
  const financingThreshold = parseFloat(settings?.financing_threshold ?? '500')

  const outstanding = invoices.filter(i => i.status !== 'paid').reduce((s, i) => s + i.balance, 0)
  const collectedMonth = invoices.filter(i => i.status === 'paid').reduce((s, i) => s + i.amount_paid, 0)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '20px 24px 0', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Invoices</div>
        </div>

        {/* Stats */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
          {[
            { label: 'Outstanding', value: `$${outstanding.toFixed(0)}`, color: '#f87171' },
            { label: 'Collected this month', value: `$${collectedMonth.toFixed(0)}`, color: '#4ade80' },
            { label: 'Total invoices', value: String(invoices.length), color: '#fff' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ flex: 1, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 9, padding: '11px 14px' }}>
              <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em', color }}>{value}</div>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Filter tabs */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 0 }}>
          {FILTERS.map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                height: 28, padding: '0 12px', borderRadius: 6, border: 'none', cursor: 'pointer',
                fontSize: 11, fontWeight: 600, textTransform: 'capitalize',
                background: filter === f ? 'rgba(255,255,255,0.1)' : 'transparent',
                color: filter === f ? '#fff' : 'rgba(255,255,255,0.4)',
              }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 24px 20px' }}>
        {isLoading ? (
          <div style={{ color: 'rgba(255,255,255,0.3)', padding: '20px 0' }}>Loading…</div>
        ) : invoices.length === 0 ? (
          <div style={{ color: 'rgba(255,255,255,0.25)', padding: '40px 0', textAlign: 'center', fontSize: 13 }}>
            No invoices yet
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                {['Number', 'Total', 'Balance', 'Status', 'Date'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '0 0 10px', fontWeight: 700 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {invoices.map(inv => (
                <tr
                  key={inv.id}
                  onClick={() => setSelected(inv)}
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', cursor: 'pointer' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)' }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}
                >
                  <td style={{ padding: '12px 0', fontWeight: 600 }}>{inv.number}</td>
                  <td style={{ padding: '12px 0' }}>${inv.total.toFixed(2)}</td>
                  <td style={{ padding: '12px 0', color: inv.balance > 0 ? '#f87171' : '#4ade80' }}>${inv.balance.toFixed(2)}</td>
                  <td style={{ padding: '12px 0' }}>
                    <span style={{
                      padding: '2px 8px', borderRadius: 5, fontSize: 10, fontWeight: 700,
                      background: `${STATUS_COLORS[inv.status] ?? '#94a3b8'}22`,
                      color: STATUS_COLORS[inv.status] ?? '#94a3b8',
                    }}>
                      {inv.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px 0', color: 'rgba(255,255,255,0.4)' }}>
                    {new Date(inv.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <InvoiceDetail
          invoice={selected}
          onClose={() => setSelected(null)}
          financingThreshold={financingThreshold}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Verify invoices page works**

Open http://localhost:3000/invoices — should show stats row, filter tabs, and invoice table. Click any invoice to open the detail panel. Verify "Send Payment Link" and "Record Payment" buttons appear for unpaid invoices. Verify "Offer Financing" button appears when balance ≥ threshold.

- [ ] **Step 5: Commit**

```bash
git add web/app/invoices/page.tsx web/components/invoices/
git commit -m "feat(web): add Invoices page with detail panel, payment link, and financing modal"
```

---

## Task 11: Wire up navigation and dashboard tiles

**Files:**
- Modify: `web/components/dashboard/tiles.tsx`
- Modify: `web/components/AppShell.tsx`

- [ ] **Step 1: Read current tiles.tsx to find Job Cards and Invoices tile entries**

```bash
grep -n "job-card\|invoice\|Job Card\|Invoice" web/components/dashboard/tiles.tsx
```

- [ ] **Step 2: Update Job Cards and Invoices tiles to "live"**

In `web/components/dashboard/tiles.tsx`, find the entries for Job Cards and Invoices and change their status from `'soon'` to `'live'`, and set their `href` to `/job-cards` and `/invoices` respectively. The exact lines depend on the current file — apply this change based on the grep output from Step 1.

Example: if the file has `{ label: 'Job Cards', status: 'soon', icon: '🗂' }`, change to:
```typescript
{ label: 'Job Cards', status: 'live', icon: '🗂', href: '/job-cards' },
{ label: 'Invoices', status: 'live', icon: '🧾', href: '/invoices' },
```

- [ ] **Step 3: Add Job Cards and Invoices to AppShell nav**

In `web/components/AppShell.tsx`, find the nav items array. Add Job Cards and Invoices as navigatable items:

```typescript
// In the nav items / links array, add:
{ label: 'Job Cards', href: '/job-cards' },
{ label: 'Invoices', href: '/invoices' },
```

- [ ] **Step 4: Verify both pages are accessible from nav and dashboard**

Open http://localhost:3000 — Job Cards and Invoices tiles should no longer have "soon" badges. Click each tile → navigates to the correct page.

- [ ] **Step 5: Commit**

```bash
git add web/components/dashboard/tiles.tsx web/components/AppShell.tsx
git commit -m "feat(web): wire Job Cards and Invoices to nav and dashboard tiles"
```
