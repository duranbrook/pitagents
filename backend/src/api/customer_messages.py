import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from twilio.rest import Client as TwilioClient
from twilio.request_validator import RequestValidator
from sendgrid import SendGridAPIClient as SendGridClient
from sendgrid.helpers.mail import Mail
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.customer import Customer
from src.models.vehicle import Vehicle
from src.models.customer_message import CustomerMessage
from src.config import settings

router = APIRouter(tags=["customer_messages"])


class MessageCreate(BaseModel):
    body: str
    channel: str  # "wa" or "email"
    subject: str | None = None
    report_id: str | None = None


class MessageResponse(BaseModel):
    message_id: str
    vehicle_id: str
    direction: str
    channel: str
    body: str
    external_id: str | None
    sent_at: str | None
    created_at: str


def _to_response(m: CustomerMessage) -> MessageResponse:
    return MessageResponse(
        message_id=str(m.id),
        vehicle_id=str(m.vehicle_id),
        direction=m.direction,
        channel=m.channel,
        body=m.body,
        external_id=m.external_id,
        sent_at=m.sent_at.isoformat() if m.sent_at else None,
        created_at=m.created_at.isoformat(),
    )


async def _get_vehicle_for_shop(vehicle_id: uuid.UUID, shop_id: str, db: AsyncSession) -> Vehicle:
    result = await db.execute(
        select(Vehicle)
        .join(Customer, Vehicle.customer_id == Customer.id)
        .where(
            Vehicle.id == vehicle_id,
            Customer.shop_id == uuid.UUID(shop_id),
        )
    )
    vehicle = result.scalar_one_or_none()
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle


def _send_whatsapp(to_phone: str, body: str) -> str:
    client = TwilioClient(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN.get_secret_value(),
    )
    message = client.messages.create(
        body=body,
        from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}",
        to=f"whatsapp:{to_phone}",
    )
    return message.sid


def _send_email(to_email: str, subject: str, body: str) -> str:
    sg = SendGridClient(settings.SENDGRID_API_KEY.get_secret_value())
    mail = Mail(
        from_email=settings.SENDGRID_FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )
    resp = sg.send(mail)
    return resp.headers.get("X-Message-Id", "")


@router.get("/vehicles/{vehicle_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    vehicle_id: uuid.UUID,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    await _get_vehicle_for_shop(vehicle_id, shop_id, db)
    result = await db.execute(
        select(CustomerMessage)
        .where(CustomerMessage.vehicle_id == vehicle_id)
        .order_by(CustomerMessage.created_at.asc())
    )
    return [_to_response(m) for m in result.scalars().all()]


@router.post(
    "/vehicles/{vehicle_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    vehicle_id: uuid.UUID,
    body: MessageCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    vehicle = await _get_vehicle_for_shop(vehicle_id, shop_id, db)

    cust_result = await db.execute(select(Customer).where(Customer.id == vehicle.customer_id))
    customer = cust_result.scalar_one()

    external_id: str | None = None
    sent_at: datetime | None = None

    if body.channel == "wa":
        if not customer.phone:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Customer has no phone number for WhatsApp",
            )
        try:
            external_id = _send_whatsapp(customer.phone, body.body)
            sent_at = datetime.now(timezone.utc)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("WhatsApp send failed (message still saved): %s", e)

    elif body.channel == "email":
        if not customer.email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Customer has no email address",
            )
        try:
            subject = body.subject or "Message from your mechanic"
            external_id = _send_email(customer.email, subject, body.body)
            sent_at = datetime.now(timezone.utc)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Email send failed (message still saved): %s", e)

    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="channel must be 'wa' or 'email'",
        )

    msg = CustomerMessage(
        vehicle_id=vehicle_id,
        report_id=uuid.UUID(body.report_id) if body.report_id else None,
        direction="out",
        channel=body.channel,
        body=body.body,
        external_id=external_id,
        sent_at=sent_at,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return _to_response(msg)


@router.post("/twilio/webhook")
async def twilio_webhook(
    request: Request,
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN.get_secret_value())
    form_data = dict(await request.form())
    signature = request.headers.get("X-Twilio-Signature", "")
    if not validator.validate(str(request.url), form_data, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")

    from_phone = From.replace("whatsapp:", "").strip()

    result = await db.execute(
        select(Vehicle)
        .join(Customer, Vehicle.customer_id == Customer.id)
        .where(Customer.phone == from_phone)
        .order_by(Vehicle.created_at.desc())
        .limit(1)
    )
    vehicle = result.scalar_one_or_none()

    if vehicle is None:
        return {"status": "ignored", "reason": "unknown_sender"}

    msg = CustomerMessage(
        vehicle_id=vehicle.id,
        direction="in",
        channel="wa",
        body=Body,
        external_id=MessageSid,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(msg)
    await db.commit()
    return {"status": "ok"}
