import uuid
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.base import get_db
from src.models.demo_request import DemoRequest

router = APIRouter(prefix="/demo", tags=["demo"])


class DemoRequestBody(BaseModel):
    first_name: str
    last_name: str
    email: str
    shop_name: str
    locations: str
    message: Optional[str] = None


class OkResponse(BaseModel):
    ok: bool = True


@router.post("/request", response_model=OkResponse)
async def submit_demo_request(
    body: DemoRequestBody,
    db: AsyncSession = Depends(get_db),
) -> OkResponse:
    record = DemoRequest(
        id=uuid.uuid4(),
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        shop_name=body.shop_name,
        locations=body.locations,
        message=body.message,
    )
    db.add(record)
    await db.commit()
    return OkResponse()
