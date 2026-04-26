"""Session management, media upload, and report generation endpoints."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.db.base import get_db
from src.models.media import MediaFile
from src.models.report import Report
from src.models.session import InspectionSession
from src.models.vehicle import Vehicle
from src.storage.s3 import StorageService
from src.tools.extract_findings import extract_repair_findings
from src.tools.estimate import generate_estimate

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    shop_id: str
    labor_rate: float
    pricing_flag: Literal["shop", "alldata"]
    vehicle_id: str | None = None


class CreateSessionResponse(BaseModel):
    session_id: str
    status: str


class UploadMediaResponse(BaseModel):
    media_id: str
    s3_url: str


@router.post("", response_model=CreateSessionResponse)
async def create_session(
    body: CreateSessionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreateSessionResponse:
    try:
        shop_uuid = uuid.UUID(body.shop_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid shop_id")

    technician_uuid = uuid.UUID(current_user["sub"])

    vehicle_snapshot: dict = {"labor_rate": body.labor_rate, "pricing_flag": body.pricing_flag}
    if body.vehicle_id:
        try:
            vid = uuid.UUID(body.vehicle_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid vehicle_id")
        result = await db.execute(select(Vehicle).where(Vehicle.id == vid))
        v = result.scalar_one_or_none()
        if v:
            vehicle_snapshot.update({
                "vehicle_id": str(v.id),
                "year": v.year,
                "make": v.make,
                "model": v.model,
                "trim": v.trim,
                "vin": v.vin,
                "color": v.color,
            })

    session = InspectionSession(
        shop_id=shop_uuid,
        technician_id=technician_uuid,
        status="recording",
        vehicle=vehicle_snapshot,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return CreateSessionResponse(session_id=str(session.id), status=session.status)


@router.post("/{session_id}/media", response_model=UploadMediaResponse)
async def upload_media(
    session_id: str,
    file: UploadFile = File(...),
    media_type: Literal["audio", "video", "photo"] = Form(...),
    tag: Literal["vin", "odometer", "tire", "damage", "general"] = Form(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadMediaResponse:
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid session_id")

    result = await db.execute(select(InspectionSession).where(InspectionSession.id == sid))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"
    media_id = str(uuid.uuid4())
    key = f"{session_id}/{media_id}/{filename}"

    storage = StorageService()
    s3_url = await storage.upload(data, key, content_type)

    media_rec = MediaFile(
        id=uuid.UUID(media_id),
        session_id=sid,
        media_type=media_type,
        tag=tag,
        s3_url=s3_url,
        filename=filename,
    )
    db.add(media_rec)
    await db.commit()

    return UploadMediaResponse(media_id=media_id, s3_url=s3_url)


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid session_id")

    result = await db.execute(select(InspectionSession).where(InspectionSession.id == sid))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return {
        "session_id": str(session.id),
        "shop_id": str(session.shop_id),
        "status": session.status,
        "vehicle": session.vehicle or {},
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


@router.post("/{session_id}/generate-report")
async def generate_report(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run the full inspection → findings → estimate → report pipeline."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid session_id")

    # Load session
    sess_result = await db.execute(select(InspectionSession).where(InspectionSession.id == sid))
    session = sess_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Load media files
    media_result = await db.execute(select(MediaFile).where(MediaFile.session_id == sid))
    media_files = media_result.scalars().all()

    # Collect photo URLs for multimodal analysis (skip local:// dev URLs)
    photo_urls = [
        m.s3_url for m in media_files
        if m.media_type == "photo" and m.s3_url.startswith("http")
    ]

    transcript = session.transcript or ""

    # Extract findings via Claude (multimodal if photos available)
    findings_data = await extract_repair_findings(transcript, photo_urls or None)

    # Generate estimate with Qdrant parts pricing
    vehicle = session.vehicle or {}
    labor_rate = float(vehicle.get("labor_rate", 120.0))
    pricing_flag = vehicle.get("pricing_flag", "shop")
    estimate_data = await generate_estimate(vehicle, findings_data.get("findings", []), labor_rate, pricing_flag)

    # Persist report
    vehicle_id_str = vehicle.get("vehicle_id")
    vehicle_uuid = uuid.UUID(vehicle_id_str) if vehicle_id_str else None

    report = Report(
        session_id=sid,
        vehicle_id=vehicle_uuid,
        summary=findings_data.get("summary", ""),
        title=_build_title(vehicle),
        status="final",
        findings=findings_data.get("findings", []),
        estimate=estimate_data,
        estimate_total=estimate_data.get("total", 0),
        vehicle=vehicle,
    )
    db.add(report)

    # Mark session complete
    session.status = "complete"

    await db.commit()
    await db.refresh(report)

    return {
        "report_id": str(report.id),
        "share_token": str(report.share_token),
        "report_url": f"/r/{report.share_token}",
    }


def _build_title(vehicle: dict) -> str:
    parts = [vehicle.get("year"), vehicle.get("make"), vehicle.get("model")]
    label = " ".join(str(p) for p in parts if p)
    return f"Inspection Report — {label}" if label else "Inspection Report"
