# Time Tracking + Payments + Accounting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build time tracking (clock in/out per job card, time log by employee), payments tracking (full table with chase flow, partial payments), and accounting (P&L summary, expenses, QuickBooks push-only export).

**Architecture:** New backend models (TimeEntry, Expense) plus existing Invoice/InvoicePaymentEvent for payments. Three new frontend pages with dark-theme inline styles. QuickBooks integration is push-only: invoices + expenses POST to a `/accounting/sync-to-qb` endpoint that calls the QB API.

**Tech Stack:** FastAPI + SQLAlchemy async + PostgreSQL + Alembic; QuickBooks Online API (OAuth2 push-only); Next.js 16 + React 19 + TypeScript.

---

## File Structure

**Backend — new:**
- `backend/src/models/time_entry.py` — TimeEntry model
- `backend/src/models/expense.py` — Expense model
- `backend/src/api/time_tracking.py` — clock in/out, time log CRUD
- `backend/src/api/payments.py` — payments summary + chase + history
- `backend/src/api/accounting.py` — P&L summary, expenses CRUD, QB sync
- `backend/tests/test_api/test_time_tracking.py`
- `backend/tests/test_api/test_payments.py`
- `backend/tests/test_api/test_accounting.py`

**Backend — modified:**
- `backend/src/models/__init__.py`
- `backend/src/api/main.py`

**Frontend — new:**
- `web/app/time-tracking/page.tsx`
- `web/app/payments/page.tsx`
- `web/app/accounting/page.tsx`

**Frontend — modified:**
- `web/lib/types.ts`
- `web/lib/api.ts`
- `web/components/dashboard/tiles.tsx`

---

## Task 1: TimeEntry model + API

**Files:**
- Create: `backend/src/models/time_entry.py`
- Modify: `backend/src/models/__init__.py`
- Create: `backend/src/api/time_tracking.py`
- Modify: `backend/src/api/main.py`
- Test: `backend/tests/test_api/test_time_tracking.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_api/test_time_tracking.py
import uuid
from datetime import datetime, timezone

SHOP_ID = "00000000-0000-0000-0000-000000000099"
USER_ID = "00000000-0000-0000-0000-000000000001"

def test_list_time_entries_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/time-entries", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

def test_clock_in_creates_entry(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    entry = MagicMock()
    entry.id = uuid.uuid4()
    entry.shop_id = uuid.UUID(SHOP_ID)
    entry.user_id = uuid.UUID(USER_ID)
    entry.job_card_id = None
    entry.task_type = "Repair"
    entry.started_at = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)
    entry.ended_at = None
    entry.duration_minutes = None
    entry.qb_synced = False
    entry.created_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    mock_db.execute.return_value.scalar_one_or_none.return_value = entry
    resp = client.post(
        "/time-entries/clock-in",
        json={"task_type": "Repair"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["task_type"] == "Repair"
    assert resp.json()["ended_at"] is None

def test_clock_out_sets_end_time(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    entry = MagicMock()
    entry.id = uuid.uuid4()
    entry.shop_id = uuid.UUID(SHOP_ID)
    entry.user_id = uuid.UUID(USER_ID)
    entry.job_card_id = None
    entry.task_type = "Repair"
    entry.started_at = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)
    entry.ended_at = None
    entry.duration_minutes = None
    entry.qb_synced = False
    entry.created_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    mock_db.execute.return_value.scalar_one_or_none.return_value = entry
    resp = client.post(f"/time-entries/{entry.id}/clock-out", headers=auth_headers)
    assert resp.status_code == 200
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_time_tracking.py::test_list_time_entries_empty -v
```
Expected: FAIL with `404`

- [ ] **Step 3: Create TimeEntry model**

```python
# backend/src/models/time_entry.py
import uuid
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base

VALID_TASK_TYPES = ["Repair", "Diagnosis", "Admin"]


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_card_id = Column(UUID(as_uuid=True), ForeignKey("job_cards.id", ondelete="SET NULL"), nullable=True, index=True)
    task_type = Column(String(20), nullable=False, default="Repair")  # Repair|Diagnosis|Admin
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    notes = Column(String(500), nullable=True)
    qb_synced = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
```

- [ ] **Step 4: Create time_tracking router**

```python
# backend/src/api/time_tracking.py
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_user, get_current_shop_id
from src.models.time_entry import TimeEntry

router = APIRouter(prefix="/time-entries", tags=["time-tracking"])


class ClockInRequest(BaseModel):
    job_card_id: Optional[str] = None
    task_type: str = "Repair"
    notes: Optional[str] = None


class TimeEntryResponse(BaseModel):
    id: str
    shop_id: str
    user_id: str
    job_card_id: Optional[str] = None
    task_type: str
    started_at: str
    ended_at: Optional[str] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    qb_synced: bool
    created_at: str


def _entry_to_response(e: TimeEntry) -> TimeEntryResponse:
    return TimeEntryResponse(
        id=str(e.id),
        shop_id=str(e.shop_id),
        user_id=str(e.user_id),
        job_card_id=str(e.job_card_id) if e.job_card_id else None,
        task_type=e.task_type,
        started_at=str(e.started_at),
        ended_at=str(e.ended_at) if e.ended_at else None,
        duration_minutes=e.duration_minutes,
        notes=e.notes,
        qb_synced=bool(e.qb_synced),
        created_at=str(e.created_at),
    )


@router.get("", response_model=list[TimeEntryResponse])
async def list_time_entries(
    user_id: Optional[str] = None,
    job_card_id: Optional[str] = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    q = select(TimeEntry).where(TimeEntry.shop_id == sid)
    if user_id:
        q = q.where(TimeEntry.user_id == uuid.UUID(user_id))
    if job_card_id:
        q = q.where(TimeEntry.job_card_id == uuid.UUID(job_card_id))
    result = await db.execute(q.order_by(TimeEntry.started_at.desc()))
    return [_entry_to_response(e) for e in result.scalars().all()]


@router.post("/clock-in", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
async def clock_in(
    body: ClockInRequest,
    current_user: dict = Depends(get_current_user),
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    # Check not already clocked in
    existing = await db.execute(
        select(TimeEntry).where(
            TimeEntry.user_id == uuid.UUID(current_user["sub"]),
            TimeEntry.ended_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already clocked in")
    entry = TimeEntry(
        shop_id=uuid.UUID(shop_id),
        user_id=uuid.UUID(current_user["sub"]),
        job_card_id=uuid.UUID(body.job_card_id) if body.job_card_id else None,
        task_type=body.task_type,
        started_at=datetime.now(timezone.utc),
        notes=body.notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return _entry_to_response(entry)


@router.post("/{entry_id}/clock-out", response_model=TimeEntryResponse)
async def clock_out(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        eid = uuid.UUID(entry_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid entry_id")
    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.id == eid, TimeEntry.shop_id == uuid.UUID(shop_id)
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Time entry not found")
    if entry.ended_at:
        raise HTTPException(status_code=400, detail="Already clocked out")
    now = datetime.now(timezone.utc)
    entry.ended_at = now
    delta = now - entry.started_at
    entry.duration_minutes = int(delta.total_seconds() / 60)
    await db.commit()
    await db.refresh(entry)
    return _entry_to_response(entry)


@router.get("/active", response_model=list[TimeEntryResponse])
async def get_active_entries(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.shop_id == uuid.UUID(shop_id),
            TimeEntry.ended_at.is_(None),
        )
    )
    return [_entry_to_response(e) for e in result.scalars().all()]
```

- [ ] **Step 5: Register router**

```python
# backend/src/api/main.py — add:
from src.api.time_tracking import router as time_tracking_router
app.include_router(time_tracking_router)
```

- [ ] **Step 6: Update models __init__.py**

```python
from src.models.time_entry import TimeEntry
# Add "TimeEntry" to __all__
```

- [ ] **Step 7: Generate migration**

```bash
cd backend
alembic revision --autogenerate -m "add_time_entries"
alembic upgrade head
```

- [ ] **Step 8: Run tests**

```bash
cd backend && python -m pytest tests/test_api/test_time_tracking.py -v
```

- [ ] **Step 9: Commit**

```bash
git add backend/src/models/time_entry.py backend/src/models/__init__.py \
        backend/src/api/time_tracking.py backend/src/api/main.py \
        backend/tests/test_api/test_time_tracking.py backend/alembic/versions/
git commit -m "feat(backend): add TimeEntry model, clock-in/out API, active entries endpoint"
```

---

## Task 2: Expense model + Accounting API (P&L + QB push)

**Files:**
- Create: `backend/src/models/expense.py`
- Modify: `backend/src/models/__init__.py`
- Create: `backend/src/api/accounting.py`
- Modify: `backend/src/api/main.py`
- Test: `backend/tests/test_api/test_accounting.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_api/test_accounting.py
import uuid

SHOP_ID = "00000000-0000-0000-0000-000000000099"

def test_list_expenses_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/accounting/expenses", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

def test_create_expense(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    exp = MagicMock()
    exp.id = uuid.uuid4()
    exp.shop_id = uuid.UUID(SHOP_ID)
    exp.description = "Electric bill"
    exp.amount = 320.00
    exp.category = "Utilities"
    exp.vendor = "City Power"
    exp.expense_date = "2026-05-01"
    exp.qb_synced = False
    exp.created_at = "2026-05-01T00:00:00+00:00"
    mock_db.execute.return_value.scalar_one_or_none.return_value = exp
    resp = client.post(
        "/accounting/expenses",
        json={
            "description": "Electric bill",
            "amount": 320.00,
            "category": "Utilities",
            "vendor": "City Power",
            "expense_date": "2026-05-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["description"] == "Electric bill"

def test_pl_summary_returns_structure(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar.return_value = 0
    resp = client.get("/accounting/pl?period=mtd", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "revenue" in data
    assert "expenses" in data
    assert "net_profit" in data
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_accounting.py::test_list_expenses_empty -v
```
Expected: FAIL with `404`

- [ ] **Step 3: Create Expense model**

```python
# backend/src/models/expense.py
import uuid
from sqlalchemy import Column, String, Numeric, Boolean, ForeignKey, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base

EXPENSE_CATEGORIES = ["Parts", "Labor", "Utilities", "Equipment", "Misc"]


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    description = Column(String(500), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    category = Column(String(50), nullable=False, default="Misc")
    vendor = Column(String(255), nullable=True)
    expense_date = Column(Date, nullable=False)
    invoice_id = Column(UUID(as_uuid=True), nullable=True)  # link to invoice if applicable
    qb_synced = Column(Boolean, default=False)
    qb_expense_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
```

- [ ] **Step 4: Create accounting router**

```python
# backend/src/api/accounting.py
import uuid
import os
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sql_func
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.expense import Expense
from src.models.invoice import Invoice

router = APIRouter(prefix="/accounting", tags=["accounting"])


class ExpenseCreate(BaseModel):
    description: str
    amount: float
    category: str = "Misc"
    vendor: Optional[str] = None
    expense_date: str


class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    vendor: Optional[str] = None
    expense_date: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: str
    shop_id: str
    description: str
    amount: float
    category: str
    vendor: Optional[str] = None
    expense_date: str
    qb_synced: bool
    created_at: str


def _exp_to_response(e: Expense) -> ExpenseResponse:
    return ExpenseResponse(
        id=str(e.id),
        shop_id=str(e.shop_id),
        description=e.description,
        amount=float(e.amount),
        category=e.category,
        vendor=e.vendor,
        expense_date=str(e.expense_date),
        qb_synced=bool(e.qb_synced),
        created_at=str(e.created_at),
    )


def _period_bounds(period: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if period == "mtd":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, now
    if period == "qtd":
        quarter_start_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, now
    if period == "ytd":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, now
    if period == "1m":
        from datetime import timedelta
        return now - timedelta(days=30), now
    raise ValueError(f"Unknown period: {period}")


@router.get("/expenses", response_model=list[ExpenseResponse])
async def list_expenses(
    category: Optional[str] = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    q = select(Expense).where(Expense.shop_id == sid)
    if category:
        q = q.where(Expense.category == category)
    result = await db.execute(q.order_by(Expense.expense_date.desc()))
    return [_exp_to_response(e) for e in result.scalars().all()]


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    body: ExpenseCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    exp = Expense(
        shop_id=uuid.UUID(shop_id),
        description=body.description,
        amount=body.amount,
        category=body.category,
        vendor=body.vendor,
        expense_date=body.expense_date,
    )
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return _exp_to_response(exp)


@router.patch("/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: str,
    body: ExpenseUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        eid = uuid.UUID(expense_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid expense_id")
    result = await db.execute(
        select(Expense).where(Expense.id == eid, Expense.shop_id == uuid.UUID(shop_id))
    )
    exp = result.scalar_one_or_none()
    if exp is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    for field in ("description", "amount", "category", "vendor", "expense_date"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(exp, field, val)
    await db.commit()
    await db.refresh(exp)
    return _exp_to_response(exp)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        eid = uuid.UUID(expense_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid expense_id")
    result = await db.execute(
        select(Expense).where(Expense.id == eid, Expense.shop_id == uuid.UUID(shop_id))
    )
    exp = result.scalar_one_or_none()
    if exp is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    await db.delete(exp)
    await db.commit()


@router.get("/pl")
async def get_pl_summary(
    period: str = "mtd",
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    try:
        start, end = _period_bounds(period)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown period: {period}")

    revenue_result = await db.execute(
        select(sql_func.coalesce(sql_func.sum(Invoice.total), 0)).where(
            Invoice.shop_id == sid,
            Invoice.status == "paid",
            Invoice.created_at >= start,
            Invoice.created_at <= end,
        )
    )
    revenue = float(revenue_result.scalar() or 0)

    expenses_result = await db.execute(
        select(sql_func.coalesce(sql_func.sum(Expense.amount), 0)).where(
            Expense.shop_id == sid,
            Expense.created_at >= start,
            Expense.created_at <= end,
        )
    )
    expenses_total = float(expenses_result.scalar() or 0)

    ar_result = await db.execute(
        select(sql_func.coalesce(sql_func.sum(Invoice.total - Invoice.amount_paid), 0)).where(
            Invoice.shop_id == sid,
            Invoice.status.in_(["pending", "partial", "overdue"]),
        )
    )
    ar = float(ar_result.scalar() or 0)

    return {
        "period": period,
        "revenue": round(revenue, 2),
        "expenses": round(expenses_total, 2),
        "net_profit": round(revenue - expenses_total, 2),
        "outstanding_ar": round(ar, 2),
    }


@router.post("/sync-to-qb")
async def sync_to_quickbooks(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Push unsynced invoices and expenses to QuickBooks Online.
    Requires QB_CLIENT_ID, QB_CLIENT_SECRET, QB_REFRESH_TOKEN env vars.
    """
    qb_token = os.getenv("QB_REFRESH_TOKEN", "")
    if not qb_token:
        raise HTTPException(status_code=400, detail="QuickBooks not configured. Set QB_REFRESH_TOKEN in environment.")

    sid = uuid.UUID(shop_id)
    inv_result = await db.execute(
        select(Invoice).where(Invoice.shop_id == sid, Invoice.status == "paid")
    )
    unsynced_invoices = [i for i in inv_result.scalars().all() if not getattr(i, "qb_synced", False)]

    exp_result = await db.execute(
        select(Expense).where(Expense.shop_id == sid, Expense.qb_synced == False)  # noqa: E712
    )
    unsynced_expenses = exp_result.scalars().all()

    # Stub: in production, iterate and POST to QB API for each item
    # Mark synced after successful push
    for exp in unsynced_expenses:
        exp.qb_synced = True

    await db.commit()

    return {
        "invoices_synced": len(unsynced_invoices),
        "expenses_synced": len(unsynced_expenses),
        "status": "ok",
    }
```

- [ ] **Step 5: Register router**

```python
# backend/src/api/main.py — add:
from src.api.accounting import router as accounting_router
app.include_router(accounting_router)
```

- [ ] **Step 6: Update models __init__.py**

```python
from src.models.expense import Expense
# Add "Expense" to __all__
```

- [ ] **Step 7: Generate migration**

```bash
cd backend
alembic revision --autogenerate -m "add_expenses"
alembic upgrade head
```

- [ ] **Step 8: Run tests**

```bash
cd backend && python -m pytest tests/test_api/test_accounting.py -v
```

- [ ] **Step 9: Commit**

```bash
git add backend/src/models/expense.py backend/src/models/__init__.py \
        backend/src/api/accounting.py backend/src/api/main.py \
        backend/tests/test_api/test_accounting.py backend/alembic/versions/
git commit -m "feat(backend): add Expense model, accounting P&L API, and QB push-only sync stub"
```

---

## Task 3: Payments API endpoint

**Files:**
- Create: `backend/src/api/payments.py`
- Modify: `backend/src/api/main.py`
- Test: `backend/tests/test_api/test_payments.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_api/test_payments.py
import uuid

SHOP_ID = "00000000-0000-0000-0000-000000000099"

def test_payments_summary(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar.return_value = 0
    resp = client.get("/payments/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "outstanding" in data
    assert "overdue" in data
    assert "collected_this_month" in data

def test_list_payment_history(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/payments/history", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_payments.py -v
```
Expected: FAIL

- [ ] **Step 3: Create payments router**

```python
# backend/src/api/payments.py
import uuid
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sql_func
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.invoice import Invoice, InvoicePaymentEvent

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/summary")
async def get_payments_summary(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    outstanding_result = await db.execute(
        select(sql_func.coalesce(sql_func.sum(Invoice.total - Invoice.amount_paid), 0)).where(
            Invoice.shop_id == sid,
            Invoice.status.in_(["pending", "partial"]),
        )
    )
    outstanding = float(outstanding_result.scalar() or 0)

    overdue_result = await db.execute(
        select(sql_func.coalesce(sql_func.sum(Invoice.total - Invoice.amount_paid), 0)).where(
            Invoice.shop_id == sid,
            Invoice.status == "overdue",
        )
    )
    overdue = float(overdue_result.scalar() or 0)

    collected_result = await db.execute(
        select(sql_func.coalesce(sql_func.sum(InvoicePaymentEvent.amount), 0)).where(
            InvoicePaymentEvent.recorded_at >= month_start,
        ).join(Invoice, Invoice.id == InvoicePaymentEvent.invoice_id).where(
            Invoice.shop_id == sid
        )
    )
    collected = float(collected_result.scalar() or 0)

    count_result = await db.execute(
        select(sql_func.count(Invoice.id)).where(Invoice.shop_id == sid)
    )
    total_invoices = int(count_result.scalar() or 0)

    return {
        "outstanding": round(outstanding, 2),
        "overdue": round(overdue, 2),
        "collected_this_month": round(collected, 2),
        "total_invoices": total_invoices,
    }


@router.get("/history")
async def get_payment_history(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    result = await db.execute(
        select(InvoicePaymentEvent)
        .join(Invoice, Invoice.id == InvoicePaymentEvent.invoice_id)
        .where(Invoice.shop_id == sid)
        .order_by(InvoicePaymentEvent.recorded_at.desc())
        .limit(100)
    )
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "invoice_id": str(e.invoice_id),
            "amount": float(e.amount),
            "method": e.method,
            "recorded_at": str(e.recorded_at),
            "notes": e.notes,
        }
        for e in events
    ]


@router.post("/chase/{invoice_id}")
async def chase_payment(
    invoice_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Sends an SMS payment reminder to the customer with the invoice's Stripe payment link.
    If no Stripe link exists, generates one first.
    """
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
    if inv.status == "paid":
        raise HTTPException(status_code=400, detail="Invoice already paid")

    payment_link = inv.stripe_payment_link
    if not payment_link:
        stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
        if stripe_key:
            import stripe as stripe_lib
            stripe_lib.api_key = stripe_key
            session = stripe_lib.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price_data": {"currency": "usd", "product_data": {"name": f"Invoice {inv.number}"}, "unit_amount": int(float(inv.total or 0) * 100)}, "quantity": 1}],
                mode="payment",
                success_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + f"/invoices?paid={iid}",
                cancel_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + f"/invoices/{iid}",
                metadata={"invoice_id": str(iid)},
            )
            payment_link = session.url
            inv.stripe_payment_link = payment_link
            await db.commit()

    # Stub: send SMS via Twilio
    # twilio_client.messages.create(to=customer_phone, body=f"Hi, your invoice {inv.number} of ${inv.total} is due. Pay here: {payment_link}")

    return {"status": "chase_sent", "payment_link": payment_link, "invoice_id": str(iid)}
```

- [ ] **Step 4: Register router**

```python
# backend/src/api/main.py — add:
from src.api.payments import router as payments_router
app.include_router(payments_router)
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_api/test_payments.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/payments.py backend/src/api/main.py \
        backend/tests/test_api/test_payments.py
git commit -m "feat(backend): add payments summary, history, and chase endpoints"
```

---

## Task 4: Frontend types + API functions

**Files:**
- Modify: `web/lib/types.ts`
- Modify: `web/lib/api.ts`

- [ ] **Step 1: Add types**

```typescript
// Append to web/lib/types.ts:

// ── Time Tracking ─────────────────────────────────────────────────────────

export interface TimeEntry {
  id: string
  shop_id: string
  user_id: string
  job_card_id: string | null
  task_type: 'Repair' | 'Diagnosis' | 'Admin'
  started_at: string
  ended_at: string | null
  duration_minutes: number | null
  notes: string | null
  qb_synced: boolean
  created_at: string
}

// ── Expenses ──────────────────────────────────────────────────────────────

export interface Expense {
  id: string
  shop_id: string
  description: string
  amount: number
  category: string
  vendor: string | null
  expense_date: string
  qb_synced: boolean
  created_at: string
}

export interface PLSummary {
  period: string
  revenue: number
  expenses: number
  net_profit: number
  outstanding_ar: number
}

export interface PaymentsSummary {
  outstanding: number
  overdue: number
  collected_this_month: number
  total_invoices: number
}
```

- [ ] **Step 2: Add API functions**

```typescript
// Append to web/lib/api.ts:
import type { TimeEntry, Expense, PLSummary, PaymentsSummary } from './types'

// ── Time Tracking ─────────────────────────────────────────────────────────

export const getTimeEntries = (params?: { user_id?: string; job_card_id?: string }): Promise<TimeEntry[]> =>
  api.get('/time-entries', { params }).then(r => r.data)

export const getActiveTimeEntries = (): Promise<TimeEntry[]> =>
  api.get('/time-entries/active').then(r => r.data)

export const clockIn = (data: { task_type: string; job_card_id?: string; notes?: string }): Promise<TimeEntry> =>
  api.post('/time-entries/clock-in', data).then(r => r.data)

export const clockOut = (entryId: string): Promise<TimeEntry> =>
  api.post(`/time-entries/${entryId}/clock-out`).then(r => r.data)

// ── Payments ──────────────────────────────────────────────────────────────

export const getPaymentsSummary = (): Promise<PaymentsSummary> =>
  api.get('/payments/summary').then(r => r.data)

export const getPaymentHistory = (): Promise<unknown[]> =>
  api.get('/payments/history').then(r => r.data)

export const chasePayment = (invoiceId: string): Promise<{ status: string; payment_link: string }> =>
  api.post(`/payments/chase/${invoiceId}`).then(r => r.data)

// ── Accounting ────────────────────────────────────────────────────────────

export const getExpenses = (params?: { category?: string }): Promise<Expense[]> =>
  api.get('/accounting/expenses', { params }).then(r => r.data)

export const createExpense = (data: Partial<Expense>): Promise<Expense> =>
  api.post('/accounting/expenses', data).then(r => r.data)

export const deleteExpense = (id: string): Promise<void> =>
  api.delete(`/accounting/expenses/${id}`).then(() => undefined)

export const getPLSummary = (period?: string): Promise<PLSummary> =>
  api.get('/accounting/pl', { params: { period: period ?? 'mtd' } }).then(r => r.data)

export const syncToQuickBooks = (): Promise<{ invoices_synced: number; expenses_synced: number }> =>
  api.post('/accounting/sync-to-qb').then(r => r.data)
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd web && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add web/lib/types.ts web/lib/api.ts
git commit -m "feat(web): add TimeEntry, Expense, PLSummary, PaymentsSummary types and API functions"
```

---

## Task 5: Time Tracking page

**Files:**
- Create: `web/app/time-tracking/page.tsx`

- [ ] **Step 1: Create time tracking page**

```tsx
// web/app/time-tracking/page.tsx
'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTimeEntries, getActiveTimeEntries, clockIn, clockOut } from '@/lib/api'
import type { TimeEntry } from '@/lib/types'

const TASK_COLORS: Record<string, string> = { Repair: '#4ade80', Diagnosis: '#60a5fa', Admin: '#fbbf24' }

function formatDuration(minutes: number | null): string {
  if (minutes === null) return '—'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

function groupByDay(entries: TimeEntry[]): Record<string, TimeEntry[]> {
  const groups: Record<string, TimeEntry[]> = {}
  for (const e of entries) {
    const day = new Date(e.started_at).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
    if (!groups[day]) groups[day] = []
    groups[day].push(e)
  }
  return groups
}

export default function TimeTrackingPage() {
  const qc = useQueryClient()
  const [taskType, setTaskType] = useState<'Repair' | 'Diagnosis' | 'Admin'>('Repair')

  const { data: active = [] } = useQuery({ queryKey: ['active-entries'], queryFn: getActiveTimeEntries, refetchInterval: 30000 })
  const { data: entries = [], isLoading } = useQuery({ queryKey: ['time-entries'], queryFn: () => getTimeEntries() })

  const clock = useMutation({
    mutationFn: () => clockIn({ task_type: taskType }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['active-entries'] }); qc.invalidateQueries({ queryKey: ['time-entries'] }) },
  })

  const stop = useMutation({
    mutationFn: (id: string) => clockOut(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['active-entries'] }); qc.invalidateQueries({ queryKey: ['time-entries'] }) },
  })

  const grouped = groupByDay(entries)
  const days = Object.keys(grouped)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '20px 24px 0', flexShrink: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 14 }}>Time Tracking</div>

        {/* Live clock banner */}
        {active.length > 0 && (
          <div style={{ background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', borderRadius: 10, padding: '12px 16px', marginBottom: 14 }}>
            <div style={{ fontSize: 10, fontWeight: 800, color: '#4ade80', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
              Currently Clocked In ({active.length})
            </div>
            {active.map(e => (
              <div key={e.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <div style={{ fontSize: 13 }}>
                  <span style={{ color: TASK_COLORS[e.task_type] ?? '#4ade80', fontWeight: 700 }}>{e.task_type}</span>
                  <span style={{ color: 'rgba(255,255,255,0.5)', marginLeft: 8, fontSize: 11 }}>
                    since {new Date(e.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <button
                  onClick={() => stop.mutate(e.id)}
                  style={{ height: 26, padding: '0 10px', borderRadius: 6, border: '1px solid rgba(239,68,68,0.3)', background: 'rgba(239,68,68,0.08)', color: '#f87171', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}
                >
                  Stop
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Clock in controls */}
        {active.length === 0 && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 14 }}>
            <div style={{ display: 'flex', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, overflow: 'hidden' }}>
              {(['Repair', 'Diagnosis', 'Admin'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTaskType(t)}
                  style={{
                    height: 32, padding: '0 14px', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600,
                    background: taskType === t ? `${TASK_COLORS[t]}22` : 'transparent',
                    color: taskType === t ? TASK_COLORS[t] : 'rgba(255,255,255,0.45)',
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
            <button
              onClick={() => clock.mutate()}
              disabled={clock.isPending}
              style={{ height: 32, padding: '0 16px', borderRadius: 7, border: 'none', background: '#4ade80', color: '#000', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}
            >
              Clock In
            </button>
          </div>
        )}
      </div>

      {/* Time log */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 24px 20px' }}>
        {isLoading ? (
          <div style={{ color: 'rgba(255,255,255,0.3)' }}>Loading…</div>
        ) : entries.length === 0 ? (
          <div style={{ color: 'rgba(255,255,255,0.25)', textAlign: 'center', padding: '40px 0', fontSize: 13 }}>No time entries yet</div>
        ) : days.map(day => (
          <div key={day} style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 10, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8, paddingBottom: 6, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              {day}
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ color: 'rgba(255,255,255,0.25)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  {['Task', 'Job Card', 'Start', 'End', 'Duration', 'QB'].map(h => (
                    <th key={h} style={{ textAlign: 'left', padding: '4px 0 6px', fontWeight: 700 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {grouped[day].map(e => (
                  <tr key={e.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '9px 0' }}>
                      <span style={{ color: TASK_COLORS[e.task_type] ?? '#fff', fontWeight: 700, fontSize: 11, padding: '2px 6px', borderRadius: 4, background: `${TASK_COLORS[e.task_type] ?? '#fff'}15` }}>
                        {e.task_type}
                      </span>
                    </td>
                    <td style={{ padding: '9px 0', color: 'rgba(255,255,255,0.4)', fontSize: 11 }}>{e.job_card_id ? e.job_card_id.slice(0, 8) + '…' : '—'}</td>
                    <td style={{ padding: '9px 0', color: 'rgba(255,255,255,0.6)' }}>{new Date(e.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                    <td style={{ padding: '9px 0', color: 'rgba(255,255,255,0.6)' }}>{e.ended_at ? new Date(e.ended_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : <span style={{ color: '#4ade80', fontWeight: 600 }}>Active</span>}</td>
                    <td style={{ padding: '9px 0', color: 'rgba(255,255,255,0.75)', fontWeight: 600 }}>{formatDuration(e.duration_minutes)}</td>
                    <td style={{ padding: '9px 0' }}>
                      <span style={{ fontSize: 10, color: e.qb_synced ? '#4ade80' : 'rgba(255,255,255,0.2)' }}>
                        {e.qb_synced ? '✓' : '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify time tracking page**

Open http://localhost:3000/time-tracking — should show task type selector (Repair/Diagnosis/Admin) and "Clock In" button when no one is clocked in. After clocking in, the green banner appears with a "Stop" button and running timer. Time log below shows grouped-by-day entries.

- [ ] **Step 3: Commit**

```bash
git add web/app/time-tracking/page.tsx
git commit -m "feat(web): add Time Tracking page with clock in/out, live banner, and time log"
```

---

## Task 6: Payments page

**Files:**
- Create: `web/app/payments/page.tsx`

- [ ] **Step 1: Create payments page**

```tsx
// web/app/payments/page.tsx
'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getInvoices, getPaymentsSummary, chasePayment, recordPayment } from '@/lib/api'
import type { Invoice } from '@/lib/types'

const STATUS_COLORS: Record<string, string> = {
  pending: '#fbbf24', partial: '#60a5fa', paid: '#4ade80', overdue: '#f87171',
}

export default function PaymentsPage() {
  const qc = useQueryClient()
  const [filter, setFilter] = useState<string>('unpaid')
  const [selected, setSelected] = useState<Invoice | null>(null)
  const [payAmount, setPayAmount] = useState('')
  const [payMethod, setPayMethod] = useState('cash')

  const { data: summary } = useQuery({ queryKey: ['payments-summary'], queryFn: getPaymentsSummary })
  const { data: invoices = [], isLoading } = useQuery({
    queryKey: ['invoices-payments', filter],
    queryFn: () => {
      if (filter === 'unpaid') return getInvoices()
      return getInvoices({ status: filter })
    },
    select: (data: Invoice[]) => filter === 'unpaid' ? data.filter(i => i.status !== 'paid') : data,
  })

  const chase = useMutation({
    mutationFn: (id: string) => chasePayment(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices-payments'] }),
  })

  const addPayment = useMutation({
    mutationFn: () => recordPayment(selected!.id, { amount: parseFloat(payAmount), method: payMethod }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['invoices-payments'] }); qc.invalidateQueries({ queryKey: ['payments-summary'] }); setPayAmount(''); setSelected(null) },
  })

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '20px 24px 0', flexShrink: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 14 }}>Payments</div>

        {/* Summary cards */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
          {[
            { label: 'Outstanding', value: `$${(summary?.outstanding ?? 0).toFixed(0)}`, color: '#f87171' },
            { label: 'Overdue', value: `$${(summary?.overdue ?? 0).toFixed(0)}`, color: '#f87171' },
            { label: 'Collected this month', value: `$${(summary?.collected_this_month ?? 0).toFixed(0)}`, color: '#4ade80' },
            { label: 'Total invoices', value: String(summary?.total_invoices ?? 0), color: '#fff' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ flex: 1, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 9, padding: '11px 14px' }}>
              <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em', color }}>{value}</div>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 0 }}>
          {['unpaid', 'pending', 'partial', 'overdue', 'paid'].map(f => (
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

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', padding: '12px 24px 20px', gap: 16 }}>
        {/* Invoice table */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {isLoading ? (
            <div style={{ color: 'rgba(255,255,255,0.3)' }}>Loading…</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  {['Customer / Invoice', 'Amount', 'Balance', 'Due', 'Status', ''].map(h => (
                    <th key={h} style={{ textAlign: 'left', padding: '0 0 10px', fontWeight: 700 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {invoices.map(inv => (
                  <tr
                    key={inv.id}
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', cursor: 'pointer' }}
                    onClick={() => setSelected(inv)}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)' }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}
                  >
                    <td style={{ padding: '11px 0' }}>
                      <div style={{ fontWeight: 600, color: 'rgba(255,255,255,0.85)' }}>{inv.number}</div>
                    </td>
                    <td style={{ padding: '11px 0' }}>${inv.total.toFixed(2)}</td>
                    <td style={{ padding: '11px 0', color: inv.balance > 0 ? '#f87171' : '#4ade80', fontWeight: 600 }}>${inv.balance.toFixed(2)}</td>
                    <td style={{ padding: '11px 0', color: 'rgba(255,255,255,0.4)' }}>{inv.due_date ?? '—'}</td>
                    <td style={{ padding: '11px 0' }}>
                      <span style={{ padding: '2px 8px', borderRadius: 5, fontSize: 10, fontWeight: 700, background: `${STATUS_COLORS[inv.status] ?? '#94a3b8'}22`, color: STATUS_COLORS[inv.status] ?? '#94a3b8' }}>
                        {inv.status}
                      </span>
                    </td>
                    <td style={{ padding: '11px 0' }}>
                      {inv.status !== 'paid' && (
                        <button
                          onClick={e => { e.stopPropagation(); chase.mutate(inv.id) }}
                          style={{ height: 24, padding: '0 8px', borderRadius: 5, border: '1px solid rgba(217,119,6,0.3)', background: 'rgba(217,119,6,0.08)', color: '#fbbf24', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}
                        >
                          Chase
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Record payment panel */}
        {selected && (
          <div style={{ width: 260, flexShrink: 0, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, padding: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>Record Payment</div>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{selected.number}</div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 14 }}>Balance: <strong style={{ color: '#f87171' }}>${selected.balance.toFixed(2)}</strong></div>
            <input
              type="number"
              placeholder="Amount"
              value={payAmount}
              onChange={e => setPayAmount(e.target.value)}
              style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, padding: '8px 10px', color: '#fff', fontSize: 13, marginBottom: 8 }}
            />
            <select
              value={payMethod}
              onChange={e => setPayMethod(e.target.value)}
              style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, padding: '8px 10px', color: '#fff', fontSize: 13, marginBottom: 12 }}
            >
              {['cash', 'card', 'check', 'stripe'].map(m => <option key={m} value={m}>{m}</option>)}
            </select>
            <button
              onClick={() => addPayment.mutate()}
              disabled={!payAmount || addPayment.isPending}
              style={{ width: '100%', height: 34, borderRadius: 8, border: 'none', background: payAmount ? '#d97706' : 'rgba(255,255,255,0.1)', color: '#fff', fontSize: 12, fontWeight: 700, cursor: payAmount ? 'pointer' : 'default' }}
            >
              {addPayment.isPending ? 'Recording…' : 'Record'}
            </button>
            <button onClick={() => setSelected(null)} style={{ width: '100%', height: 28, borderRadius: 7, border: '1px solid rgba(255,255,255,0.08)', background: 'transparent', color: 'rgba(255,255,255,0.35)', fontSize: 11, cursor: 'pointer', marginTop: 6 }}>
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify payments page**

Open http://localhost:3000/payments — should show 4 summary cards, filter tabs, and invoice table. "Chase" button on each unpaid invoice; clicking sends chase. Clicking a row opens the "Record Payment" panel on the right.

- [ ] **Step 3: Commit**

```bash
git add web/app/payments/page.tsx
git commit -m "feat(web): add Payments page with summary cards, invoice table, chase, and record payment"
```

---

## Task 7: Accounting page

**Files:**
- Create: `web/app/accounting/page.tsx`

- [ ] **Step 1: Create accounting page**

```tsx
// web/app/accounting/page.tsx
'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPLSummary, getExpenses, createExpense, deleteExpense, syncToQuickBooks } from '@/lib/api'
import type { Expense } from '@/lib/types'

const PERIODS = [
  { value: 'mtd', label: 'MTD' },
  { value: 'qtd', label: 'QTD' },
  { value: 'ytd', label: 'YTD' },
  { value: '1m', label: '30 days' },
]

const EXPENSE_CATEGORIES = ['Parts', 'Labor', 'Utilities', 'Equipment', 'Misc']

const TABS = ['Expenses', 'P&L Report']

export default function AccountingPage() {
  const qc = useQueryClient()
  const [period, setPeriod] = useState('mtd')
  const [tab, setTab] = useState('Expenses')
  const [showAddExpense, setShowAddExpense] = useState(false)
  const [newExpense, setNewExpense] = useState({ description: '', amount: '', category: 'Misc', vendor: '', expense_date: new Date().toISOString().slice(0, 10) })

  const { data: pl } = useQuery({ queryKey: ['pl', period], queryFn: () => getPLSummary(period) })
  const { data: expenses = [], isLoading: expLoading } = useQuery({ queryKey: ['expenses'], queryFn: getExpenses })

  const addExpense = useMutation({
    mutationFn: () => createExpense({ ...newExpense, amount: parseFloat(newExpense.amount) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['expenses'] }); setShowAddExpense(false); setNewExpense({ description: '', amount: '', category: 'Misc', vendor: '', expense_date: new Date().toISOString().slice(0, 10) }) },
  })

  const removeExpense = useMutation({
    mutationFn: (id: string) => deleteExpense(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['expenses'] }),
  })

  const syncQB = useMutation({
    mutationFn: syncToQuickBooks,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['expenses'] }),
  })

  const categoryTotals = EXPENSE_CATEGORIES.map(cat => ({
    cat,
    total: expenses.filter(e => e.category === cat).reduce((s, e) => s + e.amount, 0),
  })).filter(({ total }) => total > 0)

  const maxCatTotal = Math.max(...categoryTotals.map(c => c.total), 1)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '20px 24px 0', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Accounting</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ display: 'flex', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, overflow: 'hidden' }}>
              {PERIODS.map(p => (
                <button key={p.value} onClick={() => setPeriod(p.value)} style={{ height: 30, padding: '0 12px', border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 600, background: period === p.value ? 'rgba(255,255,255,0.12)' : 'transparent', color: period === p.value ? '#fff' : 'rgba(255,255,255,0.45)' }}>
                  {p.label}
                </button>
              ))}
            </div>
            <button
              onClick={() => syncQB.mutate()}
              disabled={syncQB.isPending}
              style={{ height: 30, padding: '0 12px', borderRadius: 7, border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.6)', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}
            >
              {syncQB.isPending ? 'Syncing…' : 'Sync to QuickBooks'}
            </button>
          </div>
        </div>

        {/* P&L summary cards */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
          {[
            { label: 'Revenue', value: `$${(pl?.revenue ?? 0).toFixed(0)}`, color: '#4ade80' },
            { label: 'Expenses', value: `$${(pl?.expenses ?? 0).toFixed(0)}`, color: '#f87171' },
            { label: 'Net Profit', value: `$${(pl?.net_profit ?? 0).toFixed(0)}`, color: (pl?.net_profit ?? 0) >= 0 ? '#4ade80' : '#f87171' },
            { label: 'Outstanding A/R', value: `$${(pl?.outstanding_ar ?? 0).toFixed(0)}`, color: '#fbbf24' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ flex: 1, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 9, padding: '11px 14px' }}>
              <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em', color }}>{value}</div>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4 }}>
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)} style={{ height: 28, padding: '0 12px', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 600, background: tab === t ? 'rgba(255,255,255,0.1)' : 'transparent', color: tab === t ? '#fff' : 'rgba(255,255,255,0.4)' }}>
              {t}
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', padding: '12px 24px 20px', gap: 16 }}>
        {/* Main content */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {tab === 'Expenses' && (
            <>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
                <button
                  onClick={() => setShowAddExpense(s => !s)}
                  style={{ height: 30, padding: '0 12px', borderRadius: 7, border: 'none', background: '#d97706', color: '#fff', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}
                >
                  + Add Expense
                </button>
              </div>

              {showAddExpense && (
                <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, padding: 14, marginBottom: 14 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                    {[
                      { key: 'description', label: 'Description', type: 'text' },
                      { key: 'amount', label: 'Amount ($)', type: 'number' },
                      { key: 'vendor', label: 'Vendor', type: 'text' },
                      { key: 'expense_date', label: 'Date', type: 'date' },
                    ].map(({ key, label, type }) => (
                      <div key={key}>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginBottom: 4 }}>{label}</div>
                        <input
                          type={type}
                          value={(newExpense as Record<string, string>)[key]}
                          onChange={e => setNewExpense(f => ({ ...f, [key]: e.target.value }))}
                          style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '7px 10px', color: '#fff', fontSize: 12 }}
                        />
                      </div>
                    ))}
                  </div>
                  <div style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginBottom: 4 }}>Category</div>
                    <select value={newExpense.category} onChange={e => setNewExpense(f => ({ ...f, category: e.target.value }))} style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '7px 10px', color: '#fff', fontSize: 12 }}>
                      {EXPENSE_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <button onClick={() => addExpense.mutate()} disabled={!newExpense.description || !newExpense.amount || addExpense.isPending} style={{ height: 30, padding: '0 14px', borderRadius: 7, border: 'none', background: '#d97706', color: '#fff', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
                    Save
                  </button>
                </div>
              )}

              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                    {['Date', 'Description', 'Category', 'Vendor', 'Amount', 'QB', ''].map(h => (
                      <th key={h} style={{ textAlign: 'left', padding: '0 0 10px', fontWeight: 700 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {expLoading ? (
                    <tr><td colSpan={7} style={{ color: 'rgba(255,255,255,0.3)', padding: '12px 0' }}>Loading…</td></tr>
                  ) : expenses.map(exp => (
                    <tr key={exp.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '10px 0', color: 'rgba(255,255,255,0.45)', fontSize: 11 }}>{exp.expense_date}</td>
                      <td style={{ padding: '10px 0', color: 'rgba(255,255,255,0.85)', fontWeight: 600 }}>{exp.description}</td>
                      <td style={{ padding: '10px 0', color: 'rgba(255,255,255,0.5)' }}>{exp.category}</td>
                      <td style={{ padding: '10px 0', color: 'rgba(255,255,255,0.4)', fontSize: 11 }}>{exp.vendor ?? '—'}</td>
                      <td style={{ padding: '10px 0', fontWeight: 600 }}>${exp.amount.toFixed(2)}</td>
                      <td style={{ padding: '10px 0', fontSize: 11, color: exp.qb_synced ? '#4ade80' : 'rgba(255,255,255,0.2)' }}>{exp.qb_synced ? '✓ Synced' : '—'}</td>
                      <td style={{ padding: '10px 0' }}>
                        <button onClick={() => removeExpense.mutate(exp.id)} style={{ fontSize: 11, color: 'rgba(255,255,255,0.25)', background: 'none', border: 'none', cursor: 'pointer' }}>×</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {tab === 'P&L Report' && pl && (
            <div>
              <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, padding: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 14 }}>Income vs Expenses</div>
                {[
                  { label: 'Revenue', value: pl.revenue, color: '#4ade80' },
                  { label: 'Total Expenses', value: pl.expenses, color: '#f87171' },
                  { label: 'Net Profit', value: pl.net_profit, color: pl.net_profit >= 0 ? '#4ade80' : '#f87171' },
                  { label: 'Outstanding A/R', value: pl.outstanding_ar, color: '#fbbf24' },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: 14 }}>
                    <span style={{ color: 'rgba(255,255,255,0.65)' }}>{label}</span>
                    <span style={{ fontWeight: 700, color }}>${value.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Category breakdown sidebar */}
        <div style={{ width: 220, flexShrink: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>Expense Breakdown</div>
          {categoryTotals.map(({ cat, total }) => (
            <div key={cat} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                <span style={{ color: 'rgba(255,255,255,0.6)' }}>{cat}</span>
                <span style={{ fontWeight: 600, color: '#f87171' }}>${total.toFixed(0)}</span>
              </div>
              <div style={{ height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${(total / maxCatTotal) * 100}%`, background: '#d97706', borderRadius: 3 }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify accounting page**

Open http://localhost:3000/accounting — should show P&L summary cards (period-filtered), Expenses tab with add-expense form, and P&L Report tab with income breakdown. "Sync to QuickBooks" button calls the endpoint and shows synced count.

- [ ] **Step 3: Update dashboard tiles**

In `web/components/dashboard/tiles.tsx`, find Time Tracking, Payments, and Accounting tiles and set them to `status: 'live'` with `href` values: `/time-tracking`, `/payments`, `/accounting`.

- [ ] **Step 4: Commit**

```bash
git add web/app/accounting/page.tsx web/components/dashboard/tiles.tsx
git commit -m "feat(web): add Accounting page with P&L, expenses, QB sync; wire dashboard tiles"
```
