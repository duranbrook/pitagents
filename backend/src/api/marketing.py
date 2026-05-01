import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, String
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.campaign import Campaign

router = APIRouter(prefix="/marketing", tags=["marketing"])

TEMPLATES = [
    {
        "id": "seasonal-promo",
        "name": "Seasonal Promo",
        "message_body": "Hi {first_name}! Summer is here — bring in your {vehicle} for an AC check. Book now: {booking_link}",
    },
    {
        "id": "win-back",
        "name": "Win-Back",
        "message_body": "Hi {first_name}, we miss you! It's been a while since your last visit. Come back in and we'll take care of your {vehicle}.",
    },
    {
        "id": "maintenance-reminder",
        "name": "Maintenance Reminder",
        "message_body": "Hi {first_name}, your {vehicle} is due for {service}. Book online: {booking_link}",
    },
]


class AudienceSegment(BaseModel):
    type: str  # all_customers | by_service | by_last_visit | by_vehicle_type
    service_type: str | None = None
    last_visit_months_start: int | None = None
    last_visit_months_end: int | None = None
    vehicle_type: str | None = None


class CampaignCreate(BaseModel):
    name: str
    message_body: str
    channel: str = "sms"
    audience_segment: dict
    send_at: str | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    message_body: str | None = None
    channel: str | None = None
    audience_segment: dict | None = None
    send_at: str | None = None
    status: str | None = None


class CampaignResponse(BaseModel):
    campaign_id: str
    shop_id: str
    name: str
    status: str
    message_body: str
    channel: str
    audience_segment: dict
    send_at: str | None
    sent_at: str | None
    stats: dict
    created_at: str


def _to_response(c: Campaign) -> CampaignResponse:
    return CampaignResponse(
        campaign_id=str(c.id),
        shop_id=str(c.shop_id),
        name=c.name,
        status=c.status,
        message_body=c.message_body,
        channel=c.channel,
        audience_segment=c.audience_segment or {},
        send_at=c.send_at.isoformat() if c.send_at else None,
        sent_at=c.sent_at.isoformat() if c.sent_at else None,
        stats=c.stats or {},
        created_at=c.created_at.isoformat(),
    )


@router.get("/templates")
async def list_templates():
    return TEMPLATES


@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    status: str | None = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    q = select(Campaign).where(Campaign.shop_id == shop_id)
    if status:
        q = q.where(Campaign.status == status)
    q = q.order_by(Campaign.created_at.desc())
    result = await db.execute(q)
    return [_to_response(c) for c in result.scalars().all()]


@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    send_at = datetime.fromisoformat(body.send_at) if body.send_at else None
    campaign = Campaign(
        shop_id=shop_id,
        name=body.name,
        message_body=body.message_body,
        channel=body.channel,
        audience_segment=body.audience_segment,
        send_at=send_at,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return _to_response(campaign)


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == uuid.UUID(campaign_id), Campaign.shop_id == shop_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "send_at" and value:
            value = datetime.fromisoformat(value)
        setattr(campaign, field, value)
    await db.commit()
    await db.refresh(campaign)
    return _to_response(campaign)


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == uuid.UUID(campaign_id), Campaign.shop_id == shop_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await db.delete(campaign)
    await db.commit()


@router.get("/audience/count")
async def get_audience_count(
    segment_type: str,
    service_type: str | None = None,
    last_visit_months_start: int | None = None,
    last_visit_months_end: int | None = None,
    vehicle_type: str | None = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    from src.models.customer import Customer
    from src.models.job_card import JobCard
    from sqlalchemy import and_
    from datetime import timedelta

    shop_uuid = uuid.UUID(shop_id)

    if segment_type == "all_customers":
        q = select(func.count(Customer.id)).where(Customer.shop_id == shop_uuid)
        result = await db.execute(q)
        return {"count": result.scalar() or 0}

    if segment_type == "by_last_visit":
        if last_visit_months_start is None or last_visit_months_end is None:
            raise HTTPException(status_code=400, detail="last_visit_months_start and last_visit_months_end required")
        now = datetime.utcnow()
        window_start = now - timedelta(days=last_visit_months_end * 30)
        window_end = now - timedelta(days=last_visit_months_start * 30)
        subq = (
            select(JobCard.customer_id)
            .where(
                and_(
                    JobCard.shop_id == shop_uuid,
                    JobCard.created_at >= window_start,
                    JobCard.created_at <= window_end,
                )
            )
            .distinct()
        )
        q = select(func.count()).select_from(subq.subquery())
        result = await db.execute(q)
        return {"count": result.scalar() or 0}

    if segment_type == "by_service":
        if not service_type:
            raise HTTPException(status_code=400, detail="service_type required")
        subq = (
            select(JobCard.customer_id)
            .where(
                and_(
                    JobCard.shop_id == shop_uuid,
                    JobCard.services.cast(String).contains(f'"description": "{service_type}"'),
                )
            )
            .distinct()
        )
        q = select(func.count()).select_from(subq.subquery())
        result = await db.execute(q)
        return {"count": result.scalar() or 0}

    if segment_type == "by_vehicle_type":
        if not vehicle_type:
            raise HTTPException(status_code=400, detail="vehicle_type required")
        from src.models.vehicle import Vehicle
        subq = (
            select(JobCard.customer_id)
            .join(Vehicle, Vehicle.id == JobCard.vehicle_id)
            .where(
                and_(
                    JobCard.shop_id == shop_uuid,
                    Vehicle.make.ilike(f"%{vehicle_type}%"),
                )
            )
            .distinct()
        )
        q = select(func.count()).select_from(subq.subquery())
        result = await db.execute(q)
        return {"count": result.scalar() or 0}

    raise HTTPException(status_code=400, detail=f"Unknown segment_type: {segment_type}")


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(
    campaign_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == uuid.UUID(campaign_id), Campaign.shop_id == shop_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == "sent":
        raise HTTPException(status_code=400, detail="Campaign already sent")

    campaign.status = "sent"
    campaign.sent_at = datetime.utcnow()
    campaign.stats = {**campaign.stats, "sent_count": 0, "note": "SMS/email delivery not yet wired"}
    await db.commit()
    await db.refresh(campaign)
    return _to_response(campaign)
