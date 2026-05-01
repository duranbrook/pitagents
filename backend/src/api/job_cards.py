import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
    return [_col_to_response(c) for c in cols]


@router.post("/columns/seed", response_model=list[ColumnResponse], status_code=status.HTTP_201_CREATED)
async def seed_columns(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    """Seed default columns for a shop (idempotent — skips if columns already exist)."""
    sid = uuid.UUID(shop_id)
    result = await db.execute(
        select(JobCardColumn)
        .where(JobCardColumn.shop_id == sid)
    )
    existing = result.scalars().all()
    if existing:
        return [_col_to_response(c) for c in existing]
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
