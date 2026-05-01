import uuid
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sql_func
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
        select(sql_func.coalesce(sql_func.sum(InvoicePaymentEvent.amount), 0))
        .join(Invoice, Invoice.id == InvoicePaymentEvent.invoice_id)
        .where(
            Invoice.shop_id == sid,
            InvoicePaymentEvent.recorded_at >= month_start,
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
            "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None,
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
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"Invoice {inv.number}"},
                        "unit_amount": int(float(inv.total or 0) * 100),
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + f"/invoices?paid={iid}",
                cancel_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + f"/invoices/{iid}",
                metadata={"invoice_id": str(iid)},
            )
            payment_link = session.url
            inv.stripe_payment_link = payment_link
            await db.commit()

    return {"status": "chase_sent", "payment_link": payment_link, "invoice_id": str(iid)}
