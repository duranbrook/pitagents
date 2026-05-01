import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, Literal
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.job_card import JobCardColumn, JobCard
from sqlalchemy import func as sql_func

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
    created_at: Optional[str]


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
        created_at=c.created_at.isoformat() if c.created_at else None,
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


# ---------------------------------------------------------------------------
# Job Card Pydantic models
# ---------------------------------------------------------------------------

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
    services: Optional[list[ServiceLine]] = None
    parts: Optional[list[PartLine]] = None
    notes: Optional[str] = None
    status: Optional[Literal["active", "closed", "void"]] = None


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
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


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
        created_at=c.created_at.isoformat() if c.created_at else None,
        updated_at=c.updated_at.isoformat() if c.updated_at else None,
    )


async def _next_card_number(shop_id: uuid.UUID, db: AsyncSession) -> str:
    result = await db.execute(
        select(sql_func.max(JobCard.number)).where(JobCard.shop_id == shop_id)
    )
    last = result.scalar()  # e.g. "JC-0003" or None
    if last is None:
        return "JC-0001"
    try:
        n = int(last.split("-")[1])
    except (IndexError, ValueError):
        n = 0
    return f"JC-{n + 1:04d}"


# ---------------------------------------------------------------------------
# Job Card route handlers
# NOTE: list/create ("" / "") come AFTER the column routes so that
#       /columns (literal) is matched before /{card_id} (wildcard).
# ---------------------------------------------------------------------------

@router.get("", response_model=list[JobCardResponse])
async def list_job_cards(
    column_id: Optional[str] = None,
    card_status: Optional[str] = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    q = select(JobCard).where(JobCard.shop_id == sid)
    if column_id:
        q = q.where(JobCard.column_id == uuid.UUID(column_id))
    if card_status:
        q = q.where(JobCard.status == card_status)
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
        card.services = [s.model_dump() for s in body.services]
    if body.parts is not None:
        card.parts = [p.model_dump() for p in body.parts]
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
