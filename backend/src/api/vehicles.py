import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.customer import Customer
from src.models.vehicle import Vehicle
from src.models.report import Report

router = APIRouter(tags=["vehicles"])


class VehicleCreate(BaseModel):
    year: int
    make: str
    model: str
    trim: str | None = None
    vin: str | None = None
    color: str | None = None


class VehicleResponse(BaseModel):
    vehicle_id: str
    customer_id: str
    year: int
    make: str
    model: str
    trim: str | None
    vin: str | None
    color: str | None
    created_at: str


class ReportSummary(BaseModel):
    report_id: str
    title: str | None
    status: str
    estimate_total: float | None
    created_at: str


def _to_response(v: Vehicle) -> VehicleResponse:
    return VehicleResponse(
        vehicle_id=str(v.id),
        customer_id=str(v.customer_id),
        year=v.year,
        make=v.make,
        model=v.model,
        trim=v.trim,
        vin=v.vin,
        color=v.color,
        created_at=v.created_at.isoformat(),
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


@router.get("/customers/{customer_id}/vehicles", response_model=list[VehicleResponse])
async def list_vehicles(
    customer_id: uuid.UUID,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
) -> list[VehicleResponse]:
    cust_result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.shop_id == uuid.UUID(shop_id),
        )
    )
    if cust_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    result = await db.execute(
        select(Vehicle)
        .where(Vehicle.customer_id == customer_id)
        .order_by(Vehicle.created_at.desc())
    )
    return [_to_response(v) for v in result.scalars().all()]


@router.post(
    "/customers/{customer_id}/vehicles",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_vehicle(
    customer_id: uuid.UUID,
    body: VehicleCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
) -> VehicleResponse:
    cust_result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.shop_id == uuid.UUID(shop_id),
        )
    )
    if cust_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    vehicle = Vehicle(
        customer_id=customer_id,
        year=body.year,
        make=body.make,
        model=body.model,
        trim=body.trim,
        vin=body.vin,
        color=body.color,
    )
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return _to_response(vehicle)


@router.delete("/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: uuid.UUID,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    vehicle = await _get_vehicle_for_shop(vehicle_id, shop_id, db)
    await db.delete(vehicle)
    await db.commit()


@router.get("/vehicles/{vehicle_id}/reports", response_model=list[ReportSummary])
async def list_vehicle_reports(
    vehicle_id: uuid.UUID,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
) -> list[ReportSummary]:
    await _get_vehicle_for_shop(vehicle_id, shop_id, db)
    result = await db.execute(
        select(Report)
        .where(Report.vehicle_id == vehicle_id)
        .order_by(Report.created_at.desc())
    )
    return [
        ReportSummary(
            report_id=str(r.id),
            title=r.title,
            status=r.status,
            estimate_total=float(r.estimate_total) if r.estimate_total is not None else None,
            created_at=r.created_at.isoformat(),
        )
        for r in result.scalars().all()
    ]
