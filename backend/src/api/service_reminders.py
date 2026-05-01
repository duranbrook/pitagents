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

router = APIRouter(prefix="/reminders", tags=["reminders"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ReminderConfigCreate(BaseModel):
    service_type: str
    window_start_months: int
    window_end_months: int
    sms_enabled: bool = True
    email_enabled: bool = True
    message_template: Optional[str] = None


class ReminderConfigUpdate(BaseModel):
    service_type: Optional[str] = None
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
    created_at: Optional[str] = None


class RunReminderResponse(BaseModel):
    reminders_sent: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg_to_response(cfg: ServiceReminderConfig) -> ReminderConfigResponse:
    return ReminderConfigResponse(
        id=str(cfg.id),
        shop_id=str(cfg.shop_id),
        service_type=cfg.service_type,
        window_start_months=cfg.window_start_months,
        window_end_months=cfg.window_end_months,
        sms_enabled=bool(cfg.sms_enabled),
        email_enabled=bool(cfg.email_enabled),
        message_template=cfg.message_template,
        created_at=cfg.created_at.isoformat() if cfg.created_at else "",
    )


# ---------------------------------------------------------------------------
# Routes — GET/POST /reminders/config before PATCH /reminders/config/{id}
# then POST /reminders/run
# ---------------------------------------------------------------------------

@router.get("/config", response_model=list[ReminderConfigResponse])
async def list_reminder_configs(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    result = await db.execute(
        select(ServiceReminderConfig).where(ServiceReminderConfig.shop_id == sid)
        .order_by(ServiceReminderConfig.created_at.asc())
    )
    configs = result.scalars().all()

    if not configs:
        # Seed defaults
        seeded = []
        for d in DEFAULT_CONFIGS:
            cfg = ServiceReminderConfig(
                shop_id=sid,
                service_type=d["service_type"],
                window_start_months=d["window_start_months"],
                window_end_months=d["window_end_months"],
                sms_enabled=True,
                email_enabled=True,
                message_template=d["message_template"],
            )
            db.add(cfg)
            seeded.append(cfg)
        await db.commit()
        for cfg in seeded:
            await db.refresh(cfg)
        return [_cfg_to_response(cfg) for cfg in seeded]

    return [_cfg_to_response(cfg) for cfg in configs]


@router.post("/config", response_model=ReminderConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder_config(
    body: ReminderConfigCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    cfg = ServiceReminderConfig(
        shop_id=sid,
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


@router.post("/run", response_model=RunReminderResponse)
async def run_reminder_job(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    now = datetime.now(timezone.utc)
    sent_count = 0

    # Load all active reminders for this shop with their configs
    result = await db.execute(
        select(ServiceReminder, ServiceReminderConfig)
        .join(ServiceReminderConfig, ServiceReminder.config_id == ServiceReminderConfig.id)
        .where(ServiceReminder.shop_id == sid, ServiceReminder.status == "active")
    )
    rows = result.all()

    for reminder, config in rows:
        if reminder.last_service_at is None:
            continue

        months_since = (now - reminder.last_service_at).days / 30.0

        # Mark inactive if beyond window_end
        if months_since > config.window_end_months:
            reminder.status = "inactive"
            continue

        # Check if within window
        if months_since < config.window_start_months:
            continue

        # Check send throttle: only send if never sent or > 30 days ago
        if reminder.last_sent_at is not None:
            days_since_sent = (now - reminder.last_sent_at).days
            if days_since_sent < 30:
                continue

        # Stub: mark as sent
        reminder.last_sent_at = now
        reminder.send_count = (reminder.send_count or 0) + 1
        sent_count += 1

    await db.commit()
    return RunReminderResponse(reminders_sent=sent_count)


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
            ServiceReminderConfig.id == cid,
            ServiceReminderConfig.shop_id == uuid.UUID(shop_id),
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Reminder config not found")

    if body.service_type is not None:
        cfg.service_type = body.service_type
    if body.window_start_months is not None:
        cfg.window_start_months = body.window_start_months
    if body.window_end_months is not None:
        cfg.window_end_months = body.window_end_months
    if body.sms_enabled is not None:
        cfg.sms_enabled = body.sms_enabled
    if body.email_enabled is not None:
        cfg.email_enabled = body.email_enabled
    if body.message_template is not None:
        cfg.message_template = body.message_template

    await db.commit()
    await db.refresh(cfg)
    return _cfg_to_response(cfg)
