"""Reports CRUD — DB-backed consumer and staff views."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, require_owner
from src.db.base import get_db
from src.models.media import MediaFile
from src.models.report import Report
from src.models.session import InspectionSession

router = APIRouter(tags=["reports"])


class SendRequest(BaseModel):
    phone: str | None = None
    email: str | None = None


# ---------------------------------------------------------------------------
# Staff views (auth required)
# ---------------------------------------------------------------------------


@router.get("/reports")
async def list_reports(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all reports (summary view)."""
    result = await db.execute(select(Report).order_by(Report.created_at.desc()))
    reports = result.scalars().all()
    return [_to_list_item(r) for r in reports]


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get full report detail (staff view)."""
    report = await _get_report_or_404(report_id, db)
    return _to_staff_detail(report)


@router.post("/reports/{report_id}/send")
async def send_report(
    report_id: str,
    body: SendRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    report = await _get_report_or_404(report_id, db)
    report.sent_to = {"phone": body.phone, "email": body.email}
    await db.commit()
    return {"sent_to": report.sent_to}


# ---------------------------------------------------------------------------
# Consumer view (no auth)
# ---------------------------------------------------------------------------


@router.get("/r/{share_token}")
async def consumer_view(
    share_token: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Public consumer-facing report — no auth required."""
    try:
        token_uuid = uuid.UUID(share_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    result = await db.execute(select(Report).where(Report.share_token == token_uuid))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    # Gather media URLs from the session
    media_result = await db.execute(
        select(MediaFile).where(MediaFile.session_id == report.session_id)
    )
    media_files = media_result.scalars().all()
    media_urls = [m.s3_url for m in media_files if m.s3_url.startswith("http")]

    return _to_consumer_view(report, media_urls)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_report_or_404(report_id: str, db: AsyncSession) -> Report:
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    result = await db.execute(select(Report).where(Report.id == rid))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


def _to_list_item(r: Report) -> dict:
    return {
        "id": str(r.id),
        "vehicle": r.vehicle or {},
        "summary": r.summary or "",
        "total": float(r.estimate_total or 0),
        "share_token": str(r.share_token),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _to_staff_detail(r: Report) -> dict:
    estimate_data = r.estimate or {}
    line_items = estimate_data.get("line_items", [])
    estimate_rows = [
        {
            "part": item.get("part", ""),
            "labor_hours": item.get("labor_hrs", 0),
            "labor_cost": item.get("labor_cost", 0),
            "parts_cost": item.get("parts_cost", 0),
            "total": item.get("line_total", 0),
        }
        for item in line_items
    ]
    return {
        "id": str(r.id),
        "vehicle": r.vehicle or {},
        "summary": r.summary or "",
        "findings": r.findings or [],
        "estimate": estimate_rows,
        "total": float(r.estimate_total or 0),
        "share_token": str(r.share_token),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _to_consumer_view(r: Report, media_urls: list[str]) -> dict:
    # Normalize findings for consumer: {description, severity}
    severity_map = {"high": "urgent", "medium": "moderate", "low": "low"}
    findings = []
    for f in (r.findings or []):
        part = f.get("part", "")
        notes = f.get("notes", "")
        description = f"{part} — {notes}" if notes else part
        raw_sev = (f.get("severity") or "low").lower()
        findings.append({
            "description": description,
            "severity": severity_map.get(raw_sev, raw_sev),
        })

    # Flatten estimate to label/amount pairs
    estimate_data = r.estimate or {}
    estimate_items = [
        {"label": item.get("part", ""), "amount": item.get("line_total", 0)}
        for item in estimate_data.get("line_items", [])
    ]

    return {
        "id": str(r.id),
        "vehicle": r.vehicle or {},
        "summary": r.summary or "",
        "findings": findings,
        "estimate_items": estimate_items,
        "total": float(r.estimate_total or 0),
        "media_urls": media_urls,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
