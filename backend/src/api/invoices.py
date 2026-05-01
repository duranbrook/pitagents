import os
import uuid
from decimal import Decimal
import stripe as stripe_lib
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, cast, Integer
from pydantic import BaseModel
from typing import Optional, Literal
from src.db.base import get_db
from src.api.deps import get_current_shop_id, get_current_user_id
from src.models.invoice import Invoice, InvoicePaymentEvent
from src.models.job_card import JobCard
from src.models.shop_settings import ShopSettings
from sqlalchemy import func as sql_func

router = APIRouter(prefix="/invoices", tags=["invoices"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class LineItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    amount: float = 0.0


class InvoiceCreate(BaseModel):
    job_card_id: Optional[str] = None
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    line_items: list[LineItem] = []
    tax_rate: float = 0.0
    due_date: Optional[str] = None
    stripe_payment_link: Optional[str] = None
    pdf_url: Optional[str] = None


class InvoiceFromJobCard(BaseModel):
    job_card_id: str
    tax_rate: float = 0.0
    due_date: Optional[str] = None


class InvoiceUpdate(BaseModel):
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    status: Optional[Literal["pending", "partial", "paid", "void"]] = None
    line_items: Optional[list[LineItem]] = None
    subtotal: Optional[float] = None
    tax_rate: Optional[float] = None
    total: Optional[float] = None
    due_date: Optional[str] = None
    stripe_payment_link: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    pdf_url: Optional[str] = None


class RecordPayment(BaseModel):
    amount: float
    method: Literal["stripe", "card", "cash", "check"]
    notes: Optional[str] = None


class FinancingLinkRequest(BaseModel):
    provider: str  # synchrony | wisetack


class InvoiceResponse(BaseModel):
    id: str
    shop_id: str
    job_card_id: Optional[str] = None
    number: str
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    status: str
    line_items: list[dict]
    subtotal: str
    tax_rate: str
    total: str
    amount_paid: str
    due_date: Optional[str] = None
    stripe_payment_link: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    pdf_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PaymentEventResponse(BaseModel):
    id: str
    invoice_id: str
    amount: str
    method: str
    recorded_by: Optional[str] = None
    recorded_at: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _inv_to_response(inv: Invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=str(inv.id),
        shop_id=str(inv.shop_id),
        job_card_id=str(inv.job_card_id) if inv.job_card_id else None,
        number=inv.number,
        customer_id=str(inv.customer_id) if inv.customer_id else None,
        vehicle_id=str(inv.vehicle_id) if inv.vehicle_id else None,
        status=inv.status,
        line_items=inv.line_items or [],
        subtotal=str(inv.subtotal or "0"),
        tax_rate=str(inv.tax_rate or "0"),
        total=str(inv.total or "0"),
        amount_paid=str(inv.amount_paid or "0"),
        due_date=inv.due_date.isoformat() if inv.due_date else None,
        stripe_payment_link=inv.stripe_payment_link,
        stripe_payment_intent_id=inv.stripe_payment_intent_id,
        pdf_url=inv.pdf_url,
        created_at=inv.created_at.isoformat() if inv.created_at else "",
        updated_at=inv.updated_at.isoformat() if inv.updated_at else "",
    )


async def _next_invoice_number(shop_id: uuid.UUID, db: AsyncSession) -> str:
    result = await db.execute(
        select(sql_func.max(
            cast(
                sql_func.split_part(Invoice.number, "-", 2),
                Integer
            )
        )).where(Invoice.shop_id == shop_id)
    )
    last_n = result.scalar()
    if last_n is None:
        return "INV-0001"
    return f"INV-{last_n + 1:04d}"


def _compute_totals_from_line_items(line_items: list[dict], tax_rate: float) -> tuple[Decimal, Decimal]:
    """Return (subtotal, total) as Decimals."""
    subtotal = sum(Decimal(str(item.get("amount", 0))) for item in line_items)
    total = subtotal * (1 + Decimal(str(tax_rate)))
    return subtotal, total


# ---------------------------------------------------------------------------
# Routes — note: POST /from-job-card MUST come before GET /{invoice_id}
# ---------------------------------------------------------------------------

@router.get("", response_model=list[InvoiceResponse])
async def list_invoices(
    inv_status: Optional[str] = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    q = select(Invoice).where(Invoice.shop_id == sid)
    if inv_status:
        q = q.where(Invoice.status == inv_status)
    result = await db.execute(q.order_by(Invoice.created_at.desc()))
    return [_inv_to_response(inv) for inv in result.scalars().all()]


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: InvoiceCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    number = await _next_invoice_number(sid, db)
    line_items = [item.model_dump() for item in body.line_items]
    subtotal, total = _compute_totals_from_line_items(line_items, body.tax_rate)
    inv = Invoice(
        shop_id=sid,
        number=number,
        job_card_id=uuid.UUID(body.job_card_id) if body.job_card_id else None,
        customer_id=uuid.UUID(body.customer_id) if body.customer_id else None,
        vehicle_id=uuid.UUID(body.vehicle_id) if body.vehicle_id else None,
        line_items=line_items,
        subtotal=subtotal,
        tax_rate=Decimal(str(body.tax_rate)),
        total=total,
        due_date=body.due_date,
        stripe_payment_link=body.stripe_payment_link,
        pdf_url=body.pdf_url,
        status="pending",
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return _inv_to_response(inv)


@router.post("/from-job-card", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice_from_job_card(
    body: InvoiceFromJobCard,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    jcid = uuid.UUID(body.job_card_id)

    # Load the job card
    result = await db.execute(
        select(JobCard).where(JobCard.id == jcid, JobCard.shop_id == sid)
    )
    card = result.scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail="Job card not found")

    # Prevent duplicate invoices for the same job card
    existing = await db.execute(
        select(Invoice).where(Invoice.job_card_id == card.id, Invoice.shop_id == sid)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Invoice already exists for this job card")

    # Build line items from services and parts
    line_items: list[dict] = []
    for svc in (card.services or []):
        amount = float(svc.get("labor_cost", 0))
        line_items.append({
            "description": svc.get("description", "Service"),
            "quantity": 1.0,
            "unit_price": amount,
            "amount": amount,
        })
    for part in (card.parts or []):
        qty = float(part.get("qty", 1))
        unit = float(part.get("sell_price", 0))
        line_items.append({
            "description": part.get("name", "Part"),
            "quantity": qty,
            "unit_price": unit,
            "amount": qty * unit,
        })

    subtotal, total = _compute_totals_from_line_items(line_items, body.tax_rate)
    number = await _next_invoice_number(sid, db)

    inv = Invoice(
        shop_id=sid,
        number=number,
        job_card_id=jcid,
        customer_id=card.customer_id,
        vehicle_id=card.vehicle_id,
        line_items=line_items,
        subtotal=subtotal,
        tax_rate=Decimal(str(body.tax_rate)),
        total=total,
        due_date=body.due_date,
        status="pending",
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return _inv_to_response(inv)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
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
    return _inv_to_response(inv)


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    body: InvoiceUpdate,
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

    if body.customer_id is not None:
        inv.customer_id = uuid.UUID(body.customer_id) if body.customer_id else None
    if body.vehicle_id is not None:
        inv.vehicle_id = uuid.UUID(body.vehicle_id) if body.vehicle_id else None
    if body.status is not None:
        if body.status == "paid":
            raise HTTPException(status_code=400, detail="Use record-payment to mark invoices as paid")
        inv.status = body.status
    if body.line_items is not None:
        inv.line_items = [item.model_dump() for item in body.line_items]
    if body.subtotal is not None:
        inv.subtotal = Decimal(str(body.subtotal))
    if body.tax_rate is not None:
        inv.tax_rate = Decimal(str(body.tax_rate))
    if body.total is not None:
        inv.total = Decimal(str(body.total))
    if body.due_date is not None:
        inv.due_date = body.due_date
    if body.stripe_payment_link is not None:
        inv.stripe_payment_link = body.stripe_payment_link
    if body.stripe_payment_intent_id is not None:
        inv.stripe_payment_intent_id = body.stripe_payment_intent_id
    if body.pdf_url is not None:
        inv.pdf_url = body.pdf_url

    await db.commit()
    await db.refresh(inv)
    return _inv_to_response(inv)


@router.post("/{invoice_id}/record-payment", response_model=PaymentEventResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    invoice_id: str,
    body: RecordPayment,
    shop_id: str = Depends(get_current_shop_id),
    user_id: str = Depends(get_current_user_id),
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

    payment_amount = Decimal(str(body.amount))
    current_paid = Decimal(str(inv.amount_paid or 0))
    new_paid = current_paid + payment_amount

    if new_paid > Decimal(str(inv.total or 0)):
        raise HTTPException(status_code=400, detail="Payment exceeds invoice total")

    event = InvoicePaymentEvent(
        invoice_id=iid,
        amount=payment_amount,
        method=body.method,
        recorded_by=uuid.UUID(user_id),
        notes=body.notes,
    )
    db.add(event)

    inv.amount_paid = new_paid
    inv_total = Decimal(str(inv.total or 0))
    if inv_total > 0 and new_paid >= inv_total:
        inv.status = "paid"
    elif new_paid > 0:
        inv.status = "partial"

    await db.commit()
    await db.refresh(event)
    return PaymentEventResponse(
        id=str(event.id),
        invoice_id=str(event.invoice_id),
        amount=str(event.amount),
        method=event.method,
        recorded_by=str(event.recorded_by) if event.recorded_by else None,
        recorded_at=event.recorded_at.isoformat() if event.recorded_at else None,
        notes=event.notes,
    )


@router.post("/{invoice_id}/payment-link")
async def send_payment_link(
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
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise HTTPException(status_code=400, detail="Stripe not configured")
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
        metadata={"invoice_id": str(iid), "shop_id": shop_id},
    )
    inv.stripe_payment_link = session.url
    await db.commit()
    return {"payment_link": session.url}


@router.post("/{invoice_id}/financing-link")
async def send_financing_link(
    invoice_id: str,
    body: FinancingLinkRequest,
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
    settings_result = await db.execute(
        select(ShopSettings).where(ShopSettings.shop_id == uuid.UUID(shop_id))
    )
    settings = settings_result.scalar_one_or_none()
    if body.provider == "synchrony":
        if not settings or not settings.synchrony_enabled or not getattr(settings, "synchrony_dealer_id", None):
            raise HTTPException(status_code=400, detail="Synchrony Car Care not configured")
        link = (
            f"https://apply.synchronybank.com/car-care"
            f"?dealer={settings.synchrony_dealer_id}"
            f"&amount={int(float(inv.total or 0))}"
            f"&ref={iid}"
        )
    elif body.provider == "wisetack":
        if not settings or not settings.wisetack_enabled or not getattr(settings, "wisetack_merchant_id", None):
            raise HTTPException(status_code=400, detail="Wisetack not configured")
        link = (
            f"https://app.wisetack.com/#/apply"
            f"?merchant={settings.wisetack_merchant_id}"
            f"&loan_amount={int(float(inv.total or 0))}"
            f"&ref={iid}"
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider}")
    return {"application_link": link, "provider": body.provider}
