"""Session management and media upload endpoints."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.db.base import get_db
from src.models.session import InspectionSession
from src.storage.s3 import StorageService

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Media records remain in-memory (not yet in DB schema).
_media: dict[str, dict] = {}


class CreateSessionRequest(BaseModel):
    shop_id: str
    labor_rate: float
    pricing_flag: Literal["shop", "alldata"]


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

    session = InspectionSession(
        shop_id=shop_uuid,
        technician_id=technician_uuid,
        status="recording",
        vehicle={"labor_rate": body.labor_rate, "pricing_flag": body.pricing_flag},
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

    _media[media_id] = {
        "media_id": media_id,
        "session_id": session_id,
        "media_type": media_type,
        "tag": tag,
        "s3_url": s3_url,
        "filename": filename,
    }

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
