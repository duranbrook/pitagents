import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_user_id, get_current_shop_id
from src.models.time_entry import TimeEntry, VALID_TASK_TYPES

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
        started_at=e.started_at.isoformat(),
        ended_at=e.ended_at.isoformat() if e.ended_at else None,
        duration_minutes=e.duration_minutes,
        notes=e.notes,
        qb_synced=bool(e.qb_synced),
        created_at=e.created_at.isoformat() if e.created_at else "",
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


@router.post("/clock-in", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
async def clock_in(
    body: ClockInRequest,
    user_id: str = Depends(get_current_user_id),
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    if body.task_type not in VALID_TASK_TYPES:
        raise HTTPException(status_code=422, detail=f"task_type must be one of {VALID_TASK_TYPES}")
    existing = await db.execute(
        select(TimeEntry).where(
            TimeEntry.shop_id == uuid.UUID(shop_id),
            TimeEntry.user_id == uuid.UUID(user_id),
            TimeEntry.ended_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already clocked in")
    entry = TimeEntry(
        shop_id=uuid.UUID(shop_id),
        user_id=uuid.UUID(user_id),
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
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        eid = uuid.UUID(entry_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid entry_id")
    result = await db.execute(
        select(TimeEntry).where(TimeEntry.id == eid, TimeEntry.shop_id == uuid.UUID(shop_id))
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Time entry not found")
    if entry.ended_at:
        raise HTTPException(status_code=400, detail="Already clocked out")
    now = datetime.now(timezone.utc)
    entry.ended_at = now
    started = entry.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    delta = now - started
    entry.duration_minutes = int(delta.total_seconds() / 60)
    await db.commit()
    await db.refresh(entry)
    return _entry_to_response(entry)
