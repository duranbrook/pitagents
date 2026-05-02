import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.shop_settings import ShopSettings
from src.models.shop import Shop

router = APIRouter(prefix="/settings", tags=["settings"])


class ShopSettingsResponse(BaseModel):
    id: str
    shop_id: str
    nav_pins: list[str]
    stripe_publishable_key: Optional[str] = None
    has_stripe_secret: bool = False
    mitchell1_enabled: bool
    has_mitchell1_key: bool = False
    synchrony_enabled: bool
    synchrony_dealer_id: Optional[str] = None
    wisetack_enabled: bool
    wisetack_merchant_id: Optional[str] = None
    quickbooks_enabled: bool
    has_quickbooks_token: bool = False
    carmd_api_key: Optional[str] = None
    financing_threshold: str


class ShopSettingsUpdate(BaseModel):
    nav_pins: Optional[list[str]] = None
    stripe_publishable_key: Optional[str] = None
    stripe_secret_key_encrypted: Optional[str] = None
    mitchell1_enabled: Optional[bool] = None
    mitchell1_api_key_encrypted: Optional[str] = None
    synchrony_enabled: Optional[bool] = None
    synchrony_dealer_id: Optional[str] = None
    wisetack_enabled: Optional[bool] = None
    wisetack_merchant_id: Optional[str] = None
    quickbooks_enabled: Optional[bool] = None
    quickbooks_refresh_token_encrypted: Optional[str] = None
    carmd_api_key: Optional[str] = None
    financing_threshold: Optional[str] = None


class ShopProfileResponse(BaseModel):
    id: str
    name: str
    address: Optional[str] = None
    labor_rate: str


class ShopProfileUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    labor_rate: Optional[str] = None


def _to_response(s: ShopSettings) -> ShopSettingsResponse:
    return ShopSettingsResponse(
        id=str(s.id),
        shop_id=str(s.shop_id),
        nav_pins=s.nav_pins or [],
        stripe_publishable_key=s.stripe_publishable_key,
        has_stripe_secret=bool((s.stripe_secret_key_encrypted or "").strip()),
        mitchell1_enabled=bool(s.mitchell1_enabled),
        has_mitchell1_key=bool((s.mitchell1_api_key_encrypted or "").strip()),
        synchrony_enabled=bool(s.synchrony_enabled),
        synchrony_dealer_id=s.synchrony_dealer_id,
        wisetack_enabled=bool(s.wisetack_enabled),
        wisetack_merchant_id=s.wisetack_merchant_id,
        quickbooks_enabled=bool(s.quickbooks_enabled),
        has_quickbooks_token=bool((s.quickbooks_refresh_token_encrypted or "").strip()),
        # carmd_api_key is a non-secret identifier, returned as plain text (unlike stripe/mitchell1/quickbooks)
        carmd_api_key=s.carmd_api_key,
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
    for field in (
        "stripe_publishable_key", "stripe_secret_key_encrypted",
        "mitchell1_enabled", "mitchell1_api_key_encrypted",
        "synchrony_enabled", "synchrony_dealer_id",
        "wisetack_enabled", "wisetack_merchant_id",
        "quickbooks_enabled", "quickbooks_refresh_token_encrypted",
        "carmd_api_key", "financing_threshold",
    ):
        val = getattr(body, field, None)
        if val is not None:
            setattr(settings, field, val)
    await db.commit()
    await db.refresh(settings)
    return _to_response(settings)


@router.get("/profile", response_model=ShopProfileResponse)
async def get_shop_profile(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Shop).where(Shop.id == uuid.UUID(shop_id)))
    shop = result.scalar_one_or_none()
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
    return ShopProfileResponse(
        id=str(shop.id),
        name=shop.name,
        address=shop.address,
        labor_rate=str(shop.labor_rate),
    )


@router.patch("/profile", response_model=ShopProfileResponse)
async def update_shop_profile(
    body: ShopProfileUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Shop).where(Shop.id == uuid.UUID(shop_id)))
    shop = result.scalar_one_or_none()
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
    if body.name is not None:
        shop.name = body.name
    if body.address is not None:
        shop.address = body.address
    if body.labor_rate is not None:
        try:
            shop.labor_rate = Decimal(body.labor_rate)
        except Exception:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="labor_rate must be a valid number")
    await db.commit()
    await db.refresh(shop)
    return ShopProfileResponse(
        id=str(shop.id),
        name=shop.name,
        address=shop.address,
        labor_rate=str(shop.labor_rate),
    )
