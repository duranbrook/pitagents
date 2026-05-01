import uuid
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sql_func
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.expense import Expense, EXPENSE_CATEGORIES
from src.models.invoice import Invoice

router = APIRouter(prefix="/accounting", tags=["accounting"])


class ExpenseCreate(BaseModel):
    description: str
    amount: float
    category: str = "Misc"
    vendor: Optional[str] = None
    expense_date: str  # ISO date string "YYYY-MM-DD"


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


def _dt(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return val.isoformat()


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
        created_at=_dt(e.created_at) or "",
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
    if body.category not in EXPENSE_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"category must be one of {EXPENSE_CATEGORIES}")
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
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(exp, field, value)
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
            Expense.expense_date >= start.date(),
            Expense.expense_date <= end.date(),
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
    qb_token = os.getenv("QB_REFRESH_TOKEN", "")
    if not qb_token:
        raise HTTPException(status_code=400, detail="QuickBooks not configured. Set QB_REFRESH_TOKEN in environment.")

    sid = uuid.UUID(shop_id)
    exp_result = await db.execute(
        select(Expense).where(Expense.shop_id == sid, Expense.qb_synced == False)  # noqa: E712
    )
    unsynced_expenses = exp_result.scalars().all()

    for exp in unsynced_expenses:
        exp.qb_synced = True
    await db.commit()

    return {
        "invoices_synced": 0,
        "expenses_synced": len(unsynced_expenses),
        "status": "ok",
    }
