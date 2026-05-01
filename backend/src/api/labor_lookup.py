import logging
import os
import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from src.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/labor-lookup", tags=["labor-lookup"])


class LaborLookupRequest(BaseModel):
    year: int
    make: str
    model: str
    engine: Optional[str] = None
    service: str


class LaborLookupResponse(BaseModel):
    hours: Optional[float]
    source: str  # mitchell1 | manual


@router.post("", response_model=LaborLookupResponse)
async def lookup_labor_time(
    body: LaborLookupRequest,
    _: dict = Depends(get_current_user),
):
    api_key = os.getenv("MITCHELL1_API_KEY", "")
    if not api_key:
        return LaborLookupResponse(hours=None, source="manual")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "https://api.prodemand.com/v1/labor",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "year": body.year,
                    "make": body.make,
                    "model": body.model,
                    "engine": body.engine,
                    "operation": body.service,
                },
            )
        if resp.status_code == 200:
            data = resp.json()
            return LaborLookupResponse(hours=data.get("laborHours"), source="mitchell1")
    except Exception as e:
        logger.warning("Mitchell1 lookup failed: %s", e)
    return LaborLookupResponse(hours=None, source="manual")
