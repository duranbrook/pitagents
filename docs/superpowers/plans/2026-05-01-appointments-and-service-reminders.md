# Appointments + Service Reminders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shop-side appointment calendar with month/week/day views, a public customer booking page, one-click appointment→job card conversion, and an automated service reminder system with configurable windows and a monthly background job.

**Architecture:** New backend models (Appointment, BookingConfig, ServiceReminderConfig, ServiceReminder) with CRUD routes and a public booking endpoint. Service reminders run as a background task triggered via a `/reminders/run` endpoint (cronnable). Frontend calendar uses CSS Grid for month/week/day layout without external calendar libraries.

**Tech Stack:** FastAPI + SQLAlchemy async + PostgreSQL + Alembic; APScheduler or manual cron trigger for reminder job; Twilio SMS (already in project); Next.js 16 + React 19 + TypeScript.

---

## File Structure

**Backend — new:**
- `backend/src/models/appointment.py` — Appointment + BookingConfig models
- `backend/src/models/service_reminder.py` — ServiceReminderConfig + ServiceReminder models
- `backend/src/api/appointments.py` — shop CRUD + public booking endpoint
- `backend/src/api/service_reminders.py` — config CRUD + reminder job trigger
- `backend/tests/test_api/test_appointments.py`
- `backend/tests/test_api/test_service_reminders.py`

**Backend — modified:**
- `backend/src/models/__init__.py`
- `backend/src/api/main.py`

**Frontend — new:**
- `web/app/appointments/page.tsx` — shop calendar
- `web/app/book/[slug]/page.tsx` — public booking page (no auth)
- `web/components/appointments/CalendarGrid.tsx`
- `web/components/appointments/AppointmentCard.tsx`
- `web/components/appointments/NewAppointmentModal.tsx`
- `web/app/reminders/page.tsx` — service reminder settings

**Frontend — modified:**
- `web/lib/types.ts` — Appointment, BookingConfig, ServiceReminderConfig types
- `web/lib/api.ts` — appointment + reminder API functions
- `web/components/dashboard/tiles.tsx` — set Appointments + Reminders tiles to "live"

---

## Task 1: Appointment model + migration + API

**Files:**
- Create: `backend/src/models/appointment.py`
- Modify: `backend/src/models/__init__.py`
- Create: `backend/src/api/appointments.py`
- Modify: `backend/src/api/main.py`
- Test: `backend/tests/test_api/test_appointments.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_api/test_appointments.py
import uuid
from datetime import datetime, timezone

SHOP_ID = "00000000-0000-0000-0000-000000000099"

def test_list_appointments_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/appointments", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

def test_create_appointment(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    appt = MagicMock()
    appt.id = uuid.uuid4()
    appt.shop_id = uuid.UUID(SHOP_ID)
    appt.customer_id = None
    appt.vehicle_id = None
    appt.starts_at = datetime(2026, 5, 10, 9, 0, tzinfo=timezone.utc)
    appt.ends_at = datetime(2026, 5, 10, 10, 0, tzinfo=timezone.utc)
    appt.service_requested = "Oil change"
    appt.status = "confirmed"
    appt.notes = None
    appt.source = "manual"
    appt.booking_token = None
    appt.job_card_id = None
    appt.created_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    mock_db.execute.return_value.scalar_one_or_none.return_value = appt
    resp = client.post(
        "/appointments",
        json={
            "starts_at": "2026-05-10T09:00:00+00:00",
            "ends_at": "2026-05-10T10:00:00+00:00",
            "service_requested": "Oil change",
            "status": "confirmed",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

def test_get_appointment_404(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.get(f"/appointments/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_appointments.py::test_list_appointments_empty -v
```
Expected: FAIL with `404`

- [ ] **Step 3: Create Appointment model**

```python
# backend/src/models/appointment.py
import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    service_requested = Column(String(500), nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending|confirmed|cancelled
    notes = Column(Text, nullable=True)
    source = Column(String(20), default="manual", nullable=False)  # manual|booking_link
    booking_token = Column(String(100), nullable=True, unique=True)
    job_card_id = Column(UUID(as_uuid=True), ForeignKey("job_cards.id", ondelete="SET NULL"), nullable=True)
    customer_name = Column(String(255), nullable=True)
    customer_phone = Column(String(50), nullable=True)
    customer_email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)


class BookingConfig(Base):
    __tablename__ = "booking_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    slug = Column(String(100), nullable=False, unique=True)
    available_services = Column(String, default="[]")  # JSON stored as text
    working_hours_start = Column(String(5), default="08:00")  # HH:MM
    working_hours_end = Column(String(5), default="17:00")
    slot_duration_minutes = Column(String(5), default="60")
    working_days = Column(String, default="[1,2,3,4,5]")  # JSON: 1=Mon…7=Sun
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
```

- [ ] **Step 4: Create appointments router**

```python
# backend/src/api/appointments.py
import uuid
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.appointment import Appointment, BookingConfig
from src.models.job_card import JobCard

router = APIRouter(prefix="/appointments", tags=["appointments"])


class AppointmentCreate(BaseModel):
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    starts_at: str
    ends_at: str
    service_requested: Optional[str] = None
    status: str = "pending"
    notes: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None


class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
    service_requested: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: str
    shop_id: str
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    starts_at: str
    ends_at: str
    service_requested: Optional[str] = None
    status: str
    notes: Optional[str] = None
    source: str
    job_card_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    created_at: str


def _appt_to_response(a: Appointment) -> AppointmentResponse:
    return AppointmentResponse(
        id=str(a.id),
        shop_id=str(a.shop_id),
        customer_id=str(a.customer_id) if a.customer_id else None,
        vehicle_id=str(a.vehicle_id) if a.vehicle_id else None,
        starts_at=str(a.starts_at),
        ends_at=str(a.ends_at),
        service_requested=a.service_requested,
        status=a.status,
        notes=a.notes,
        source=a.source,
        job_card_id=str(a.job_card_id) if a.job_card_id else None,
        customer_name=a.customer_name,
        customer_phone=a.customer_phone,
        customer_email=a.customer_email,
        created_at=str(a.created_at),
    )


@router.get("", response_model=list[AppointmentResponse])
async def list_appointments(
    year: Optional[int] = None,
    month: Optional[int] = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    q = select(Appointment).where(Appointment.shop_id == sid)
    if year and month:
        from sqlalchemy import extract
        q = q.where(
            extract("year", Appointment.starts_at) == year,
            extract("month", Appointment.starts_at) == month,
        )
    result = await db.execute(q.order_by(Appointment.starts_at))
    return [_appt_to_response(a) for a in result.scalars().all()]


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    body: AppointmentCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    appt = Appointment(
        shop_id=uuid.UUID(shop_id),
        customer_id=uuid.UUID(body.customer_id) if body.customer_id else None,
        vehicle_id=uuid.UUID(body.vehicle_id) if body.vehicle_id else None,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        service_requested=body.service_requested,
        status=body.status,
        notes=body.notes,
        source="manual",
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        customer_email=body.customer_email,
    )
    db.add(appt)
    await db.commit()
    await db.refresh(appt)
    return _appt_to_response(appt)


@router.get("/{appt_id}", response_model=AppointmentResponse)
async def get_appointment(
    appt_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        aid = uuid.UUID(appt_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid appt_id")
    result = await db.execute(
        select(Appointment).where(Appointment.id == aid, Appointment.shop_id == uuid.UUID(shop_id))
    )
    appt = result.scalar_one_or_none()
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return _appt_to_response(appt)


@router.patch("/{appt_id}", response_model=AppointmentResponse)
async def update_appointment(
    appt_id: str,
    body: AppointmentUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        aid = uuid.UUID(appt_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid appt_id")
    result = await db.execute(
        select(Appointment).where(Appointment.id == aid, Appointment.shop_id == uuid.UUID(shop_id))
    )
    appt = result.scalar_one_or_none()
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    for field in ("status", "notes", "starts_at", "ends_at", "service_requested"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(appt, field, val)
    await db.commit()
    await db.refresh(appt)
    return _appt_to_response(appt)


@router.post("/{appt_id}/convert-to-job-card")
async def convert_to_job_card(
    appt_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        aid = uuid.UUID(appt_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid appt_id")
    result = await db.execute(
        select(Appointment).where(Appointment.id == aid, Appointment.shop_id == uuid.UUID(shop_id))
    )
    appt = result.scalar_one_or_none()
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    from sqlalchemy import func as sql_func
    count_result = await db.execute(
        select(sql_func.count(JobCard.id)).where(JobCard.shop_id == uuid.UUID(shop_id))
    )
    count = count_result.scalar() or 0
    number = f"JC-{count + 1:04d}"

    services = []
    if appt.service_requested:
        services = [{"description": appt.service_requested, "labor_hours": 0, "labor_rate": 0, "labor_cost": 0}]

    card = JobCard(
        shop_id=uuid.UUID(shop_id),
        number=number,
        customer_id=appt.customer_id,
        vehicle_id=appt.vehicle_id,
        services=services,
        parts=[],
        technician_ids=[],
        status="active",
    )
    db.add(card)
    appt.job_card_id = card.id
    await db.commit()
    await db.refresh(card)
    return {"job_card_id": str(card.id), "number": card.number}


# ── Public booking endpoints (no auth) ────────────────────────────────────

public_router = APIRouter(prefix="/book", tags=["booking"])


class PublicBookingRequest(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    service_requested: str
    starts_at: str
    ends_at: str


@public_router.get("/{slug}")
async def get_booking_config(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BookingConfig).where(BookingConfig.slug == slug))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="Shop not found")
    import json
    return {
        "slug": config.slug,
        "available_services": json.loads(config.available_services or "[]"),
        "working_hours_start": config.working_hours_start,
        "working_hours_end": config.working_hours_end,
        "slot_duration_minutes": config.slot_duration_minutes,
        "working_days": json.loads(config.working_days or "[1,2,3,4,5]"),
    }


@public_router.post("/{slug}", status_code=status.HTTP_201_CREATED)
async def submit_booking(slug: str, body: PublicBookingRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BookingConfig).where(BookingConfig.slug == slug))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="Shop not found")

    token = secrets.token_urlsafe(16)
    appt = Appointment(
        shop_id=config.shop_id,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        service_requested=body.service_requested,
        status="pending",
        source="booking_link",
        booking_token=token,
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        customer_email=body.customer_email,
    )
    db.add(appt)
    await db.commit()
    return {"booking_token": token, "status": "pending", "message": "Booking received. You'll receive a confirmation shortly."}
```

- [ ] **Step 5: Register routers**

```python
# backend/src/api/main.py — add:
from src.api.appointments import router as appointments_router, public_router as booking_router
app.include_router(appointments_router)
app.include_router(booking_router)
```

- [ ] **Step 6: Update models __init__.py**

```python
from src.models.appointment import Appointment, BookingConfig

__all__ = [
    "Shop", "User", "InspectionSession", "Report", "MediaFile",
    "ChatMessage", "Quote", "Customer", "Vehicle", "CustomerMessage",
    "ShopSettings", "JobCardColumn", "JobCard", "Invoice", "InvoicePaymentEvent",
    "Appointment", "BookingConfig",
]
```

- [ ] **Step 7: Generate migration**

```bash
cd backend
alembic revision --autogenerate -m "add_appointments"
alembic upgrade head
```

- [ ] **Step 8: Run tests**

```bash
cd backend && python -m pytest tests/test_api/test_appointments.py -v
```
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add backend/src/models/appointment.py backend/src/models/__init__.py \
        backend/src/api/appointments.py backend/src/api/main.py \
        backend/tests/test_api/test_appointments.py backend/alembic/versions/
git commit -m "feat(backend): add Appointment, BookingConfig models and appointments API"
```

---

## Task 2: Service Reminder model + config API + reminder job

**Files:**
- Create: `backend/src/models/service_reminder.py`
- Modify: `backend/src/models/__init__.py`
- Create: `backend/src/api/service_reminders.py`
- Modify: `backend/src/api/main.py`
- Test: `backend/tests/test_api/test_service_reminders.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_api/test_service_reminders.py
import uuid

SHOP_ID = "00000000-0000-0000-0000-000000000099"

def test_list_reminder_configs_empty(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    resp = client.get("/reminders/config", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

def test_create_reminder_config(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    cfg = MagicMock()
    cfg.id = uuid.uuid4()
    cfg.shop_id = uuid.UUID(SHOP_ID)
    cfg.service_type = "Oil Change"
    cfg.window_start_months = 3
    cfg.window_end_months = 6
    cfg.sms_enabled = True
    cfg.email_enabled = False
    cfg.message_template = "Hi {first_name}, your {vehicle} is due for an oil change."
    cfg.created_at = "2026-05-01T00:00:00+00:00"
    mock_db.execute.return_value.scalar_one_or_none.return_value = cfg
    resp = client.post(
        "/reminders/config",
        json={
            "service_type": "Oil Change",
            "window_start_months": 3,
            "window_end_months": 6,
            "sms_enabled": True,
            "email_enabled": False,
            "message_template": "Hi {first_name}, your {vehicle} is due for an oil change.",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["service_type"] == "Oil Change"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_service_reminders.py -v
```
Expected: FAIL with `404`

- [ ] **Step 3: Create service_reminder.py model**

```python
# backend/src/models/service_reminder.py
import uuid
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base

DEFAULT_CONFIGS = [
    {"service_type": "Oil Change", "window_start_months": 3, "window_end_months": 6,
     "message_template": "Hi {first_name}, your {vehicle} is due for an oil change. Book now: {booking_link}"},
    {"service_type": "Tire Rotation", "window_start_months": 6, "window_end_months": 12,
     "message_template": "Hi {first_name}, time for a tire rotation on your {vehicle}. Book now: {booking_link}"},
    {"service_type": "Full Service", "window_start_months": 10, "window_end_months": 14,
     "message_template": "Hi {first_name}, your {vehicle} is due for a full service. Book now: {booking_link}"},
    {"service_type": "AC Check", "window_start_months": 10, "window_end_months": 14,
     "message_template": "Hi {first_name}, time to check the AC on your {vehicle}. Book now: {booking_link}"},
]


class ServiceReminderConfig(Base):
    __tablename__ = "service_reminder_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(
        UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    service_type = Column(String(100), nullable=False)
    window_start_months = Column(Integer, nullable=False)
    window_end_months = Column(Integer, nullable=False)
    sms_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=True)
    message_template = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)


class ServiceReminder(Base):
    __tablename__ = "service_reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    config_id = Column(UUID(as_uuid=True), ForeignKey("service_reminder_configs.id", ondelete="CASCADE"), nullable=False)
    service_type = Column(String(100), nullable=False)
    status = Column(String(20), default="active", nullable=False)  # active|booked|inactive
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    last_service_at = Column(DateTime(timezone=True), nullable=True)
    send_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
```

- [ ] **Step 4: Create service_reminders router**

```python
# backend/src/api/service_reminders.py
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.service_reminder import ServiceReminderConfig, ServiceReminder, DEFAULT_CONFIGS
from src.models.customer import Customer

router = APIRouter(prefix="/reminders", tags=["reminders"])


class ReminderConfigCreate(BaseModel):
    service_type: str
    window_start_months: int
    window_end_months: int
    sms_enabled: bool = True
    email_enabled: bool = True
    message_template: Optional[str] = None


class ReminderConfigUpdate(BaseModel):
    window_start_months: Optional[int] = None
    window_end_months: Optional[int] = None
    sms_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    message_template: Optional[str] = None


class ReminderConfigResponse(BaseModel):
    id: str
    shop_id: str
    service_type: str
    window_start_months: int
    window_end_months: int
    sms_enabled: bool
    email_enabled: bool
    message_template: Optional[str] = None
    created_at: str


def _cfg_to_response(c: ServiceReminderConfig) -> ReminderConfigResponse:
    return ReminderConfigResponse(
        id=str(c.id),
        shop_id=str(c.shop_id),
        service_type=c.service_type,
        window_start_months=c.window_start_months,
        window_end_months=c.window_end_months,
        sms_enabled=bool(c.sms_enabled),
        email_enabled=bool(c.email_enabled),
        message_template=c.message_template,
        created_at=str(c.created_at),
    )


async def _get_or_seed_configs(shop_id: uuid.UUID, db: AsyncSession) -> list[ServiceReminderConfig]:
    result = await db.execute(
        select(ServiceReminderConfig).where(ServiceReminderConfig.shop_id == shop_id)
    )
    configs = result.scalars().all()
    if not configs:
        configs = []
        for d in DEFAULT_CONFIGS:
            cfg = ServiceReminderConfig(shop_id=shop_id, **d)
            db.add(cfg)
            configs.append(cfg)
        await db.commit()
        for cfg in configs:
            await db.refresh(cfg)
    return configs


@router.get("/config", response_model=list[ReminderConfigResponse])
async def list_reminder_configs(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    configs = await _get_or_seed_configs(uuid.UUID(shop_id), db)
    return [_cfg_to_response(c) for c in configs]


@router.post("/config", response_model=ReminderConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder_config(
    body: ReminderConfigCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    cfg = ServiceReminderConfig(
        shop_id=uuid.UUID(shop_id),
        service_type=body.service_type,
        window_start_months=body.window_start_months,
        window_end_months=body.window_end_months,
        sms_enabled=body.sms_enabled,
        email_enabled=body.email_enabled,
        message_template=body.message_template,
    )
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return _cfg_to_response(cfg)


@router.patch("/config/{config_id}", response_model=ReminderConfigResponse)
async def update_reminder_config(
    config_id: str,
    body: ReminderConfigUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        cid = uuid.UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid config_id")
    result = await db.execute(
        select(ServiceReminderConfig).where(
            ServiceReminderConfig.id == cid, ServiceReminderConfig.shop_id == uuid.UUID(shop_id)
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Config not found")
    for field in ("window_start_months", "window_end_months", "sms_enabled", "email_enabled", "message_template"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(cfg, field, val)
    await db.commit()
    await db.refresh(cfg)
    return _cfg_to_response(cfg)


@router.post("/run")
async def run_reminder_job(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Runs the monthly reminder job for this shop:
    - For each active ServiceReminder, check if customer is within window
    - Send SMS/email if due (last_sent_at is None or > 30 days ago)
    - Mark inactive if > 12 months since last service
    Returns count of reminders sent.
    """
    sid = uuid.UUID(shop_id)
    configs_result = await db.execute(
        select(ServiceReminderConfig).where(ServiceReminderConfig.shop_id == sid)
    )
    configs = {str(c.id): c for c in configs_result.scalars().all()}

    reminders_result = await db.execute(
        select(ServiceReminder).where(
            ServiceReminder.shop_id == sid, ServiceReminder.status == "active"
        )
    )
    reminders = reminders_result.scalars().all()

    now = datetime.now(timezone.utc)
    sent_count = 0

    for reminder in reminders:
        cfg = configs.get(str(reminder.config_id))
        if cfg is None:
            continue

        last_service = reminder.last_service_at
        if last_service is None:
            continue

        months_since = (now - last_service).days / 30.0

        # Hard stop: 12 months no visit → mark inactive
        if months_since > 12:
            reminder.status = "inactive"
            continue

        # In window?
        if not (cfg.window_start_months <= months_since <= cfg.window_end_months):
            continue

        # Already sent within 30 days?
        if reminder.last_sent_at and (now - reminder.last_sent_at).days < 30:
            continue

        # Send SMS/email (stub — actual send via Twilio/email service)
        # TODO: integrate with Twilio for SMS, email provider for email
        reminder.last_sent_at = now
        reminder.send_count = (reminder.send_count or 0) + 1
        sent_count += 1

    await db.commit()
    return {"reminders_sent": sent_count}
```

- [ ] **Step 5: Register router**

```python
# backend/src/api/main.py — add:
from src.api.service_reminders import router as service_reminders_router
app.include_router(service_reminders_router)
```

- [ ] **Step 6: Update models __init__.py**

```python
from src.models.service_reminder import ServiceReminderConfig, ServiceReminder

__all__ = [
    "Shop", "User", "InspectionSession", "Report", "MediaFile",
    "ChatMessage", "Quote", "Customer", "Vehicle", "CustomerMessage",
    "ShopSettings", "JobCardColumn", "JobCard", "Invoice", "InvoicePaymentEvent",
    "Appointment", "BookingConfig", "ServiceReminderConfig", "ServiceReminder",
]
```

- [ ] **Step 7: Generate migration**

```bash
cd backend
alembic revision --autogenerate -m "add_service_reminders"
alembic upgrade head
```

- [ ] **Step 8: Run tests**

```bash
cd backend && python -m pytest tests/test_api/test_service_reminders.py -v
```

- [ ] **Step 9: Commit**

```bash
git add backend/src/models/service_reminder.py backend/src/models/__init__.py \
        backend/src/api/service_reminders.py backend/src/api/main.py \
        backend/tests/test_api/test_service_reminders.py backend/alembic/versions/
git commit -m "feat(backend): add ServiceReminderConfig model, config API, and reminder job endpoint"
```

---

## Task 3: Frontend types + API functions

**Files:**
- Modify: `web/lib/types.ts`
- Modify: `web/lib/api.ts`

- [ ] **Step 1: Add types to web/lib/types.ts**

```typescript
// Append to web/lib/types.ts:

// ── Appointments ──────────────────────────────────────────────────────────

export interface Appointment {
  id: string
  shop_id: string
  customer_id: string | null
  vehicle_id: string | null
  starts_at: string
  ends_at: string
  service_requested: string | null
  status: 'pending' | 'confirmed' | 'cancelled'
  notes: string | null
  source: 'manual' | 'booking_link'
  job_card_id: string | null
  customer_name: string | null
  customer_phone: string | null
  customer_email: string | null
  created_at: string
}

export interface BookingConfig {
  slug: string
  available_services: string[]
  working_hours_start: string
  working_hours_end: string
  slot_duration_minutes: string
  working_days: number[]
}

// ── Service Reminders ─────────────────────────────────────────────────────

export interface ServiceReminderConfig {
  id: string
  shop_id: string
  service_type: string
  window_start_months: number
  window_end_months: number
  sms_enabled: boolean
  email_enabled: boolean
  message_template: string | null
  created_at: string
}
```

- [ ] **Step 2: Add API functions to web/lib/api.ts**

```typescript
// Append to web/lib/api.ts:
import type { Appointment, BookingConfig, ServiceReminderConfig } from './types'

// ── Appointments ──────────────────────────────────────────────────────────

export const getAppointments = (params?: { year?: number; month?: number }): Promise<Appointment[]> =>
  api.get('/appointments', { params }).then(r => r.data)

export const createAppointment = (data: Partial<Appointment>): Promise<Appointment> =>
  api.post('/appointments', data).then(r => r.data)

export const updateAppointment = (id: string, data: Partial<Appointment>): Promise<Appointment> =>
  api.patch(`/appointments/${id}`, data).then(r => r.data)

export const convertAppointmentToJobCard = (id: string): Promise<{ job_card_id: string; number: string }> =>
  api.post(`/appointments/${id}/convert-to-job-card`).then(r => r.data)

// ── Service Reminders ─────────────────────────────────────────────────────

export const getReminderConfigs = (): Promise<ServiceReminderConfig[]> =>
  api.get('/reminders/config').then(r => r.data)

export const createReminderConfig = (data: Partial<ServiceReminderConfig>): Promise<ServiceReminderConfig> =>
  api.post('/reminders/config', data).then(r => r.data)

export const updateReminderConfig = (id: string, data: Partial<ServiceReminderConfig>): Promise<ServiceReminderConfig> =>
  api.patch(`/reminders/config/${id}`, data).then(r => r.data)

export const runReminderJob = (): Promise<{ reminders_sent: number }> =>
  api.post('/reminders/run').then(r => r.data)
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd web && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add web/lib/types.ts web/lib/api.ts
git commit -m "feat(web): add Appointment and ServiceReminderConfig types and API functions"
```

---

## Task 4: Appointments calendar page

**Files:**
- Create: `web/app/appointments/page.tsx`
- Create: `web/components/appointments/CalendarGrid.tsx`
- Create: `web/components/appointments/AppointmentCard.tsx`
- Create: `web/components/appointments/NewAppointmentModal.tsx`

- [ ] **Step 1: Create CalendarGrid component**

```tsx
// web/components/appointments/CalendarGrid.tsx
'use client'
import type { Appointment } from '@/lib/types'

interface Props {
  year: number
  month: number  // 1–12
  appointments: Appointment[]
  onDayClick: (date: Date) => void
  onAppointmentClick: (appt: Appointment) => void
}

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const STATUS_COLORS: Record<string, string> = {
  confirmed: '#4ade80', pending: '#fbbf24', cancelled: 'rgba(255,255,255,0.2)',
}

export default function CalendarGrid({ year, month, appointments, onDayClick, onAppointmentClick }: Props) {
  const firstDay = new Date(year, month - 1, 1).getDay()
  const daysInMonth = new Date(year, month, 0).getDate()
  const cells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ]
  while (cells.length % 7 !== 0) cells.push(null)

  const apptsByDay: Record<number, Appointment[]> = {}
  for (const a of appointments) {
    const d = new Date(a.starts_at).getDate()
    if (!apptsByDay[d]) apptsByDay[d] = []
    apptsByDay[d].push(a)
  }

  const today = new Date()
  const isToday = (day: number) =>
    today.getFullYear() === year && today.getMonth() + 1 === month && today.getDate() === day

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '14px 24px' }}>
      {/* Day headers */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4, marginBottom: 4 }}>
        {DAYS.map(d => (
          <div key={d} style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,0.3)', textAlign: 'center', padding: '4px 0', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            {d}
          </div>
        ))}
      </div>
      {/* Calendar grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}>
        {cells.map((day, i) => (
          <div
            key={i}
            onClick={() => day && onDayClick(new Date(year, month - 1, day))}
            style={{
              minHeight: 80, background: day ? 'rgba(255,255,255,0.02)' : 'transparent',
              border: day ? `1px solid ${isToday(day!) ? 'rgba(217,119,6,0.5)' : 'rgba(255,255,255,0.06)'}` : 'none',
              borderRadius: 8, padding: '6px 8px', cursor: day ? 'pointer' : 'default',
            }}
            onMouseEnter={e => { if (day) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)' }}
            onMouseLeave={e => { if (day) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.02)' }}
          >
            {day && (
              <>
                <div style={{
                  fontSize: 12, fontWeight: isToday(day) ? 700 : 400,
                  color: isToday(day) ? '#d97706' : 'rgba(255,255,255,0.6)',
                  marginBottom: 4,
                }}>
                  {day}
                </div>
                {(apptsByDay[day] ?? []).slice(0, 3).map(a => (
                  <div
                    key={a.id}
                    onClick={e => { e.stopPropagation(); onAppointmentClick(a) }}
                    style={{
                      fontSize: 10, fontWeight: 600, padding: '2px 5px', borderRadius: 4, marginBottom: 2,
                      background: `${STATUS_COLORS[a.status] ?? '#94a3b8'}22`,
                      color: STATUS_COLORS[a.status] ?? '#94a3b8',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}
                  >
                    {new Date(a.starts_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} {a.customer_name ?? a.service_requested ?? 'Appointment'}
                  </div>
                ))}
                {(apptsByDay[day]?.length ?? 0) > 3 && (
                  <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)' }}>+{(apptsByDay[day]?.length ?? 0) - 3} more</div>
                )}
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create NewAppointmentModal**

```tsx
// web/components/appointments/NewAppointmentModal.tsx
'use client'
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createAppointment } from '@/lib/api'

interface Props {
  defaultDate: Date
  onClose: () => void
}

export default function NewAppointmentModal({ defaultDate, onClose }: Props) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    customer_name: '',
    service_requested: '',
    starts_at: defaultDate.toISOString().slice(0, 16),
    ends_at: new Date(defaultDate.getTime() + 3600000).toISOString().slice(0, 16),
    status: 'confirmed',
    notes: '',
  })

  const create = useMutation({
    mutationFn: () => createAppointment({
      ...form,
      starts_at: new Date(form.starts_at).toISOString(),
      ends_at: new Date(form.ends_at).toISOString(),
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['appointments'] }); onClose() },
  })

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
      <div style={{ background: '#1a1a1a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 24, width: 380 }}>
        <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 18 }}>New Appointment</div>
        {[
          { key: 'customer_name', label: 'Customer name', type: 'text' },
          { key: 'service_requested', label: 'Service', type: 'text' },
          { key: 'starts_at', label: 'Start', type: 'datetime-local' },
          { key: 'ends_at', label: 'End', type: 'datetime-local' },
        ].map(({ key, label, type }) => (
          <div key={key} style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
            <input
              type={type}
              value={(form as Record<string, string>)[key]}
              onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
              style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, padding: '8px 10px', color: '#fff', fontSize: 13 }}
            />
          </div>
        ))}
        <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
          <button onClick={onClose} style={{ flex: 1, height: 36, borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.6)', cursor: 'pointer' }}>
            Cancel
          </button>
          <button
            onClick={() => create.mutate()}
            disabled={create.isPending}
            style={{ flex: 1, height: 36, borderRadius: 8, border: 'none', background: '#d97706', color: '#fff', fontWeight: 600, cursor: 'pointer' }}
          >
            {create.isPending ? 'Saving…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create appointments page**

```tsx
// web/app/appointments/page.tsx
'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import CalendarGrid from '@/components/appointments/CalendarGrid'
import NewAppointmentModal from '@/components/appointments/NewAppointmentModal'
import type { Appointment } from '@/lib/types'
import { getAppointments, updateAppointment, convertAppointmentToJobCard } from '@/lib/api'

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

export default function AppointmentsPage() {
  const qc = useQueryClient()
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [showNewModal, setShowNewModal] = useState(false)
  const [selectedDate, setSelectedDate] = useState(now)
  const [selectedAppt, setSelectedAppt] = useState<Appointment | null>(null)

  const { data: appointments = [] } = useQuery({
    queryKey: ['appointments', year, month],
    queryFn: () => getAppointments({ year, month }),
  })

  const convertToJC = useMutation({
    mutationFn: (id: string) => convertAppointmentToJobCard(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['appointments'] }); setSelectedAppt(null) },
  })

  const updateAppt = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Appointment> }) => updateAppointment(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['appointments'] }),
  })

  const prevMonth = () => { if (month === 1) { setMonth(12); setYear(y => y - 1) } else setMonth(m => m - 1) }
  const nextMonth = () => { if (month === 12) { setMonth(1); setYear(y => y + 1) } else setMonth(m => m + 1) }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px 0', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Appointments</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button onClick={prevMonth} style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, width: 28, height: 28, color: '#fff', cursor: 'pointer', fontSize: 14 }}>‹</button>
            <span style={{ fontSize: 14, fontWeight: 600, minWidth: 120, textAlign: 'center' }}>{MONTHS[month - 1]} {year}</span>
            <button onClick={nextMonth} style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, width: 28, height: 28, color: '#fff', cursor: 'pointer', fontSize: 14 }}>›</button>
          </div>
        </div>
        <button
          onClick={() => { setSelectedDate(new Date(year, month - 1, 1)); setShowNewModal(true) }}
          style={{ height: 32, padding: '0 14px', borderRadius: 7, border: 'none', background: '#d97706', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
        >
          + New Appointment
        </button>
      </div>

      <CalendarGrid
        year={year}
        month={month}
        appointments={appointments}
        onDayClick={date => { setSelectedDate(date); setShowNewModal(true) }}
        onAppointmentClick={setSelectedAppt}
      />

      {showNewModal && (
        <NewAppointmentModal defaultDate={selectedDate} onClose={() => setShowNewModal(false)} />
      )}

      {/* Appointment detail sidebar */}
      {selectedAppt && (
        <div style={{
          position: 'fixed', right: 0, top: 0, bottom: 0, width: 360,
          background: '#141414', borderLeft: '1px solid rgba(255,255,255,0.08)',
          display: 'flex', flexDirection: 'column', zIndex: 50,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '18px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
            <div style={{ fontSize: 16, fontWeight: 700 }}>Appointment</div>
            <button onClick={() => setSelectedAppt(null)} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', fontSize: 20, cursor: 'pointer' }}>×</button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
            {[
              { label: 'Customer', value: selectedAppt.customer_name ?? '—' },
              { label: 'Service', value: selectedAppt.service_requested ?? '—' },
              { label: 'Time', value: `${new Date(selectedAppt.starts_at).toLocaleString()} – ${new Date(selectedAppt.ends_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` },
              { label: 'Phone', value: selectedAppt.customer_phone ?? '—' },
              { label: 'Notes', value: selectedAppt.notes ?? '—' },
            ].map(({ label, value }) => (
              <div key={label} style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.8)' }}>{value}</div>
              </div>
            ))}

            {/* Status toggle */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>Status</div>
              <div style={{ display: 'flex', gap: 6 }}>
                {['pending', 'confirmed', 'cancelled'].map(s => (
                  <button
                    key={s}
                    onClick={() => updateAppt.mutate({ id: selectedAppt.id, data: { status: s as Appointment['status'] } })}
                    style={{
                      padding: '4px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.1)',
                      background: selectedAppt.status === s ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.03)',
                      color: selectedAppt.status === s ? '#fff' : 'rgba(255,255,255,0.45)',
                      fontSize: 11, fontWeight: 600, cursor: 'pointer', textTransform: 'capitalize',
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div style={{ padding: '14px 20px', borderTop: '1px solid rgba(255,255,255,0.07)' }}>
            {!selectedAppt.job_card_id ? (
              <button
                onClick={() => convertToJC.mutate(selectedAppt.id)}
                disabled={convertToJC.isPending}
                style={{ width: '100%', height: 36, borderRadius: 8, border: 'none', background: '#d97706', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
              >
                {convertToJC.isPending ? 'Creating…' : '→ Convert to Job Card'}
              </button>
            ) : (
              <div style={{ fontSize: 12, color: '#4ade80', textAlign: 'center' }}>
                ✓ Job Card created: {selectedAppt.job_card_id.slice(0, 8)}…
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Verify calendar renders**

```bash
cd web && npm run dev
```
Open http://localhost:3000/appointments — should show the current month calendar grid, today highlighted in amber. Click any day → new appointment modal opens. Existing appointments appear as colored pills on their day.

- [ ] **Step 5: Commit**

```bash
git add web/app/appointments/ web/components/appointments/
git commit -m "feat(web): add Appointments calendar page with month view and new appointment modal"
```

---

## Task 5: Public booking page

**Files:**
- Create: `web/app/book/[slug]/page.tsx`

- [ ] **Step 1: Create public booking page**

```tsx
// web/app/book/[slug]/page.tsx
'use client'
import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { BookingConfig } from '@/lib/types'

interface Props {
  params: { slug: string }
}

export default function BookingPage({ params }: Props) {
  const { slug } = params
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [form, setForm] = useState({
    customer_name: '',
    customer_phone: '',
    customer_email: '',
    service_requested: '',
    starts_at: '',
    ends_at: '',
  })
  const [submitted, setSubmitted] = useState(false)

  const { data: config, isLoading, error } = useQuery<BookingConfig>({
    queryKey: ['booking-config', slug],
    queryFn: () => api.get(`/book/${slug}`).then(r => r.data),
  })

  const submit = useMutation({
    mutationFn: () => api.post(`/book/${slug}`, form).then(r => r.data),
    onSuccess: () => setSubmitted(true),
  })

  if (isLoading) return (
    <div style={{ minHeight: '100vh', background: '#0d0d0d', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)' }}>Loading…</div>
  )
  if (error || !config) return (
    <div style={{ minHeight: '100vh', background: '#0d0d0d', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f87171' }}>Shop not found</div>
  )
  if (submitted) return (
    <div style={{ minHeight: '100vh', background: '#0d0d0d', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
      <div style={{ textAlign: 'center', maxWidth: 400, padding: 24 }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>✓</div>
        <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Booking received!</div>
        <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.5)' }}>We'll confirm your appointment shortly via SMS.</div>
      </div>
    </div>
  )

  return (
    <div style={{ minHeight: '100vh', background: '#0d0d0d', color: '#fff', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 16px' }}>
      <div style={{ width: '100%', maxWidth: 480 }}>
        <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Book an Appointment</div>
        <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)', marginBottom: 32 }}>Step {step} of 3</div>

        {step === 1 && (
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>What service do you need?</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {(config.available_services.length > 0 ? config.available_services : ['Oil Change', 'Tire Rotation', 'Brake Inspection', 'Full Service']).map(svc => (
                <div
                  key={svc}
                  onClick={() => { setForm(f => ({ ...f, service_requested: svc })); setStep(2) }}
                  style={{
                    padding: '14px 16px', borderRadius: 10, cursor: 'pointer', fontSize: 14, fontWeight: 600,
                    border: `1px solid ${form.service_requested === svc ? '#d97706' : 'rgba(255,255,255,0.1)'}`,
                    background: form.service_requested === svc ? 'rgba(217,119,6,0.08)' : 'rgba(255,255,255,0.02)',
                  }}
                >
                  {svc}
                </div>
              ))}
              <div style={{ marginTop: 8 }}>
                <input
                  placeholder="Other (type here)"
                  value={form.service_requested}
                  onChange={e => setForm(f => ({ ...f, service_requested: e.target.value }))}
                  style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '12px 14px', color: '#fff', fontSize: 13 }}
                />
              </div>
            </div>
            <button
              disabled={!form.service_requested}
              onClick={() => setStep(2)}
              style={{ marginTop: 20, width: '100%', height: 44, borderRadius: 10, border: 'none', background: form.service_requested ? '#d97706' : 'rgba(255,255,255,0.1)', color: '#fff', fontWeight: 700, fontSize: 14, cursor: form.service_requested ? 'pointer' : 'default' }}
            >
              Next
            </button>
          </div>
        )}

        {step === 2 && (
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>When works for you?</div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 6 }}>PREFERRED DATE & TIME</div>
              <input
                type="datetime-local"
                value={form.starts_at}
                onChange={e => {
                  const start = new Date(e.target.value)
                  const end = new Date(start.getTime() + parseInt(config.slot_duration_minutes) * 60000)
                  setForm(f => ({ ...f, starts_at: e.target.value, ends_at: end.toISOString().slice(0, 16) }))
                }}
                style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '12px 14px', color: '#fff', fontSize: 13 }}
              />
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <button onClick={() => setStep(1)} style={{ flex: 1, height: 44, borderRadius: 10, border: '1px solid rgba(255,255,255,0.1)', background: 'transparent', color: 'rgba(255,255,255,0.6)', cursor: 'pointer' }}>Back</button>
              <button disabled={!form.starts_at} onClick={() => setStep(3)} style={{ flex: 2, height: 44, borderRadius: 10, border: 'none', background: form.starts_at ? '#d97706' : 'rgba(255,255,255,0.1)', color: '#fff', fontWeight: 700, cursor: form.starts_at ? 'pointer' : 'default' }}>Next</button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Your details</div>
            {[
              { key: 'customer_name', label: 'Full name', type: 'text', required: true },
              { key: 'customer_phone', label: 'Phone number', type: 'tel', required: true },
              { key: 'customer_email', label: 'Email (optional)', type: 'email', required: false },
            ].map(({ key, label, type }) => (
              <div key={key} style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 6 }}>{label.toUpperCase()}</div>
                <input
                  type={type}
                  value={(form as Record<string, string>)[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '12px 14px', color: '#fff', fontSize: 13 }}
                />
              </div>
            ))}
            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <button onClick={() => setStep(2)} style={{ flex: 1, height: 44, borderRadius: 10, border: '1px solid rgba(255,255,255,0.1)', background: 'transparent', color: 'rgba(255,255,255,0.6)', cursor: 'pointer' }}>Back</button>
              <button
                disabled={!form.customer_name || !form.customer_phone || submit.isPending}
                onClick={() => submit.mutate()}
                style={{ flex: 2, height: 44, borderRadius: 10, border: 'none', background: (form.customer_name && form.customer_phone) ? '#d97706' : 'rgba(255,255,255,0.1)', color: '#fff', fontWeight: 700, cursor: (form.customer_name && form.customer_phone) ? 'pointer' : 'default' }}
              >
                {submit.isPending ? 'Booking…' : 'Confirm Booking'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify public booking page**

Open http://localhost:3000/book/test-shop in a browser (no auth required). Should show the 3-step flow: service → time → confirm. Note: you need a BookingConfig with slug "test-shop" in the DB first. To seed one via the API:

```bash
curl -X POST http://localhost:8000/settings/booking-config \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"slug":"test-shop"}'
```

(Add a `POST /settings/booking-config` endpoint if not yet present, or seed via psql.)

- [ ] **Step 3: Commit**

```bash
git add web/app/book/
git commit -m "feat(web): add public customer booking page with 3-step flow"
```

---

## Task 6: Service Reminders settings page + dashboard wiring

**Files:**
- Create: `web/app/reminders/page.tsx`
- Modify: `web/components/dashboard/tiles.tsx`

- [ ] **Step 1: Create reminders settings page**

```tsx
// web/app/reminders/page.tsx
'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getReminderConfigs, updateReminderConfig, runReminderJob } from '@/lib/api'
import type { ServiceReminderConfig } from '@/lib/types'

export default function RemindersPage() {
  const qc = useQueryClient()
  const { data: configs = [], isLoading } = useQuery({
    queryKey: ['reminder-configs'],
    queryFn: getReminderConfigs,
  })

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ServiceReminderConfig> }) =>
      updateReminderConfig(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reminder-configs'] }),
  })

  const runJob = useMutation({
    mutationFn: runReminderJob,
  })

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px 14px', flexShrink: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Service Reminders</div>
        <button
          onClick={() => runJob.mutate()}
          disabled={runJob.isPending}
          style={{ height: 32, padding: '0 14px', borderRadius: 7, border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.65)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
        >
          {runJob.isPending ? 'Running…' : 'Run job now'}
        </button>
      </div>

      {runJob.isSuccess && (
        <div style={{ margin: '0 24px 12px', padding: '10px 14px', background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', borderRadius: 8, fontSize: 13, color: '#4ade80' }}>
          ✓ Sent {runJob.data?.reminders_sent ?? 0} reminder{runJob.data?.reminders_sent !== 1 ? 's' : ''}
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', padding: '0 24px 20px' }}>
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)', marginBottom: 16, lineHeight: 1.6 }}>
          Reminders are sent monthly. Customers in the service window receive a message every 30 days until they book. Hard stop at 12 months with no visit.
        </div>

        {isLoading ? (
          <div style={{ color: 'rgba(255,255,255,0.3)' }}>Loading…</div>
        ) : configs.map(cfg => (
          <div key={cfg.id} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, padding: 16, marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div style={{ fontSize: 14, fontWeight: 700 }}>{cfg.service_type}</div>
              <div style={{ display: 'flex', gap: 6 }}>
                {['sms_enabled', 'email_enabled'].map(field => (
                  <button
                    key={field}
                    onClick={() => update.mutate({ id: cfg.id, data: { [field]: !cfg[field as keyof ServiceReminderConfig] } })}
                    style={{
                      padding: '3px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer',
                      background: cfg[field as keyof ServiceReminderConfig] ? 'rgba(217,119,6,0.15)' : 'rgba(255,255,255,0.04)',
                      color: cfg[field as keyof ServiceReminderConfig] ? '#fbbf24' : 'rgba(255,255,255,0.35)',
                      fontSize: 10, fontWeight: 700,
                    }}
                  >
                    {field === 'sms_enabled' ? 'SMS' : 'Email'}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginBottom: 8 }}>
              Window: {cfg.window_start_months}–{cfg.window_end_months} months after last service
            </div>
            {cfg.message_template && (
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', fontStyle: 'italic', padding: '8px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: 6 }}>
                "{cfg.message_template}"
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Update dashboard tiles**

In `web/components/dashboard/tiles.tsx`, find Appointments and Reminders tile entries and set them to `status: 'live'` with appropriate `href` values:
- Appointments → `href: '/appointments'`
- Reminders → `href: '/reminders'`

- [ ] **Step 3: Verify reminders page**

Open http://localhost:3000/reminders — should show 4 default reminder configs (Oil Change, Tire Rotation, Full Service, AC Check) with SMS/Email toggles. Clicking "Run job now" should call the backend and show a count of reminders sent.

- [ ] **Step 4: Commit**

```bash
git add web/app/reminders/page.tsx web/components/dashboard/tiles.tsx
git commit -m "feat(web): add Service Reminders settings page and wire dashboard tiles"
```
