import uuid
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, cast, Integer
from sqlalchemy import func as sql_func
from pydantic import BaseModel
from typing import Optional, Literal
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.appointment import Appointment, BookingConfig
from src.models.job_card import JobCard

router = APIRouter(prefix="/appointments", tags=["appointments"])
public_router = APIRouter(prefix="/book", tags=["booking"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AppointmentCreate(BaseModel):
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    starts_at: str
    ends_at: str
    service_requested: Optional[str] = None
    status: Literal["pending", "confirmed", "cancelled"] = "pending"
    notes: Optional[str] = None
    source: Literal["manual", "booking_link"] = "manual"
    job_card_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None


class AppointmentUpdate(BaseModel):
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
    service_requested: Optional[str] = None
    status: Optional[Literal["pending", "confirmed", "cancelled"]] = None
    notes: Optional[str] = None
    job_card_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None


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
    booking_token: Optional[str] = None
    job_card_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    created_at: Optional[str] = None


class BookingSubmit(BaseModel):
    starts_at: str
    ends_at: str
    service_requested: Optional[str] = None
    customer_name: str
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    notes: Optional[str] = None


class BookingConfigResponse(BaseModel):
    id: str
    shop_id: str
    slug: str
    available_services: str
    working_hours_start: str
    working_hours_end: str
    slot_duration_minutes: str
    working_days: str
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt(val) -> str:
    """Return ISO string from datetime or passthrough if already a string."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    return val.isoformat()


def _appt_to_response(a: Appointment) -> AppointmentResponse:
    return AppointmentResponse(
        id=str(a.id),
        shop_id=str(a.shop_id),
        customer_id=str(a.customer_id) if a.customer_id else None,
        vehicle_id=str(a.vehicle_id) if a.vehicle_id else None,
        starts_at=_dt(a.starts_at),
        ends_at=_dt(a.ends_at),
        service_requested=a.service_requested,
        status=a.status,
        notes=a.notes,
        source=a.source,
        booking_token=a.booking_token,
        job_card_id=str(a.job_card_id) if a.job_card_id else None,
        customer_name=a.customer_name,
        customer_phone=a.customer_phone,
        customer_email=a.customer_email,
        created_at=_dt(a.created_at),
    )


def _cfg_to_response(cfg: BookingConfig) -> BookingConfigResponse:
    return BookingConfigResponse(
        id=str(cfg.id),
        shop_id=str(cfg.shop_id),
        slug=cfg.slug,
        available_services=cfg.available_services or "[]",
        working_hours_start=cfg.working_hours_start or "08:00",
        working_hours_end=cfg.working_hours_end or "17:00",
        slot_duration_minutes=cfg.slot_duration_minutes or "60",
        working_days=cfg.working_days or "[1,2,3,4,5]",
        created_at=cfg.created_at.isoformat() if cfg.created_at else "",
    )


# ---------------------------------------------------------------------------
# Routes — convert-to-job-card MUST come before /{appt_id}
# ---------------------------------------------------------------------------

@router.get("", response_model=list[AppointmentResponse])
async def list_appointments(
    year: Optional[int] = None,
    month: Optional[int] = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    q = select(Appointment).where(Appointment.shop_id == sid)
    if year is not None:
        q = q.where(sql_func.extract("year", Appointment.starts_at) == year)
    if month is not None:
        q = q.where(sql_func.extract("month", Appointment.starts_at) == month)
    result = await db.execute(q.order_by(Appointment.starts_at.asc()))
    return [_appt_to_response(a) for a in result.scalars().all()]


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    body: AppointmentCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    appt = Appointment(
        shop_id=sid,
        customer_id=uuid.UUID(body.customer_id) if body.customer_id else None,
        vehicle_id=uuid.UUID(body.vehicle_id) if body.vehicle_id else None,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        service_requested=body.service_requested,
        status=body.status,
        notes=body.notes,
        source=body.source,
        job_card_id=uuid.UUID(body.job_card_id) if body.job_card_id else None,
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        customer_email=body.customer_email,
    )
    db.add(appt)
    await db.commit()
    await db.refresh(appt)
    return _appt_to_response(appt)


@router.post(
    "/convert-to-job-card",
    status_code=status.HTTP_201_CREATED,
)
async def convert_to_job_card(
    appt_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    """This route handles /appointments/convert-to-job-card with appt_id as query param.
    See the /{appt_id}/convert-to-job-card route below for the primary endpoint."""
    raise HTTPException(status_code=422, detail="Use POST /appointments/{appt_id}/convert-to-job-card")


@router.post(
    "/{appt_id}/convert-to-job-card",
    status_code=status.HTTP_201_CREATED,
)
async def convert_appointment_to_job_card(
    appt_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        aid = uuid.UUID(appt_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid appt_id")

    sid = uuid.UUID(shop_id)
    result = await db.execute(
        select(Appointment).where(Appointment.id == aid, Appointment.shop_id == sid)
    )
    appt = result.scalar_one_or_none()
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # MAX-based numbering to avoid duplicates after deletion
    result = await db.execute(
        select(sql_func.max(
            cast(sql_func.split_part(JobCard.number, "-", 2), Integer)
        )).where(JobCard.shop_id == sid)
    )
    last_n = result.scalar()
    number = f"JC-{(last_n or 0) + 1:04d}"

    card = JobCard(
        shop_id=sid,
        number=number,
        customer_id=appt.customer_id,
        vehicle_id=appt.vehicle_id,
        notes=appt.notes,
        status="active",
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)

    # Link the appointment to the new job card
    appt.job_card_id = card.id
    await db.commit()

    return {"job_card_id": str(card.id), "number": card.number}


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

    if body.customer_id is not None:
        appt.customer_id = uuid.UUID(body.customer_id) if body.customer_id else None
    if body.vehicle_id is not None:
        appt.vehicle_id = uuid.UUID(body.vehicle_id) if body.vehicle_id else None
    if body.starts_at is not None:
        appt.starts_at = body.starts_at
    if body.ends_at is not None:
        appt.ends_at = body.ends_at
    if body.service_requested is not None:
        appt.service_requested = body.service_requested
    if body.status is not None:
        appt.status = body.status
    if body.notes is not None:
        appt.notes = body.notes
    if body.job_card_id is not None:
        appt.job_card_id = uuid.UUID(body.job_card_id) if body.job_card_id else None
    if body.customer_name is not None:
        appt.customer_name = body.customer_name
    if body.customer_phone is not None:
        appt.customer_phone = body.customer_phone
    if body.customer_email is not None:
        appt.customer_email = body.customer_email

    await db.commit()
    await db.refresh(appt)
    return _appt_to_response(appt)


# ---------------------------------------------------------------------------
# Public booking routes (no auth)
# ---------------------------------------------------------------------------

@public_router.get("/{slug}", response_model=BookingConfigResponse)
async def get_booking_config(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BookingConfig).where(BookingConfig.slug == slug)
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Booking page not found")
    return _cfg_to_response(cfg)


@public_router.post("/{slug}", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def submit_booking(
    slug: str,
    body: BookingSubmit,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BookingConfig).where(BookingConfig.slug == slug)
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Booking page not found")

    token = secrets.token_urlsafe(32)
    appt = Appointment(
        shop_id=cfg.shop_id,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        service_requested=body.service_requested,
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        customer_email=body.customer_email,
        notes=body.notes,
        status="pending",
        source="booking_link",
        booking_token=token,
    )
    db.add(appt)
    await db.commit()
    await db.refresh(appt)
    return _appt_to_response(appt)
