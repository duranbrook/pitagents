import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.customer import Customer

router = APIRouter(prefix="/customers", tags=["customers"])


class CustomerCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None


class CustomerResponse(BaseModel):
    customer_id: str
    shop_id: str
    name: str
    email: str | None
    phone: str | None
    created_at: str


def _to_response(c: Customer) -> CustomerResponse:
    return CustomerResponse(
        customer_id=str(c.id),
        shop_id=str(c.shop_id),
        name=c.name,
        email=c.email,
        phone=c.phone,
        created_at=c.created_at.isoformat(),
    )


@router.get("", response_model=list[CustomerResponse])
async def list_customers(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
) -> list[CustomerResponse]:
    result = await db.execute(
        select(Customer)
        .where(Customer.shop_id == uuid.UUID(shop_id))
        .order_by(Customer.created_at.desc())
    )
    return [_to_response(c) for c in result.scalars().all()]


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    customer = Customer(
        shop_id=uuid.UUID(shop_id),
        name=body.name,
        email=body.email,
        phone=body.phone,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return _to_response(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Customer).where(
            Customer.id == uuid.UUID(customer_id),
            Customer.shop_id == uuid.UUID(shop_id),
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    await db.delete(customer)
    await db.commit()
