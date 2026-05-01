import base64
import uuid as _uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.shop_settings import ShopSettings

router = APIRouter(prefix="/diagnose", tags=["diagnose"])

CARMD_BASE = "https://api.carmd.com/v3.0"


def _build_carmd_headers(api_key: str, partner_token: str) -> dict:
    encoded = base64.b64encode(api_key.encode()).decode()
    return {
        "content-type": "application/json",
        "authorization": f"Basic {encoded}",
        "partner-token": partner_token,
    }


async def _get_carmd_creds(shop_id: str, db: AsyncSession) -> tuple[str | None, str | None]:
    result = await db.execute(select(ShopSettings).where(ShopSettings.shop_id == _uuid.UUID(shop_id)))
    settings = result.scalar_one_or_none()
    if not settings:
        return None, None
    return settings.carmd_api_key, settings.carmd_partner_token


async def _carmd_get(path: str, params: dict, api_key: str, partner_token: str) -> dict:
    headers = _build_carmd_headers(api_key, partner_token)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CARMD_BASE}{path}", params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def _carmd_post(path: str, body: dict, api_key: str, partner_token: str) -> dict:
    headers = _build_carmd_headers(api_key, partner_token)
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{CARMD_BASE}{path}", json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()


class AnalyzeRequest(BaseModel):
    year: int
    make: str
    model: str
    engine: str | None = None
    mileage: int | None = None
    dtcs: list[str] = []


@router.post("/analyze")
async def analyze(
    body: AnalyzeRequest,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    api_key, partner_token = await _get_carmd_creds(shop_id, db)
    if not api_key or not partner_token:
        raise HTTPException(status_code=422, detail="CarMD credentials not configured")

    params = {"year": body.year, "make": body.make, "model": body.model}
    if body.engine:
        params["engine"] = body.engine

    diagnosis_data: list = []
    repair_data: list = []

    for dtc in body.dtcs:
        dtc_params = {**params, "dtc": dtc}
        try:
            d = await _carmd_post("/diagnose", dtc_params, api_key, partner_token)
            diagnosis_data.extend(d.get("data", []))
        except httpx.HTTPError:
            pass
        try:
            r = await _carmd_post("/repair", dtc_params, api_key, partner_token)
            repair_data.extend(r.get("data", []))
        except httpx.HTTPError:
            pass

    return {"diagnosis": diagnosis_data, "repair_plan": repair_data}


@router.get("/tsb")
async def get_tsb(
    year: int,
    make: str,
    model: str,
    engine: str | None = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    api_key, partner_token = await _get_carmd_creds(shop_id, db)
    if not api_key or not partner_token:
        raise HTTPException(status_code=422, detail="CarMD credentials not configured")
    params = {"year": year, "make": make, "model": model}
    if engine:
        params["engine"] = engine
    data = await _carmd_get("/tsb", params, api_key, partner_token)
    return {"tsbs": data.get("data", [])}


@router.get("/recalls")
async def get_recalls(
    year: int,
    make: str,
    model: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    api_key, partner_token = await _get_carmd_creds(shop_id, db)
    if not api_key or not partner_token:
        raise HTTPException(status_code=422, detail="CarMD credentials not configured")
    params = {"year": year, "make": make, "model": model}
    data = await _carmd_get("/recall", params, api_key, partner_token)
    return {"recalls": data.get("data", [])}


@router.get("/maintenance")
async def get_maintenance(
    year: int,
    make: str,
    model: str,
    mileage: int = 0,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    api_key, partner_token = await _get_carmd_creds(shop_id, db)
    if not api_key or not partner_token:
        raise HTTPException(status_code=422, detail="CarMD credentials not configured")
    params = {"year": year, "make": make, "model": model, "mileage": mileage}
    data = await _carmd_get("/maintainance", params, api_key, partner_token)
    return {"maintenance": data.get("data", [])}


class AddToJobCardRequest(BaseModel):
    job_card_id: str
    diagnosis: list[dict]
    repair_plan: list[dict]


@router.post("/add-to-job-card")
async def add_to_job_card(
    body: AddToJobCardRequest,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    from src.models.job_card import JobCard
    result = await db.execute(
        select(JobCard).where(
            JobCard.id == _uuid.UUID(body.job_card_id),
            JobCard.shop_id == _uuid.UUID(shop_id),
        )
    )
    job_card = result.scalar_one_or_none()
    if not job_card:
        raise HTTPException(status_code=404, detail="Job card not found")

    existing_notes = job_card.notes or ""
    diag_summary = "; ".join(d.get("desc", "") for d in body.diagnosis[:3] if d.get("desc"))
    job_card.notes = f"{existing_notes}\n\n[Diagnose] {diag_summary}".strip()

    new_services = list(job_card.services or [])
    for repair in body.repair_plan[:3]:
        desc = repair.get("repair_desc") or repair.get("desc") or ""
        labor = repair.get("labor_hrs") or 0
        if desc:
            new_services.append({"description": desc, "labor_hours": labor, "source": "carmd"})
    job_card.services = new_services

    await db.commit()
    return {"ok": True}


class SendSummaryRequest(BaseModel):
    customer_id: str
    diagnosis: list[dict]


@router.post("/send-summary")
async def send_summary(
    body: SendSummaryRequest,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    top_causes = [d.get("layman_desc") or d.get("desc") for d in body.diagnosis[:2] if d]
    summary = "Our inspection found: " + ", ".join(c for c in top_causes if c)
    summary += ". We recommend scheduling a service visit."
    return {"sms_text": summary, "sent": False, "note": "SMS sending not yet configured"}
