import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.shop_settings import ShopSettings

router = APIRouter(prefix="/settings", tags=["settings"])


class ShopSettingsResponse(BaseModel):
    id: str
    shop_id: str
    nav_pins: list[str]
    stripe_publishable_key: Optional[str] = None
    mitchell1_enabled: bool
    synchrony_enabled: bool
    wisetack_enabled: bool
    quickbooks_enabled: bool
    financing_threshold: str


class ShopSettingsUpdate(BaseModel):
    nav_pins: Optional[list[str]] = None
    stripe_publishable_key: Optional[str] = None
    mitchell1_enabled: Optional[bool] = None
    synchrony_enabled: Optional[bool] = None
    synchrony_dealer_id: Optional[str] = None
    wisetack_enabled: Optional[bool] = None
    wisetack_merchant_id: Optional[str] = None
    quickbooks_enabled: Optional[bool] = None
    financing_threshold: Optional[str] = None


def _to_response(s: ShopSettings) -> ShopSettingsResponse:
    return ShopSettingsResponse(
        id=str(s.id),
        shop_id=str(s.shop_id),
        nav_pins=s.nav_pins or [],
        stripe_publishable_key=s.stripe_publishable_key,
        mitchell1_enabled=bool(s.mitchell1_enabled),
        synchrony_enabled=bool(s.synchrony_enabled),
        wisetack_enabled=bool(s.wisetack_enabled),
        quickbooks_enabled=bool(s.quickbooks_enabled),
        financing_threshold=s.financing_threshold or "500",
    )


async def _get_or_create(shop_id: uuid.UUID, db: AsyncSession) -> ShopSettings:
    result = await db.execute(select(ShopSettings).where(ShopSettings.shop_id == shop_id))
    settings = result.scalar_one_or_none()
    if settings is None:
        try:
            settings = ShopSettings(shop_id=shop_id, nav_pins=[])
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
        except IntegrityError:
            await db.rollback()
            result = await db.execute(select(ShopSettings).where(ShopSettings.shop_id == shop_id))
            settings = result.scalar_one()
    return settings


@router.get("/shop", response_model=ShopSettingsResponse)
async def get_shop_settings(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    return _to_response(await _get_or_create(uuid.UUID(shop_id), db))


@router.patch("/shop", response_model=ShopSettingsResponse)
async def update_shop_settings(
    body: ShopSettingsUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    settings = await _get_or_create(uuid.UUID(shop_id), db)
    if body.nav_pins is not None:
        settings.nav_pins = body.nav_pins[:8]
    for field in ("stripe_publishable_key", "mitchell1_enabled", "synchrony_enabled",
                  "synchrony_dealer_id", "wisetack_enabled", "wisetack_merchant_id",
                  "quickbooks_enabled", "financing_threshold"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(settings, field, val)
    await db.commit()
    await db.refresh(settings)
    return _to_response(settings)
