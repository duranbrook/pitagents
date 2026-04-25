"""Session management and media upload endpoints."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel

from src.api.deps import get_current_user
from src.storage.s3 import StorageService

router = APIRouter(prefix="/sessions", tags=["sessions"])

_sessions: dict[str, dict] = {}
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
) -> CreateSessionResponse:
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "session_id": session_id,
        "shop_id": body.shop_id,
        "labor_rate": body.labor_rate,
        "pricing_flag": body.pricing_flag,
        "status": "recording",
        "created_by": current_user.get("sub"),
        "media": [],
    }
    return CreateSessionResponse(session_id=session_id, status="recording")


@router.post("/{session_id}/media", response_model=UploadMediaResponse)
async def upload_media(
    session_id: str,
    file: UploadFile = File(...),
    media_type: Literal["audio", "video", "photo"] = Form(...),
    tag: Literal["vin", "odometer", "tire", "damage", "general"] = Form(...),
    current_user: dict = Depends(get_current_user),
) -> UploadMediaResponse:
    if session_id not in _sessions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"
    media_id = str(uuid.uuid4())
    key = f"{session_id}/{media_id}/{filename}"

    storage = StorageService()
    s3_url = await storage.upload(data, key, content_type)

    media_record = {
        "media_id": media_id,
        "session_id": session_id,
        "media_type": media_type,
        "tag": tag,
        "s3_url": s3_url,
        "filename": filename,
    }
    _media[media_id] = media_record
    _sessions[session_id]["media"].append(media_id)

    return UploadMediaResponse(media_id=media_id, s3_url=s3_url)


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session
